#!/usr/bin/env python3
"""
This module provides a class for multilingual lemmatization using spaCy language models.
It allows for the initialization of language-specific lemmatization dictionaries and
processing pipelines, and provides methods for analyzing and lemmatizing text.

Classes:
    MultilingualLemmatizer: A class for multilingual lemmatization.

Functions:
    __init__(self, lang_lemmatization_dict: Dict[str, Dict[str, str]], languages_dict: Dict[str, str] = {}):

    _load_language_processors(self, languages_dict) -> Dict[str, spacy.language.Language]:

    analyze_text(self, text: str, lang: str) -> List[str]:

    lemmatize_linguistic_processing_tokens(self, language, token_dicts, pos_filter: Optional[Set[str]] = None):
        Lemmatizes the tokens from linguistic processing.
"""

import spacy
from typing import Dict, List, Set, Optional


class MultilingualLemmatizer:
    def __init__(
        self,
        lang_lemmatization_dict: Dict[str, Dict[str, str]],
        languages_dict: Dict[str, str] = {},
    ):
        """
        Initializes the linguistic lemmatizer with specified languages and lemmatization dictionary.

        Args:

            lemmatization_dict (Dict[str, str]): Dictionary mapping tokens to their lemmas.
            languages_dict (List[str]): List of language codes to load processing pipelines for. If not provided, no
            spacy models will be loaded
        """
        self.languages_dict = languages_dict
        self.lemmatization_dict = lang_lemmatization_dict
        if self.languages_dict:
            self.language_processors = self._load_language_processors(languages_dict)
        else:
            self.language_processors = {}

    def _load_language_processors(
        self, languages_dict
    ) -> Dict[str, spacy.language.Language]:
        """
        Loads spacy language processors for the specified languages.

        Returns:
            Dict[str, spacy.language.Language]: Dictionary mapping language codes to spacy NLP pipelines.
        """

        processors = {}
        for lang in languages_dict:
            processors[lang] = spacy.load(
                languages_dict[lang], disable=["parser", "ner"]
            )
            processors[lang].add_pipe("sentencizer")
        return processors

    def analyze_text(self, text: str, lang: str) -> List[str]:
        """
        Analyzes text, performing tokenization, POS tagging, and lemma mapping.

        Args:
            text (str): Text to process.
            lang (str): Language code for the text.

        Returns:
            List[str]: List of tokens that have matching entries in the lemmatization dictionary.
        """
        if lang not in self.language_processors:
            raise ValueError(f"No processing pipeline for language '{lang}'")

        nlp = self.language_processors[lang]
        doc = nlp(text)
        token2lemma = self.lemmatization_dict[lang]
        matched_tokens = [
            lemma for tok in doc if (lemma := token2lemma.get(tok.text.lower()))
        ]
        return matched_tokens

    def lemmatize_linguistic_processing_tokens(
        self, language, token_dicts, pos_filter: Optional[Set[str]] = None
    ):
        """
        Lemmatizes the tokens from linguistic processing

        Args:
            token_dict (Dict): Dictionary containing the tokens from linguistic processing

        Returns:
            List[str]: List of lemmatized tokens
        """

        lemmatized_text = []
        lemmatizer = self.lemmatization_dict[language]
        for token in token_dicts:
            if pos_filter and token["p"] not in pos_filter:
                continue

            token = token["t"].lower()
            lemma = lemmatizer.get(token)
            if token.get("l"):
                lemma = (token.get("l") or token["t"]).lower()
            if lemma in lemmatizer:
                lemma = lemmatizer[lemma]
            lemmatized_text.append(lemma)
        return lemmatized_text
