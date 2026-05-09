#!/usr/bin/python3

"""
This script performs vectorization and topic inference using Mallet models. It accepts a
raw JSONL file, identifies the language of the text, and applies the corresponding
Mallet model for topic inference. It also supports other input formats through a
flexible InputReader abstraction (e.g., CSV, JSONL).

Key Features:
- Handles multiple languages in a single run without calling Mallet multiple times.
- Supports various input formats (JSONL, CSV).
- Outputs results in JSONL or CSV format.

Classes:
- MalletVectorizer: Handles text-to-Mallet vectorization.
- LanguageInferencer: Performs topic inference using a Mallet inferencer and the vectorizer.
- InputReader (abstract class): Defines the interface for reading input documents.
- JsonlInputReader: Reads input from JSONL files.
- CsvInputReader: Reads input from CSV files (Mallet format).
- MalletTopicInferencer: Coordinates the process, identifies language, and manages inference.

Usage: python mallet_topic_inferencer.py -h
"""

import collections

import jpype
import jpype.imports
from dotenv import load_dotenv
from impresso_cookbook import setup_logging

import os
import logging
import argparse
import json
import csv
import tempfile
from pathlib import Path

from typing import List, Dict, Generator, Optional, Set, Iterable, Any

from .mallet2topic_assignment_jsonl import Mallet2TopicAssignment
from smart_open import open


from .language_inferencer import LanguageInferencer

from .input_reader import (
    InputReader,
    JsonlInputReader,
    CsvInputReader,
    ImpressoLinguisticProcessingJsonlInputReader,
)


log = logging.getLogger(__name__)
load_dotenv()


def save_text_as_csv(text: str) -> str:
    """
    Save the given text as a temporary CSV file with an arbitrary ID and return the file
    name.

    Args:
        text (str): The text to be saved in the CSV file.

    Returns:
        str: The name of the temporary CSV file.
    """
    # Create a temporary file with .csv suffix
    temp_csv_file = tempfile.NamedTemporaryFile(
        delete=False, mode="w", suffix=".csv", newline="", encoding="utf-8"
    )

    # Write the text to the CSV file with an arbitrary ID
    csv_writer = csv.writer(temp_csv_file, delimiter="\t")
    csv_writer.writerow(["ID", "DUMMYCLASS", "TEXT"])  # Header
    csv_writer.writerow(["USERINPUT-2024-10-24-a-i0042", "dummy_class", text])

    # Close the file to ensure all data is written
    temp_csv_file.close()

    return temp_csv_file.name


def load_json_config(config_file_path: str) -> Dict[str, Any]:
    with open(config_file_path, "r", encoding="utf-8") as file:
        return json.load(file)


def resolve_model_artifact(
    config_dir: str,
    artifacts: Dict[str, str],
    artifact_key: str,
    default_name: str,
) -> str:
    artifact_name = artifacts.get(artifact_key, default_name)
    if os.path.isabs(artifact_name) or artifact_name.startswith("s3://"):
        return artifact_name
    return os.path.join(config_dir, artifact_name)


