#!/usr/bin/env python3
"""

This module provides the LanguageInferencer class, which manages Mallet topic inference
for a specific language. It loads the inferencer and pipe file during initialization and
provides functionality to perform topic inference on input files.

Classes:
    LanguageInferencer: A class to manage Mallet inferencing for a specific language.

Usage example:
    inferencer = LanguageInferencer(language='en', inferencer_file='path/to/inferencer',
        pipe_file='path/to/pipe')
    topics = inferencer.run_csv2topics(csv_file='path/to/csv')


    Attributes:
        language (str): The language for which to perform topic inference.
        inferencer_file (str): Path to the Mallet inferencer file.
        inferencer (InferTopics): Instance of Mallet's InferTopics class.
        pipe_file (str): Path to the Mallet pipe file.
        vectorizer (MalletVectorizer): Instance of MalletVectorizer for vectorizing
            input files.
        keep_tmp_files (bool): Flag to indicate whether to keep temporary files.

    Methods:
        run_csv2topics(csv_file: str, delete_mallet_file_after: bool = True) -> Dict[str, str]:
            Perform topic inference on a single input file and return a dictionary of
            document_id -> topic distributions.
"""

import os
import logging
import shutil
import tempfile
from typing import Dict
from .mallet_vectorizer import MalletVectorizer


class LanguageInferencer:
    """
    A class to manage Mallet inferencing for a specific language.
    Loads the inferencer and pipe file during initialization.
    """

    def __init__(
        self,
        language: str,
        inferencer_file: str,
        pipe_file: str,
        keep_tmp_files: bool = False,
        random_seed: int = 42,
        rewrite_pipe: bool = True,
    ) -> None:
        # Import after JVM is started, so that the classes are available
        # noinspection PyUnresolvedReferences
        from cc.mallet.topics.tui import InferTopics  # type: ignore

        self.language = language
        self.inferencer_file = inferencer_file
        self.inferencer = InferTopics()
        self.pipe_file = pipe_file
        self.vectorizer = MalletVectorizer(
            language=language,
            pipe_file=self.pipe_file,
            keep_tmp_file=keep_tmp_files,
            rewrite_pipe=rewrite_pipe,
        )
        self.keep_tmp_files = keep_tmp_files
        self.random_seed = random_seed
        self.rewrite_pipe = rewrite_pipe

        if not os.path.exists(self.inferencer_file):
            raise FileNotFoundError(
                f"Inferencer file not found: {self.inferencer_file}"
            )

    def run_csv2topics(
        self, csv_file: str, delete_mallet_file_after: bool = True
    ) -> Dict[str, str]:
        """
        Perform topic inference on a single input file.
        The input file should be in the format expected by Mallet.
        Returns a dictionary of document_id -> topic distributions.
        """

        if self.rewrite_pipe:
            # Legacy MALLET rewrites --use-pipe-from inputs; isolate the model pipe.
            with tempfile.NamedTemporaryFile(delete=True) as temp_pipe_file:
                shutil.copyfile(self.pipe_file, temp_pipe_file.name)
                return self._run_csv2topics_with_pipe(
                    csv_file, temp_pipe_file.name, delete_mallet_file_after
                )

        return self._run_csv2topics_with_pipe(
            csv_file, self.pipe_file, delete_mallet_file_after
        )

    def _run_csv2topics_with_pipe(
        self, csv_file: str, pipe_file: str, delete_mallet_file_after: bool
    ) -> str:
        vectorizer = MalletVectorizer(
            language=self.language,
            pipe_file=pipe_file,
            keep_tmp_file=self.keep_tmp_files,
            rewrite_pipe=self.rewrite_pipe,
        )
        mallet_file = vectorizer.run_csv2vectors(csv_file)

        topics_file = mallet_file + ".doctopics"

        arguments = [
            "--input",
            mallet_file,
            "--inferencer",
            self.inferencer_file,
            "--output-doc-topics",
            topics_file,
            "--random-seed",
            str(self.random_seed),
        ]

        logging.info("Calling mallet InferTopics: %s", arguments)

        self.inferencer.main(arguments)
        logging.debug("InferTopics call finished.")

        if (
            logging.getLogger().getEffectiveLevel() != logging.DEBUG
            and delete_mallet_file_after
            and not self.keep_tmp_files
        ):
            os.remove(mallet_file)
            logging.debug("Deleting temporary mallet input file: %s", mallet_file)

        return topics_file
