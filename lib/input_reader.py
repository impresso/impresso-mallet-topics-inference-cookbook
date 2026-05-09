#!/usr/bin/env python3
"""
This module provides classes for reading input documents from various file formats.
It defines an abstract base class `InputReader` and its concrete implementations
for reading JSONL and CSV files.

Classes:
    InputReader: Abstract base class for input readers.
    JsonlInputReader: Reads input from a JSONL file.
    ImpressoLinguisticProcessingJsonlInputReader: Reads input from an impresso
        linguistic processing JSONL file.
    CsvInputReader: Reads input from a CSV file in Mallet's format.
"""
import collections
import json
import re
from functools import lru_cache
from typing import Generator, Tuple, List, Set, Dict
import logging
import csv
from impresso_cookbook import get_s3_client
from abc import ABC, abstractmethod
from smart_open import open

log = logging.getLogger(__name__)
print(log)


VALID_CORE_RE = re.compile(r"^[a-z]+$")
DEFAULT_BOUNDARY_CHARS = (
    " \t\n\r"
    ".,;:!?()[]{}"
    "\"'"
    "-_\\/|~^=+*@#$%&§°£€¥¢©®™"
    "•■□▲►▼★♦✓†‡¶"
)


def load_translation_table(path: str) -> dict[int, str | None]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    raw_table = data.get("char_normalization")
    if not isinstance(raw_table, dict):
        raise ValueError(
            f"Normalization JSON must contain a char_normalization object: {path}"
        )

    table: dict[int, str | None] = {}
    for source, target in raw_table.items():
        if len(source) != 1:
            raise ValueError(f"Source key must be one character: {source!r}")
        if target is not None and not isinstance(target, str):
            raise ValueError(
                f"Replacement for {source!r} must be string or null, got {target!r}"
            )
        table[ord(source)] = target
    return table


def count_ascii_letters(text: str) -> int:
    return sum("a" <= ch <= "z" for ch in text)


class LemmaNormalizer:
    def __init__(
        self,
        translation_table: dict[int, str | None],
        boundary_chars: str = DEFAULT_BOUNDARY_CHARS,
        min_alpha: int = 3,
        min_alpha_ratio: float = 0.75,
        cache_size: int = 2_000_000,
    ) -> None:
        self.translation_table = translation_table
        self.boundary_chars = boundary_chars
        self.min_alpha = min_alpha
        self.min_alpha_ratio = min_alpha_ratio
        self.normalize = lru_cache(maxsize=cache_size)(self._normalize_uncached)

    def normalize_chars(self, lemma: str) -> str:
        return lemma.lower().translate(self.translation_table)

    def _normalize_uncached(self, lemma: str) -> str | None:
        base = self.normalize_chars(lemma).strip()
        if not base or any(ch.isdigit() for ch in base):
            return None

        candidate = base.strip(self.boundary_chars)
        if not candidate:
            return None
        candidate = candidate.replace(".", "")
        candidate = candidate.replace("-", "")
        candidate = candidate.replace("'", "")
        if not candidate or VALID_CORE_RE.fullmatch(candidate) is None:
            return None

        alpha_len = count_ascii_letters(candidate)
        if alpha_len < self.min_alpha:
            return None
        if alpha_len / len(base) < self.min_alpha_ratio:
            return None

        return candidate


def load_vocab(path: str) -> set[str]:
    vocab = set()
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            vocab.add(line.rstrip("\n").split("\t", 1)[0])
    log.info("Read %d vocabulary entries from %s", len(vocab), path)
    return vocab


class InputReader(ABC):
    """
    Abstract base class for input readers.
    Subclasses should implement the `read_documents` method to yield documents.
    """

    @abstractmethod
    def read_documents(self) -> Generator[Tuple[str, str], None, None]:
        """
        Yields a tuple of (document_id, text).
        Each implementation should handle its specific input format.
        """
        pass


