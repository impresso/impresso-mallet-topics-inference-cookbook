#!/usr/bin/python3

"""
Script to filter text content to the excpected texual input format that mallet will
convert to a mallet file and then use for topic inference.

# filtering
Original Makefile entry
```
$(FULL)/fr.txt: $(AGGREGATED)/fr.txt
  python3 $(LIB)/freq_filter.py --inputFolder $(LINGUISTIC_PREPROCESSING) --freqDist $< \
  --lowerBound $(FR-LOWER-THRESHOLD) --upperBound $(FR-UPPER-THRESHOLD) \
  --posFilter $(POS) --outputFile $@ \
  --negativeList $(NEGLEMMA)/$(@F) --lemmatisation $(LEMMA)/$(addsuffix .json, $(basename $(@F))) \
  --language $(basename $(@F)) \
  --addLemmas $(LEMMA)/$(addsuffix .additional.txt, $(basename $(@F))) \
  --cores $(CORES) \
  > $(LOGS)/full.fr.log 2>&1
```

"""

import codecs
import json
import bz2
import argparse
import random
import glob
from collections import defaultdict
from multiprocessing import Pool
import logging

# Logger setup
log = logging.getLogger(__name__)

__author__ = "Phillip Ströbel"
__email__ = "pstroebel@cl.uzh.ch"
__organisation__ = "Institute of Computational Linguistics, University of Zurich"
__copyright__ = "UZH, 2024"
__status__ = "development"

random.seed(42)


class MainApplication(object):
    def __init__(self, args):
        self.args = args
        self.filter_words = set()
        self.negative_lemmas = set()
        self.lemma_dict = defaultdict(str)

    def load_frequency_distribution(self):
        with codecs.open(self.args.freqDist, "r", "utf-8") as f:
            for line in f:
                freq, tok = line.strip().split("\t")
                if self.args.lowerBound < int(freq) < self.args.upperBound:
                    self.filter_words.add(tok)

    def load_negative_lemmas(self):
        with codecs.open(self.args.negativeList, "r", "utf-8") as n:
            for line in n:
                self.negative_lemmas.add(line.strip())

    def load_lemma_dict(self):
        if self.args.lemmatisation.endswith(
            ".txt"
        ):  # we assume tsv output from gertwol
            with codecs.open(self.args.lemmatisation, "r", "utf-8") as g:
                for line in g:
                    tok, pos, lemma = line.strip().split("\t")
                    if tok.isalnum():
                        self.lemma_dict[tok] = lemma
        else:  # we expect a json file
            lemmafile = json.load(open(self.args.lemmatisation, "r"))
            for upos in lemmafile:
                if upos in self.args.posFilter:
                    for tok, lemma in lemmafile[upos].items():
                        self.lemma_dict[tok] = lemma

        if self.args.addLemmas:
            with open(self.args.addLemmas, "r") as addlemmas:
                for line in addlemmas:
                    try:
                        tok, pos, lemma = line.strip().split("\t")
                        if tok.isalnum():
                            self.lemma_dict[tok] = lemma
                    except ValueError:
                        continue

    def filter(self, jsonfile):
        """
        Filters the content of a given JSON file.
        """
        filtered_texts = defaultdict(str)
        try:
            input_file = bz2.BZ2File(jsonfile, "r")
            for line in input_file.readlines():
                json_line = json.loads(line)
                article_id = json_line["id"]
                article = list()
                for sent in json_line["sents"]:
                    lang = sent["lg"]
                    if lang == self.args.language:
                        for index, tok in enumerate(sent["tok"]):
                            if "l" in tok and "p" in tok:
                                if not self.lemma_dict:
                                    article.append(tok["l"])
                                else:
                                    if (
                                        tok["p"] in self.args.posFilter
                                        and tok["t"] in self.filter_words
                                        and tok["l"] not in self.negative_lemmas
                                        and tok["l"].lower() not in self.negative_lemmas
                                        and len(tok["l"]) > 2
                                    ):
                                        if tok["t"] in self.lemma_dict.keys():
                                            if lang == "fr":
                                                try:
                                                    article.append(
                                                        self.lemma_dict[tok["l"]][0]
                                                    )
                                                except IndexError:
                                                    log.warning(
                                                        "Could not append token %s to"
                                                        " text.",
                                                        tok["t"],
                                                    )
                                            else:
                                                article.append(
                                                    self.lemma_dict[tok["l"]]
                                                )
                    filtered_texts[article_id] = " ".join(str(t) for t in article)

            with codecs.open("%s" % self.args.outputFile, "a", "utf-8") as outfile:
                for aid, text in filtered_texts.items():
                    outfile.write("%s\tDUMMY\t%s\n" % (aid, text))

        except (EOFError, OSError) as e:
            log.error("Could not process %s: %s", jsonfile, e)

    def run(self):
        self.load_frequency_distribution()
        self.load_negative_lemmas()
        self.load_lemma_dict()

        files = glob.glob("%s/*/*.bz2" % self.args.inputFolder)

        with Pool(processes=self.args.cores) as pool:
            pool.map(self.filter, files)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Filter texts using a frequency distribution file."
    )
    parser.add_argument(
        "-i", "--inputFolder", help="Path to jsonl.bz2 files for input", required=True
    )
    parser.add_argument(
        "-o",
        "--outputFile",
        help="Path to file to which articles are saved",
        required=True,
    )
    parser.add_argument(
        "-f",
        "--freqDist",
        help="Frequency distribution file in format FREQ TAB WORD",
        required=True,
    )
    parser.add_argument(
        "-l",
        "--lowerBound",
        help="Threshold (int), all words below are ignored",
        type=int,
        required=True,
    )
    parser.add_argument(
        "-u",
        "--upperBound",
        help="Threshold (int), all words above are ignored",
        type=int,
        required=True,
    )
    parser.add_argument(
        "-p",
        "--posFilter",
        help="PoS tags to be included in the filtered text",
        nargs="+",
        choices=["NOUN", "PROPN", "VERB", "ADJ"],
        required=True,
    )
    parser.add_argument(
        "-n", "--negativeList", help="Lemmas to be excluded", required=True
    )
    parser.add_argument(
        "-L", "--language", help="ISO language two letter, e.g., 'de'", required=True
    )
    parser.add_argument(
        "-N", "--lemmatisation", help="Lemmas to be included", required=False
    )
    parser.add_argument(
        "-c", "--cores", help="Number of cores to use", type=int, required=True
    )
    parser.add_argument(
        "-a",
        "--addLemmas",
        help="Additional lemma lexicon tok\tpos\tlemma",
        required=False,
    )
    args = parser.parse_args()

    app = MainApplication(args)
    app.run()
