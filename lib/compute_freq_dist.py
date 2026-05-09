import os
import json
import argparse
import logging
import sys
from collections import defaultdict
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


def compute_frequency_distribution(input_dir, output_json, output_tsv):
    freq_dist = defaultdict(int)
    excluded = 0
    with smart_open(
        output_tsv,
        "w",
        encoding="utf-8",
        transport_params=get_transport_params(output_tsv),
    ) as tsv_out:
        for filename in os.listdir(input_dir):
            if filename.endswith(".tsv"):
                input_path = os.path.join(input_dir, filename)
                with smart_open(
                    input_path,
                    "r",
                    encoding="utf-8",
                    transport_params=get_transport_params(input_path),
                ) as tsv_in:
                    for line in tsv_in:
                        stripped_line = line.strip()
                        if not stripped_line:
                            continue
                        data = stripped_line.split("\t")
                        np = data[0].split("-", maxsplit=1)[0]
                        if np in EXCLUDE_NP:
                            excluded += 1
                            continue
                        if len(data) < 3:
                            continue
                        tsv_out.write(line)
                        try:
                            tokens = stripped_line.split("\t")[2].lower().split()
                        except IndexError:
                            raise ValueError(f"Error processing line: {line}") from None
                        for token in tokens:
                            if len(token) > 2:
                                freq_dist[token] += 1
    log.info("Excluded %d lines", excluded)
    with smart_open(
        output_json,
        "w",
        encoding="utf-8",
        transport_params=get_transport_params(output_json),
    ) as json_out:
        json.dump(freq_dist, json_out, indent=2, ensure_ascii=False)


def parse_arguments(args: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compute frequency distribution and merge TSV files."
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
        "--input-dir", required=True, help="Directory containing TSV files."
    )
    parser.add_argument(
        "--output-json",
        required=True,
        help="Output JSON file for frequency distribution.",
    )
    parser.add_argument("--output-tsv", required=True, help="Output merged TSV file.")
    return parser.parse_args(args)


def main(args: Optional[List[str]] = None) -> None:
    options = parse_arguments(args)
    setup_logging(options.log_level, options.log_file, force=True)
    log.info("%s", options)
    compute_frequency_distribution(
        options.input_dir, options.output_json, options.output_tsv
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log.error("Processing error: %s", e, exc_info=True)
        sys.exit(2)