class JsonlInputReader(InputReader):
    """
    Reads input from a JSONL file, where each line contains a JSON object
    with at least "id" and "text" fields.

    Args:
        input_file (str): Path to the input JSONL file.
        text_key (str): Key for the text field in the JSON objects.
        language_key (str): Key for the language field in the JSON objects.
    """

    def __init__(
        self,
        input_file: str,
        text_key: str = "text",
        language_key: str = "lg",
        docid_key: str = "id",
    ) -> None:
        self.input_file = input_file
        self.text_key = text_key
        self.language_key = language_key
        self.docid_key = docid_key
        self._cached_id_key = None  # Cache for the working ID key

    def _get_document_id(self, data: dict) -> str:
        """Get document ID from data, trying multiple possible keys.
        
        Args:
            data: The JSON document data
            
        Returns:
            The document ID
            
        Raises:
            KeyError: If no valid ID key is found
        """
        # If we already found a working key, use it
        if self._cached_id_key:
            return data[self._cached_id_key]
        
        # Try common ID keys in order of preference
        possible_keys = [self.docid_key, "ci_ref", "ci_id", "id", ]
        
        for key in possible_keys:
            if key in data:
                self._cached_id_key = key
                log.info("Using '%s' as document ID key", key)
                return data[key]
        
        # If none found, raise error with helpful message
        raise KeyError(
            f"Could not find document ID. Tried keys: {possible_keys}. "
            f"Available keys: {list(data.keys())}"
        )

    def read_documents(self) -> Generator[Tuple[str, str], None, None]:
        with open(self.input_file, "r", encoding="utf-8") as f:
            for line in f:
                data = json.loads(line)
                document_id = self._get_document_id(data)
                text = data[self.text_key]
                language = data.get(self.language_key, "und")
                yield document_id, language, text


