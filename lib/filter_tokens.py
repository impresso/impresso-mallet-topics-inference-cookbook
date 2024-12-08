import json
import argparse
import re
import logging

EXCLUDE_NPLIST = """
arbeitgeber
DTT
excelsior
EXP
FZG
GDL
handelsztg
IMP
jdpl
LCE
legaulois
LLE
schmiede
SDT
WHD
""".split(
    "\n"
)
EXCLUDE_NP = {np for np in EXCLUDE_NPLIST if np}


def filter_tokens(freq_json, input_tsv, output_tsv, min_freq=4, min_words=10):
    with open(freq_json, "r") as json_in:
        freq_dist = json.load(json_in)
    excluded = 0
    with open(input_tsv, "r") as tsv_in, open(output_tsv, "w") as tsv_out:
        for line in tsv_in:
            parts = line.strip().split("\t")
            np = parts[0].split("-", maxsplit=1)[0]
            if np in EXCLUDE_NP:
                excluded += 1
                continue
            tokens = parts[2].lower().split()
            filtered_tokens = [
                token
                for token in tokens
                if freq_dist.get(token, 0) >= min_freq and re.match(r"^[\w'-]+$", token)
            ]
            if len(filtered_tokens) >= min_words:
                parts[2] = " ".join(filtered_tokens)
                tsv_out.write("\t".join(parts) + "\n")
    logging.warning("Excluded %d lines", excluded)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Filter tokens based on frequency distribution."
    )
    parser.add_argument(
        "--freq-json", required=True, help="JSON file with frequency distribution."
    )
    parser.add_argument("--input-tsv", required=True, help="Input TSV file to filter.")
    parser.add_argument(
        "--output-tsv", required=True, help="Output TSV file with filtered tokens."
    )
    parser.add_argument(
        "--min-freq",
        type=int,
        default=4,
        help="Minimum frequency threshold for tokens.",
    )
    parser.add_argument(
        "--min-words",
        type=int,
        default=8,
        help="Minimum number of words required in a line after filtering.",
    )
    args = parser.parse_args()
    filter_tokens(
        args.freq_json, args.input_tsv, args.output_tsv, args.min_freq, args.min_words
    )