def normalize_language_config(
    config: Dict[str, Any],
    config_file_path: str,
    language: str,
    model_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Normalize legacy and v3 model configs to one internal shape."""

    config_dir = model_dir or os.path.dirname(config_file_path)
    model_id = config.get("model_id", f"tm-{language}-all-v2.0")
    preprocessing = config.get("preprocessing", {})
    if not isinstance(preprocessing, dict):
        preprocessing = {}
    artifacts = config.get("artifacts", {})
    if not isinstance(artifacts, dict):
        artifacts = {}

    preprocessing_mode = preprocessing.get("mode", config.get("preprocessing_mode"))
    if not preprocessing_mode:
        preprocessing_mode = "v2.0-legacy"

    normalized = {
        **config,
        "language": config.get("language", language),
        "model_id": model_id,
        "topic_count": int(config.get("topic_count", 100)),
        "schema_version": str(config.get("schema_version", "2.0")),
        "preprocessing_mode": preprocessing_mode,
        "upos_filter": preprocessing.get(
            "upos_filter", config.get("upos_filter", config.get("uposFilter", []))
        ),
        "lowercase_token": bool(
            preprocessing.get("lowercase_token", config.get("lowercase_token", False))
        ),
        "min_lemmas": int(
            preprocessing.get(
                "min_lemmas",
                preprocessing.get(
                    "min_vocab_tokens",
                    config.get("min_lemmas", 10),
                ),
            )
        ),
        "min_unique_lemmas": int(preprocessing.get("min_unique_lemmas", 0)),
        "min_lemma_length": int(preprocessing.get("min_lemma_length", 3)),
        "include_titles": bool(preprocessing.get("include_titles", True)),
        "model_dir": config_dir,
        "pipe_path": resolve_model_artifact(
            config_dir, artifacts, "pipe", f"{model_id}.pipe"
        ),
        "inferencer_path": resolve_model_artifact(
            config_dir, artifacts, "inferencer", f"{model_id}.inferencer"
        ),
        "lemmatization_path": os.path.join(
            config_dir, f"{model_id}.vocab.lemmatization.tsv.gz"
        ),
        "mallet": config.get("mallet", {}),
    }

    if artifacts.get("vocab"):
        normalized["vocab_path"] = resolve_model_artifact(
            config_dir, artifacts, "vocab", f"{model_id}.vocab.tsv.bz2"
        )
    if artifacts.get("char_normalization"):
        normalized["char_normalization_path"] = resolve_model_artifact(
            config_dir,
            artifacts,
            "char_normalization",
            f"{model_id}.char-normalization.json",
        )
    return normalized


class MalletTopicInferencer:
    """
    MalletTopicInferencer class coordinates the process of reading input documents,
    identifying their language, and performing topic inference using Mallet models.
    """

    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.languages = set(args.languages)
        self.language_inferencers: Optional[Dict[str, LanguageInferencer]] = None
        self.language_lemmatizations: Optional[Dict[str, Dict[str, str]]] = None
        self.language_ma2ta_converters: Optional[Dict[str, Generator]] = None
        self.language_configs: Optional[Dict[str, Dict[str, str]]] = (
            self.init_language_configs(args)
        )
        self.input_reader = None
        self.inference_results: List[Dict[str, str]] = []
        self.language_dict: Dict[str, str] = {}
        self.seen_languages: Set[str] = set()
        self.stats = collections.Counter()
        self.initialized = False  # To check if the inferencer is initialized
        self.jvm_started = False  # To track if JVM is started by this instance
        self.output_path_base = args.output_path_base
        self.keep_tmp_files = args.keep_tmp_files
        self.include_lid_path = args.include_lid_path  # New argument
        self.inferencer_random_seed: int = args.inferencer_random_seed

        # Start the JVM and initialize inferencers
        self.start_jvm()
        self.initialize()
        self.git_version = (
            self.args.git_version
            if self.args.git_version
            else os.environ.get("GIT_VERSION", "unknown")
        )

        self.model_versions: Dict[str, str] = {}

    def __del__(self):
        # Shut down the JVM if it was started by this instance
        if self.jvm_started and jpype.isJVMStarted():
            jpype.shutdownJVM()
            logging.info("JVM shut down.")

    # Optionally, implement context manager methods for better resource handling
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # Shut down the JVM if it was started by this instance
        if self.jvm_started and jpype.isJVMStarted():
            jpype.shutdownJVM()
            logging.info("JVM shut down.")

        # Handle exceptions if needed
        if exc_type:
            logging.error(f"Exception: {exc_value}")
            log.error("Traceback: %s", traceback.format_exc())
            return False  # Re-raise exception
        return True  # Suppress exception if any

    def initialize(self):
        """Initialize the inferencers after JVM startup."""

        if not self.initialized:
            if self.language_configs is None:
                self.language_configs = self.init_language_configs(self.args)
            self.language_inferencers = self.init_language_inferencers(self.args)
            self.language_lemmatizations = self.init_language_lemmatizations(self.args)

            if self.args.output_format == "jsonl":
                self.language_ma2ta_converters = self.init_ma2ta_converters(self.args)
            if self.args.language_file:
                self.language_dict = self.read_language_file(self.args.language_file)
            if self.args.input:
                self.input_reader = self.build_input_reader(self.args)
            self.initialized = True  # Mark as initialized

    def start_jvm(self) -> None:
        """Start the Java Virtual Machine if not already started."""

        if not jpype.isJVMStarted():
            classpath = self.resolve_mallet_classpath()

            jpype.startJVM("--enable-native-access=ALL-UNNAMED", classpath=classpath)
            log.info(f"JVM started successfully with classpath {classpath}.")
            self.jvm_started = True  # Mark that this instance started the JVM
        else:
            log.warning("JVM already running.")

    def resolve_mallet_classpath(self) -> List[str]:
        current_dir = Path.cwd()
        source_dir = Path(__file__).resolve().parent
        repo_dir = source_dir.parent
        required_runtime = self.required_mallet_runtime()

        mallet_home = self.find_mallet_home(required_runtime, current_dir, repo_dir)
        if mallet_home:
            classpath = sorted(str(path) for path in (mallet_home / "lib").glob("*.jar"))
            if classpath:
                return classpath

        if required_runtime and required_runtime != "mallet":
            raise FileNotFoundError(
                f"Model config requires MALLET runtime {required_runtime}, but no "
                "matching runtime was found. Set MALLET_HOME to the MALLET 2.1.0 "
                "directory or vendor it in the inference repository."
            )

        fallback_classpath = [
            current_dir / "mallet/lib/mallet-deps.jar",
            current_dir / "mallet/lib/mallet.jar",
        ]
        if not all(path.exists() for path in fallback_classpath):
            fallback_classpath = [
                repo_dir / "mallet/lib/mallet-deps.jar",
                repo_dir / "mallet/lib/mallet.jar",
            ]
        if not all(path.exists() for path in fallback_classpath):
            raise FileNotFoundError(
                "Could not locate MALLET jars. Set MALLET_HOME or run from the "
                "inference repository root."
            )
        return [str(path) for path in fallback_classpath]

    def required_mallet_runtime(self) -> Optional[str]:
        runtimes = set()
        for config in (self.language_configs or {}).values():
            mallet = config.get("mallet", {})
            if isinstance(mallet, dict) and mallet.get("runtime"):
                runtimes.add(str(mallet["runtime"]))
        if len(runtimes) > 1:
            raise ValueError(f"Conflicting MALLET runtimes in configs: {sorted(runtimes)}")
        return next(iter(runtimes), None)

    def find_mallet_home(
        self, runtime: Optional[str], current_dir: Path, repo_dir: Path
    ) -> Optional[Path]:
        candidates = []
        if os.environ.get("MALLET_HOME"):
            candidates.append(Path(os.environ["MALLET_HOME"]))
        if runtime:
            candidates.extend(
                [
                    current_dir / runtime,
                    repo_dir / runtime,
                    current_dir.parent / runtime,
                    repo_dir.parent / runtime,
                ]
            )
        for candidate in candidates:
            if (candidate / "lib").is_dir():
                return candidate
        return None

    def run(self) -> None:
        """Main execution method. Either processing an input file or waiting for
        interactive use."""

        if self.args.input:
            self.process_input_file()
        for key, value in sorted(self.stats.items()):
            log.info(f"STATS: {key}: {value}")

    def read_language_file(self, language_file: str) -> Dict[str, str]:
        """Read the language file (JSONL) and return a dictionary of document_id ->
        language."""

        language_dict = {}
        with open(language_file, "r", encoding="utf-8") as f:
            for line in f:
                data = json.loads(line)
                doc_id = data.get("doc_id")
                language = data.get("language")
                if doc_id and language:
                    language_dict[doc_id] = language
        return language_dict

    @staticmethod
    def load_lemmatization_file(
        lemmatization_file_path: str,
        bidi: bool = False,
        lowercase: bool = False,
        ignore_pos: bool = True,
    ) -> Dict[str, str]:
        """
        Load lemmatization data from the file.
        :param lemmatization_file_path: Path to the lemmatization file.
        :return: A dictionary mapping tokens to their corresponding lemmas.
        """

        token2lemma = {}
        n = 0
        logging.info(
            "Reading lemmatization entries from %s with setting: lowercase=%s"
            " ignore_pos=%s ",
            lemmatization_file_path,
            lowercase,
            ignore_pos,
        )
        with open(lemmatization_file_path, "r", "utf-8") as file:
            for line in file:
                token, _, lemma = line.strip().split("\t")
                if lowercase:
                    token2lemma[token.lower()] = lemma.lower()
                else:
                    token2lemma[token] = lemma
                n += 1

        logging.info(
            "Read %d lemmatization entries from %s", n, lemmatization_file_path
        )
        return token2lemma

    def init_language_configs(
        self, args: argparse.Namespace
    ) -> Dict[str, Dict[str, str]]:
        """Build a mapping of languages to their respective Mallet configurations."""

        language_configs = {}
        if getattr(args, "resolved_language_configs", None):
            return args.resolved_language_configs
        for language in args.languages:
            config_key = f"{language}_config"
            if getattr(args, config_key, None):
                config_file = getattr(args, config_key)
                language_configs[language] = normalize_language_config(
                    self.load_config_file(config_file), config_file, language
                )
                log.info(
                    "Loaded configuration for language: %s : %s : %s",
                    language,
                    config_file,
                    language_configs[language],
                )
            else:
                log.info(
                    "Configuration file for language: %s not provided by"
                    " arguments. Skipping.",
                    language,
                )
        return language_configs

    def load_config_file(self, config_file_path: str) -> Dict[str, Any]:
        """
        Load JSON configuration data from the file.

        :param config_file_path: Path to the configuration file.
        :return: A dictionary containing the configuration data.
        """

        try:
            with open(config_file_path, "r", encoding="utf-8") as file:
                config_data = json.load(file)
                log.debug(
                    f"Loaded configuration data from {config_file_path}: {config_data}"
                )
                return config_data
        except json.JSONDecodeError as e:
            log.error(
                f"JSON decode error in configuration file {config_file_path}: {e}"
            )
        except Exception as e:
            log.error(f"Error reading configuration file {config_file_path}: {e}")
        log.info("Continuing with empty configuration")
        return {}

    def init_language_lemmatizations(
        self, args: argparse.Namespace
    ) -> Dict[str, Dict[str, str]]:
        """Build a mapping of languages to their respective lemmatization
        dictionaries."""

        language_lemmatizations: Dict[str, Dict[str, str]] = {}
        for language in args.languages:
            lemmatization_key = f"{language}_lemmatization"
            if getattr(args, lemmatization_key, None):
                lemmatization_file = getattr(args, lemmatization_key)
                language_lemmatizations[language] = self.load_lemmatization_file(
                    lemmatization_file
                )
            else:
                log.info(
                    f"Lemmatization file for language: {language} not provided by"
                    " arguments. Skipping."
                )
        return language_lemmatizations

    def init_ma2ta_converters(self, args: argparse.Namespace) -> Dict[str, Generator]:
        """
        Build a mapping of languages to their respective Mallet2TopicAssignment
        converters.

        Args:
            args (argparse.Namespace): The arguments namespace containing the
            configuration for initializing the converters. It should include:
            - languages (List[str]): List of languages to initialize converters for.
            - <language>_model_id (str): Model ID for each language.
            - <language>_topic_count (int): Topic count for each language.
            - min_p (float): Minimum probability threshold.
            - lingproc_run_id (Optional[str]): Linguistic processing run ID.
            - git_version (Optional[str]): Git version.
            - impresso_model_id (Optional[str]): Impresso model ID.

        Returns:
            Dict[str, Generator]: A dictionary mapping each language to its respective
            Mallet2TopicAssignment converter generator.
        """

        ma2ta_converters = {}
        for language in args.languages:
            logging.info(
                "Initializing Mallet2TopicAssignment converter for %s", language
            )
            topic_model_id = getattr(args, f"{language}_model_id")
            if "{lang}" in topic_model_id:
                topic_model_id.format(lang=language)
            ma2ta_args = [
                "--output",
                "<generator>",
                "--topic_model",
                topic_model_id,
                "--topic_count",
                str(getattr(args, f"{language}_topic_count")),
                "--lg",
                language,
                "--min-p",
                str(args.min_p),
            ]
            if self.args.lingproc_run_id:
                ma2ta_args.extend(["--lingproc-run_id", self.args.lingproc_run_id])
            if self.args.git_version:
                ma2ta_args.extend(["--git-version", self.args.git_version])
            if self.args.impresso_model_id:
                ma2ta_args.extend(["--impresso-model-id", self.args.impresso_model_id])
            ma2ta_converters[language] = Mallet2TopicAssignment.main(ma2ta_args).run()
        return ma2ta_converters

    def identify_language(self, document_id: str, text: str) -> str:
        """Identify the language of the text using the language file or a dummy
        method."""

        # Check if the document ID is in the language dictionary
        if document_id in self.language_dict:
            return self.language_dict[document_id]
        # Placeholder: Assume German ("de") for now if not found in the dictionary
        return "de"

    def init_language_inferencers(
        self, args: argparse.Namespace
    ) -> Dict[str, LanguageInferencer]:
        """Build a mapping of languages to their respective inferencers

        Includes the vectorizer pipe for each language as well.
        """

        language_inferencers: Dict[str, LanguageInferencer] = {}
        for language in args.languages:
            inferencer_key = f"{language}_inferencer"
            pipe_key = f"{language}_pipe"
            if getattr(args, inferencer_key, None) and getattr(args, pipe_key, None):
                mallet_config = (self.language_configs or {}).get(language, {}).get(
                    "mallet", {}
                )
                rewrite_pipe = not (
                    isinstance(mallet_config, dict)
                    and mallet_config.get("runtime") == "mallet-2.1.0"
                )
                language_inferencers[language] = LanguageInferencer(
                    language=language,
                    inferencer_file=getattr(args, inferencer_key),
                    pipe_file=getattr(args, pipe_key),
                    keep_tmp_files=args.keep_tmp_files,
                    random_seed=self.inferencer_random_seed,
                    rewrite_pipe=rewrite_pipe,
                )
            else:
                log.info(
                    f"Inferencer or pipe file for language: {language} not provided by"
                    " arguments. Skipping."
                )
        return language_inferencers

    def build_input_reader(self, args: argparse.Namespace) -> InputReader:
        """Select the appropriate input reader based on the input format."""

        if args.input_format == "jsonl":
            return JsonlInputReader(args.input)
        elif args.input_format == "csv":
            return CsvInputReader(args.input)
        elif args.input_format == "impresso":
            return ImpressoLinguisticProcessingJsonlInputReader(
                args.input,
                self.language_lemmatizations,
                self.language_configs,
                ci_ids=self.args.ci_ids,
            )
        else:
            raise ValueError(f"Unsupported input format: {args.input_format}")

    def process_input_file(self) -> None:
        """Process the input file, identify language, and apply the appropriate Mallet
        model"""

        logging.info("Processing input file: %s", self.args.input)
        temp_files_by_language = self.write_language_specific_csv_files()

        doctopics_files = self.run_topic_inference(temp_files_by_language)
        logging.info(doctopics_files)
        if self.args.output_format == "csv":
            self.merge_inference_results(doctopics_files)
        elif self.args.output_format == "jsonl":
            self.merge_inference_results_jsonl(doctopics_files)

    def infer_texts(self, texts: Iterable[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        Infer topics for multiple texts provided as an iterable of dicts.

        Each dict should have keys: 'text', 'language', and 'id'.

        Returns a list of result dicts, each containing 'doc_id', 'language', and
        'topic_distribution'.
        """

        if not self.initialized:
            self.initialize()

        # Group texts by language
        texts_by_language = collections.defaultdict(list)
        for item in texts:
            text = item["text"]
            language = item["language"]
            doc_id = item.get("id", "doc1")
            if language not in self.languages:
                logging.warning(
                    f"Language '{language}' not supported. Skipping document {doc_id}."
                )
                continue
            lemmas = self.analyze_text(text, language)
            if not lemmas:
                logging.warning("No lemmas found in document %s: %s", doc_id, text)
            texts_by_language[language].append((doc_id, " ".join(lemmas)))

        results = []

        # For each language, process the texts
        for language, docs in texts_by_language.items():
            # Create a temporary CSV file with the input texts
            with tempfile.NamedTemporaryFile(
                delete=False,
                mode="w",
                suffix=f".{language}.csv",
                newline="",
                encoding="utf-8",
            ) as temp_csv_file:
                csv_writer = csv.writer(
                    temp_csv_file,
                    delimiter="\t",
                    escapechar=None,
                    quoting=csv.QUOTE_NONE,
                )

                for doc_id, text in docs:
                    csv_writer.writerow([doc_id, language, text])
                csv_file_path = temp_csv_file.name

            # Run topic inference
            inferencer = self.language_inferencers[language]
            doctopics_file = inferencer.run_csv2topics(csv_file_path)

            # Read the results from the doctopics file
            with open(doctopics_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("#"):
                        continue
                    parts = line.strip().split("\t")
                    # The format is: <doc_index> <doc_id> <topic_0_weight> <topic_1_weight> ...
                    # doc_index = parts[0]
                    doc_id = parts[1]
                    topic_weights = parts[2:]
                    topic_distribution = [float(x) for x in topic_weights]

                    result = {
                        "doc_id": doc_id,
                        "language": language,
                        "topic_distribution": topic_distribution,
                    }
                    results.append(result)

            if logging.getLogger().getEffectiveLevel() != logging.DEBUG:
                logging.info("Deleting temporary file: %s", csv_file_path + ".mallet")
                os.remove(csv_file_path + ".mallet")

        return results

    def infer_text(
        self, text: str, language: str, doc_id: str = "doc1"
    ) -> Dict[str, Any]:
        """
        Infer topics for a single text input.

        Returns a result dict containing 'doc_id', 'language', and 'topic_distribution'.
        """

        items = [{"text": text, "language": language, "id": doc_id}]
        results = self.infer_texts(items)
        if results:
            return results[0]
        else:
            return {}

    def merge_inference_results_jsonl(self, doctopics_files_by_language):
        """
        Merges inference results from multiple JSONL files into a single output file.
        Args:
            doctopics_files_by_language (dict): A dictionary where keys are language
              codes and values are paths to the corresponding doctopics files.
        Returns:
            None

        This method processes the given doctopics files by language, converts them using
        the Mallet2TopicAssignment tool, and writes the merged results to the output
        file specified in self.args.output. It also updates the content items statistics
        and deletes the temporary files if the logging level is not DEBUG.
        """

        m2ta_converters = {}
        for lang, doctopics_file in doctopics_files_by_language.items():
            args = ["--output", "<generator>"]
            topic_model_id = self.args.__dict__[f"{lang}_model_id"]
            if "{lang}" in topic_model_id:
                topic_model_id.format(lang=lang)
            args += [
                "--git-version",
                self.args.git_version,
                "--topic_model",
                topic_model_id,
                "--topic_count",
                str(self.args.__dict__[f"{lang}_topic_count"]),
                "--lang",
                lang,
                "--min-p",
                str(self.args.min_p),
                doctopics_file,  # input comes last!
            ]
            if self.args.lingproc_run_id:
                args.extend(["--lingproc-run_id", self.args.lingproc_run_id])
            if self.args.git_version:
                args.extend(["--git-version", self.args.git_version])
            if self.args.impresso_model_id:
                args.extend(["--impresso-model-id", self.args.impresso_model_id])
            m2ta_converters[lang] = Mallet2TopicAssignment.main(args).run()

        with open(self.args.output, "w", encoding="utf-8") as out_f:
            for lang, m2ta_converter in m2ta_converters.items():
                for row in m2ta_converter:
                    self.stats["content_items"] += 1
                    if self.include_lid_path:
                        row["lid_path"] = self.args.language_file
                    print(
                        json.dumps(row, ensure_ascii=False, separators=(",", ":")),
                        file=out_f,
                    )
        if not self.keep_tmp_files:
            for doctopics_file in doctopics_files_by_language.values():
                logging.debug("Deleting temporary file: %s", doctopics_file)
                os.remove(doctopics_file)

    def merge_inference_results(
        self, doctopics_files_by_language: Dict[str, str]
    ) -> None:
        """
        Merges topic inference results from multiple languages into a single CSV file.
        Args:
            doctopics_files_by_language (Dict[str, str]): A dictionary where keys are
              language codes and values are file paths to the topic distribution files
              for each language.
        Returns:
            None

        The method reads topic distribution files for each language, appends the
        language code to the document ID, and writes the merged results into a single
        output file specified by `self.args.output`.
        """
        logging.info(
            "Saving CSV inference results into file %s from multiple languages: %s",
            self.args.output,
            doctopics_files_by_language,
        )
        with open(self.args.output, "w", encoding="utf-8") as out_f:
            logging.info("Writing merged inference results to: %s", self.args.output)
            for language, doctopics_file in doctopics_files_by_language.items():
                with open(doctopics_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("#"):
                            continue
                        doc_id, topic_dist = line.strip().split("\t", 1)
                        print(
                            doc_id + "__" + language,
                            topic_dist,
                            sep="\t",
                            end="\n",
                            file=out_f,
                        )
        if not self.keep_tmp_files:
            for doctopics_file in doctopics_files_by_language.values():
                logging.info("Deleting temporary file: %s", doctopics_file)
                os.remove(doctopics_file)

    def write_language_specific_csv_files(self) -> Dict[str, str]:
        """Read documents and write to language-specific temporary files"""
        tsv_files_by_language = {}

        for document_id, lang, text in self.input_reader.read_documents():
            if lang in self.languages:
                language_code = lang
            else:
                language_code = self.identify_language(document_id, text)
            self.stats["LANGUAGE: " + language_code] += 1
            if language_code not in self.languages:
                continue

            if language_code not in tsv_files_by_language:
                if self.output_path_base:
                    temp_file_path = f"{self.output_path_base}.{language_code}.tsv"
                    os.makedirs(os.path.dirname(temp_file_path), exist_ok=True)
                    tsv_files_by_language[language_code] = open(
                        temp_file_path, "w", encoding="utf-8"
                    )
                else:
                    tsv_files_by_language[language_code] = tempfile.NamedTemporaryFile(
                        delete=False,
                        mode="w",
                        suffix=f".{language_code}.tsv",
                        encoding="utf-8",
                    )
                logging.debug(
                    "Writing documents for language: %s in temp file: %s",
                    language_code,
                    tsv_files_by_language[language_code].name,
                )

            print(
                document_id,
                language_code,
                text,
                sep="\t",
                end="\n",
                file=tsv_files_by_language[language_code],
            )

        # Close all temporary files
        for temp_file in tsv_files_by_language.values():
            temp_file.close()

        # noinspection PyShadowingNames
        result = {
            lang: temp_file.name for lang, temp_file in tsv_files_by_language.items()
        }
        return result

    def run_topic_inference(
        self, language_specific_csv_files: Dict[str, str]
    ) -> Dict[str, str]:
        """Run inference for each language"""
        doctopics_files_by_language = {}
        for language_code, csv_file in language_specific_csv_files.items():
            inferencer = self.language_inferencers.get(language_code)
            if not inferencer:
                log.error(f"No inferencer found for language: {language_code}")
                continue

            doctopics_file = inferencer.run_csv2topics(
                csv_file, delete_mallet_file_after=not self.keep_tmp_files
            )
            doctopics_files_by_language[language_code] = doctopics_file

        logging.debug("Resulting doctopic files: %s", doctopics_files_by_language)
        return doctopics_files_by_language

    def write_results_to_output(self) -> None:
        """Write the final merged inference results to the output file."""
        with open(self.args.output, "w", encoding="utf-8") as out_file:
            for result in self.inference_results:
                out_file.write(json.dumps(result) + "\n")
        log.info(f"All inferences merged and written to {self.args.output}")


if __name__ == "__main__":
    languages = ["de", "fr", "en", "lb"]  # You can add more languages as needed
    parser = argparse.ArgumentParser(description="Mallet Topic Inference in Python")

    parser.add_argument(
        "--loglevel",
        "--log-level",
        "--level",
        dest="log_level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level (default: %(default)s)",
    )
    parser.add_argument(
        "--input",
        help=(
            "Path to input file. If omitted, no file processing is done but you can use"
            " infert_topics() method for more interactive use."
        ),
    )
    parser.add_argument(
        "--input-format",
        choices=["impresso", "jsonl", "csv"],
        default="jsonl",
        help=(
            "Format of the input file (default: %(default)s). 'impresso' is a JSONL"
            " file containing linguistic processing data. 'jsonl' is a JSONL file with"
            " doc_id, text and language. 'csv' is a mallet three-column CSV file"
            " (DOCID, CLASS, LEMMAS)."
        ),
    )
    parser.add_argument(
        "--languages",
        nargs="+",
        default=languages,
        help="List of languages to support (%(default)s)",
    )
    parser.add_argument(
        "--ci_ids", nargs="+", help="List of ci_ids to process", required=False
    )
    parser.add_argument(
        "--output",
        help="Path to final output file. (%(default)s)",
        default="output.jsonl",
    )
    parser.add_argument(
        "--output-format",
        choices=["jsonl", "csv"],
        help=(
            "Format of the output file: csv: raw Mallet output with docids patched into"
            " numericID-LANG, jsonl: impresso JSONL format"
        ),
    )
    parser.add_argument(
        "--lemmatization_mode",
        choices=["v2.0-legacy", "normalized-lemma-vocab-v1"],
        default="v2.0-legacy",
        help=(
            "Fallback lemmatization mode to use when no model config declares one."
        ),
    )
    parser.add_argument(
        "--min-p",
        type=float,
        default=0.02,
        help=(
            "Minimum probability threshold to include the topic in the output (Default:"
            " %(default)s)"
        ),
    )
    parser.add_argument(
        "--git-version",
        help="Specify the git version to use",
    )
    parser.add_argument(
        "--lingproc-run_id",
        help=(
            "Add the impresso linguistic processing run id as property"
            " 'lingproc_run_id' to the output for data traceability."
        ),
    )
    parser.add_argument(
        "--logfile",
        "--log-file",
        dest="log_file",
        help="Path to the log file",
        default=None,
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Do not log to console, only to the log file (if specified).",
    )
    for lang in languages:
        parser.add_argument(
            f"--{lang}_config",
            help=(
                "Configuration file of topic modeling for language residing in the"
                " model_dir. If provided,--model_dir (will be derived as directory of"
                f" configuration file) --{lang}_topic_count  options are oveset from"
                " configuration file . "
            ),
        )
    parser.add_argument(
        "--language-file",
        help="Path to JSONL containing document_id to language mappings",
        required=False,
    )
    parser.add_argument(
        "--keep-tmp-files",
        "--keep_tmp_files",
        action="store_true",
        help="Keep temporary files (Default: %(default)s)",
    )
    parser.add_argument("--model_dir", help="Path to model directory")
    parser.add_argument(
        "--output_path_base",
        help=(
            "Base path for temporary files. If not specified, uses system temporary"
            " files. And default to removing intermediate files."
        ),
        required=False,
    )
    parser.add_argument(
        "--include-lid-path",
        action="store_true",
        help="Include the LID file path in the output JSON for traceability",
    )
    parser.add_argument(
        "--inferencer-random-seed",
        type=int,
        default=42,
        help="Set the random seed for the inferencer (Default: %(default)s)",
    )
    parser.add_argument(
        "--impresso-model-id",
        help="The model id stored as 'model_id' in the output.",
    )
    # Dynamically generate arguments for each language's inferencer and pipe files
    for lang in languages:
        parser.add_argument(
            f"--{lang}_inferencer",
            help=f"Path to {lang} inferencer file",
        )
        parser.add_argument(f"--{lang}_pipe", help=f"Path to {lang} pipe file")
        parser.add_argument(
            f"--{lang}_lemmatization", help=f"Path to {lang} lemmatization file"
        )
        parser.add_argument(f"--{lang}_vocab", help=f"Path to {lang} v3 vocabulary")
        parser.add_argument(
            f"--{lang}_char_normalization",
            help=f"Path to {lang} v3 character normalization JSON",
        )
    # Dynamically generate arguments for each language's inferencer and pipe files
    for lang in languages:
        parser.add_argument(
            f"--{lang}_model_id",
            help="Model ID can take a {lang} format placeholder (%(default)s)",
        )
    for lang in languages:
        parser.add_argument(
            f"--{lang}_topic_count",
            help="Number of topics of model (%(default)s). ",
        )

    args = parser.parse_args()

    setup_logging(args.log_level, args.log_file, force=True)
    if args.quiet:
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            if isinstance(handler, logging.StreamHandler) and not isinstance(
                handler, logging.FileHandler
            ):
                root_logger.removeHandler(handler)
    log.info("Script called with args: %s", args)

    logging.info("Setting up MalletTopicInferencer")
    # Automatically construct file paths if not explicitly specified
    args.resolved_language_configs = {}
    for lang in args.languages:
        if config_path := getattr(args, f"{lang}_config"):
            if not os.path.exists(config_path):
                raise FileNotFoundError(f"Config file not found: {config_path}")

            config = normalize_language_config(
                load_json_config(config_path), config_path, lang
            )

            model_dir = config["model_dir"]
            model_id = config["model_id"]
            setattr(args, f"{lang}_model_id", model_id)
            setattr(args, f"{lang}_topic_count", config["topic_count"])
            logging.info(
                "Config's %s topic count for language %s used: %s",
                config_path,
                lang,
                config["topic_count"],
            )

        else:
            model_id = getattr(args, f"{lang}_model_id")
            if not args.model_dir:
                logging.error(
                    "Model directory option --model-dir  not provided. Please provide a"
                    " model directory or specify the config json path."
                )
                exit(1)
            model_dir = args.model_dir
            config_path = os.path.join(model_dir, f"{model_id}.config.json")
            if os.path.exists(config_path):
                logging.info(
                    "Automatically setting config json path to %s", config_path
                )
                setattr(args, f"{lang}_config", config_path)
                config = normalize_language_config(
                    load_json_config(config_path), config_path, lang
                )
            else:
                config = normalize_language_config(
                    {
                        "model_id": model_id,
                        "topic_count": getattr(args, f"{lang}_topic_count", 100),
                        "preprocessing_mode": args.lemmatization_mode,
                    },
                    config_path,
                    lang,
                    model_dir=model_dir,
                )

        pipe_path = config["pipe_path"]
        inferencer_path = config["inferencer_path"]
        lemmatization_path = config["lemmatization_path"]

        if not getattr(args, f"{lang}_pipe") and os.path.exists(pipe_path):
            logging.info("Automatically setting pipe path to %s", pipe_path)
            setattr(args, f"{lang}_pipe", pipe_path)
        if not getattr(args, f"{lang}_inferencer") and os.path.exists(inferencer_path):
            logging.info("Automatically setting inferencer path to %s", inferencer_path)
            setattr(args, f"{lang}_inferencer", inferencer_path)
        if not getattr(args, f"{lang}_lemmatization") and os.path.exists(
            lemmatization_path
        ):
            logging.info(
                "Automatically setting lemmatization path to %s", lemmatization_path
            )
            setattr(args, f"{lang}_lemmatization", lemmatization_path)
        if config.get("vocab_path"):
            setattr(args, f"{lang}_vocab", config["vocab_path"])
        if config.get("char_normalization_path"):
            setattr(args, f"{lang}_char_normalization", config["char_normalization_path"])
        args.resolved_language_configs[lang] = config
    if args.output_path_base:
        args.keep_tmp_files = True
        if args.output == "output.jsonl":  # the default should be overwritten
            if args.output_format == "jsonl":
                args.output = args.output_path_base + ".jsonl"
            elif args.output_format == "csv":
                args.output = args.output_path_base + ".csv"
            else:
                logging.error("Unsupported output format: %s", args.output_format)
                exit(1)
    if not args.output_format:
        if "jsonl" in args.output:
            args.output_format = "jsonl"
        else:
            args.output_format = "csv"
        logging.warning("Unspecified output format set to %s", args.output_format)
    valid_languages = []
    for lang in args.languages:
        if not getattr(args, f"{lang}_inferencer") or not getattr(args, f"{lang}_pipe"):
            logging.warning(
                "Inferencer or pipe file not provided for language: %s. Ignoring"
                " content items for this language.",
                lang,
            )
            args.resolved_language_configs.pop(lang, None)
        else:
            valid_languages.append(lang)
    args.languages = valid_languages
    logging.info(
        "Performing monolingual topic inference for the following languages: %s",
        args.languages,
    )
    logging.info("MalletTopicInferencer setup finished.")
    logging.info("MalletTopicInferencer Class Arguments: %s", args)
    app = MalletTopicInferencer(args)
    app.run()