class ImpressoLinguisticProcessingJsonlInputReader(InputReader):
    """
      Reads input from an impresso linguistic processing JSONL file, where each line
      contains a JSON object with the tokenized and PoS-tagged text.

      Args:
          input_file (str): Path to the input JSONL file.
          lang_lemmatization_dict (dict): Dictionary mapping languages to their
            respective lemmatization dictionaries.

      Input Example (omitting "l" if equal to "t"):
      ```
      {
    "ts": "2024-4-9T03:08:05",
    "id": "onsjongen-1947-01-31-a-i0035",
    "sents": [
      {
        "lg": "de",
        "tok": [
          {
            "t": "Glück",
            "p": "NOUN",
            "o": 0
          },
          {
            "t": "um",
            "p": "ADP",
            "o": 6
          },
          ...
          ```

    """

    def __init__(
        self,
        input_file: str,
        lang_lemmatization_dict: dict,
        language_configs: dict,
        ci_id_key: str = "id",
        language_key: str = "lg",
        ci_ids: List[str] | None = None,
    ) -> None:
        self.input_file = input_file
        self.lang_lemmatization_dict = lang_lemmatization_dict
        self.ci_id_key = ci_id_key
        self.language_key = language_key
        self.ci_ids: Set[str] | None = set(ci_ids) if ci_ids else None
        self.language_pos_filter_dict: Dict[str, Set[str]] = {
            lang: set(language_configs[lang].get("upos_filter", []))
            for lang in language_configs
        }
        self.language_configs = language_configs
        self.language_vocab: Dict[str, Set[str]] = {}
        self.language_normalizers: Dict[str, LemmaNormalizer] = {}
        for lang, config in language_configs.items():
            if config.get("preprocessing_mode") != "normalized-lemma-vocab-v1":
                continue
            vocab_path = config.get("vocab_path")
            normalization_path = config.get("char_normalization_path")
            if not vocab_path or not normalization_path:
                raise ValueError(
                    f"Language {lang} uses normalized-lemma-vocab-v1 but does not "
                    "define vocab_path and char_normalization_path"
                )
            self.language_vocab[lang] = load_vocab(vocab_path)
            self.language_normalizers[lang] = LemmaNormalizer(
                load_translation_table(normalization_path),
                min_alpha=int(config.get("min_lemma_length", 3)),
            )
        log.info(
            "%s",
            self,
        )
        self.stats = collections.Counter()
        self._cached_id_key = None  # Cache for the working ID key
        self._cached_token_key = None  # Cache for the working token key

    def __repr__(self):
        return (
            f"ImpressoLinguisticProcessingJsonlInputReader({self.input_file},"
            f" language_key: {self.language_key},  LemmatizationDictSize:"
            f" {len(self.lang_lemmatization_dict)}, ci_id_key: {self.ci_id_key},"
            f" {self.language_pos_filter_dict}, VocabLanguages:"
            f" {sorted(self.language_vocab)})"
        )

    def _get_document_id(self, data: dict) -> str:
        """Get document ID from data, trying multiple possible keys.
        
        Args:
            data: The JSON document data
            
        Returns:
            The document ID
            
        Raises:
            KeyError: If no valid ID key is found
        """
        # If we already found a working key, use it
        if self._cached_id_key:
            return data[self._cached_id_key]
        
        # Try common ID keys in order of preference
        possible_keys = ["ci_id", self.ci_id_key, "id", "ci_ref"]
        
        for key in possible_keys:
            if key in data:
                self._cached_id_key = key
                log.info("Using '%s' as document ID key", key)
                return data[key]
        
        # If none found, raise error with helpful message
        raise KeyError(
            f"Could not find document ID. Tried keys: {possible_keys}. "
            f"Available keys: {list(data.keys())}"
        )

    def _get_tokens_from_sent(self, sent: dict) -> list:
        """Get tokens from a sentence, trying multiple possible keys.
        
        Args:
            sent: The sentence data
            
        Returns:
            List of tokens
            
        Raises:
            KeyError: If no valid token key is found
        """
        # If we already found a working key, use it
        if self._cached_token_key:
            return sent[self._cached_token_key]
        
        # Try common token keys in order of preference
        possible_keys = ["tokens", "tok"]
        
        for key in possible_keys:
            if key in sent:
                self._cached_token_key = key
                log.info("Using '%s' as token key in sentences", key)
                return sent[key]
        
        # If none found, raise error with helpful message
        raise KeyError(
            f"Could not find tokens in sentence. Tried keys: {possible_keys}. "
            f"Available keys: {list(sent.keys())}"
        )

    def _process_sentences(
        self,
        sentences: list,
        language: str,
        lemma_lookup: dict,
        posfilter: set,
        lowercase_token: bool
    ) -> list:
        """Process a list of sentences and extract lemmatized tokens.
        
        Args:
            sentences: List of sentence objects
            language: Language code
            lemma_lookup: Dictionary for lemma lookups
            posfilter: Set of allowed POS tags (empty set = no filter)
            lowercase_token: Whether to lowercase tokens before lookup
            
        Returns:
            List of lemmas
        """
        lemmatized_text = []
        
        for sent in sentences:
            for token in self._get_tokens_from_sent(sent):
                # if posfilter is set, only include tokens with specified pos
                if posfilter and token["p"] not in posfilter:
                    continue

                # sometimes the lemma is missing or set to "", then ignore it!
                if token.get("l") == "":
                    del token["l"]

                token_text = token.get("t")

                # note that the freq_filter.py script used to use the lemma as
                # the key for the lookup, but this is not correct to do so, but
                # had limited effects. in the old spacy pipelines the lemma and
                # token was mostly the same and the loookup was actually done
                # with the lemma. But with better spacy lemmatization this does
                # not work anymore! so we use the token as the key for the
                # lookup
                if lowercase_token:
                    token_text = token_text.lower()
                lemma = lemma_lookup.get(token_text)
                if lemma:
                    lemmatized_text.append(lemma)
        
        return lemmatized_text

    def _process_sentences_v3(
        self,
        sentences: list,
        language: str,
        posfilter: set,
    ) -> list:
        """Process sentences with the v3 normalized lemma vocabulary schema."""

        lemmatized_text = []
        normalizer = self.language_normalizers[language]
        vocab = self.language_vocab[language]

        for sent in sentences:
            if sent.get(self.language_key) != language:
                continue
            for token in self._get_tokens_from_sent(sent):
                if posfilter and token.get("p") not in posfilter:
                    continue
                lemma = token.get("l") or token.get("t") or ""
                normalized = normalizer.normalize(lemma)
                if normalized and normalized in vocab:
                    lemmatized_text.append(normalized)

        return lemmatized_text

    def read_documents(
        self, lemmatization_strategy: str = "v2.0-legacy"
    ) -> Generator[Tuple[str, str], None, None]:
        log.warning("LOG Reading documents from %s", self.input_file)

        if self.input_file.startswith("s3://"):
            tranport_params = {"client": get_s3_client()}
        else:
            tranport_params = {}
        with open(
            self.input_file, "r", encoding="utf-8", transport_params=tranport_params
        ) as f:
            for line in f:
                data = json.loads(line)
                document_id = self._get_document_id(data)
                if self.ci_ids and document_id not in self.ci_ids:
                    continue
                
                # Get both title sentences (tsents) and body sentences (sents)
                # v2 format has tsents (can be empty list), v1 format doesn't have it
                tsents = data.get("tsents", [])
                sents = data.get("sents", [])
                
                # Skip if both are empty
                if not tsents and not sents:
                    self.stats["SKIPPED: no tsents or sents"] += 1
                    continue
                
                # Get language from first available sentence (prefer tsents if exists)
                if tsents and tsents[0].get(self.language_key):
                    language = tsents[0][self.language_key]
                elif sents and sents[0].get(self.language_key):
                    language = sents[0][self.language_key]
                else:
                    self.stats["SKIPPED: no language found"] += 1
                    continue

                if (
                    language not in self.lang_lemmatization_dict
                    and language not in self.language_vocab
                ):
                    self.stats[f"unsupported_language: {language}"] += 1
                    continue

                self.stats[f"supported_language: {language}"] += 1
                
                # Track documents with/without titles
                if tsents:
                    self.stats["documents_with_title"] += 1
                else:
                    self.stats["documents_without_title"] += 1
                
                lowercase_token: bool = self.language_configs[language].get(
                    "lowercase_token", False
                )
                min_lemmas = self.language_configs[language].get("min_lemmas", 10)
                posfilter = self.language_pos_filter_dict[language]
                preprocessing_mode = self.language_configs[language].get(
                    "preprocessing_mode", "v2.0-legacy"
                )
                include_titles = self.language_configs[language].get(
                    "include_titles", True
                )

                if preprocessing_mode == "normalized-lemma-vocab-v1":
                    title_lemmas = (
                        self._process_sentences_v3(tsents, language, posfilter)
                        if tsents and include_titles
                        else []
                    )
                    body_lemmas = (
                        self._process_sentences_v3(sents, language, posfilter)
                        if sents
                        else []
                    )
                else:
                    lemma_lookup = self.lang_lemmatization_dict[language]
                    title_lemmas = (
                        self._process_sentences(
                            tsents, language, lemma_lookup, posfilter, lowercase_token
                        )
                        if tsents and include_titles
                        else []
                    )
                    body_lemmas = (
                        self._process_sentences(
                            sents, language, lemma_lookup, posfilter, lowercase_token
                        )
                        if sents
                        else []
                    )
                
                # Concatenate title and body lemmas
                lemmatized_text = title_lemmas + body_lemmas

                log.debug(
                    "Document %s in language %s has %d lemmas",
                    document_id,
                    language,
                    len(lemmatized_text),
                )
                min_unique_lemmas = self.language_configs[language].get(
                    "min_unique_lemmas"
                )
                if min_unique_lemmas and len(set(lemmatized_text)) < min_unique_lemmas:
                    self.stats[
                        f"EXCLUDED: lang {language}: less_than_{min_unique_lemmas}"
                        "_unique_lemmas"
                    ] += 1
                    continue

                if (
                    len(lemmatized_text) >= min_lemmas
                    if preprocessing_mode == "normalized-lemma-vocab-v1"
                    else len(lemmatized_text) > min_lemmas
                ):
                    self.stats[
                        f"INCLUDED: lang {language}: at_least_{min_lemmas}_lemmas"
                    ] += 1
                else:
                    self.stats[
                        f"EXCLUDED: lang {language}: less_than_{min_lemmas}_lemmas"
                    ] += 1
                    continue

                yield document_id, language, " ".join(lemmatized_text)
        for key, value in sorted(self.stats.items()):
            log.info(f"STATS: {key}: {value}")


class CsvInputReader(InputReader):
    """
    Reads input from a CSV file in Mallet's format (document ID, dummy class, text).
    Assumes that the CSV has three columns: "id", "dummyclass", and "text".
    """

    def __init__(self, input_file: str) -> None:
        self.input_file = input_file

    def read_documents(self) -> Generator[Tuple[str, str], None, None]:
        with open(self.input_file, mode="r", encoding="utf-8") as f:
            csv_reader = csv.reader(f, delimiter="\t")
            for row in csv_reader:
                if len(row) < 3:
                    continue
                document_id, lang, text = row[0], row[1], row[2]

                yield document_id, lang.lower(), text
