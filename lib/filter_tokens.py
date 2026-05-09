import json
import argparse
import re
import logging
import sys
from typing import Optional, List

from smart_open import open as smart_open
from impresso_cookbook import setup_logging, get_transport_params

log = logging.getLogger(__name__)

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
    with smart_open(
        freq_json,
        "r",
        encoding="utf-8",
        transport_params=get_transport_params(freq_json),
    ) as json_in:
        freq_dist = json.load(json_in)
    excluded = 0
    with smart_open(
        input_tsv,
        "r",
        encoding="utf-8",
        transport_params=get_transport_params(input_tsv),
    ) as tsv_in, smart_open(
        output_tsv,
        "w",
        encoding="utf-8",
        transport_params=get_transport_params(output_tsv),
    ) as tsv_out:
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
    log.warning("Excluded %d lines", excluded)


def parse_arguments(args: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Filter tokens based on frequency distribution."
    )
    parser.add_argument(
        "--log-file", dest="log_file", help="Write log to FILE", metavar="FILE"
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level (default: %(default)s)",
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
    return parser.parse_args(args)


def main(args: Optional[List[str]] = None) -> None:
    options = parse_arguments(args)
    setup_logging(options.log_level, options.log_file, force=True)
    log.info("%s", options)
    filter_tokens(
        options.freq_json,
        options.input_tsv,
        options.output_tsv,
        options.min_freq,
        options.min_words,
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log.error("Processing error: %s", e, exc_info=True)
        sys.exit(2)
