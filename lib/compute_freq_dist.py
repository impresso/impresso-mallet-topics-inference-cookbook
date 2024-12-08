import os
import json
import argparse
from collections import defaultdict

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
    with open(output_tsv, "w") as tsv_out:
        for filename in os.listdir(input_dir):
            if filename.endswith(".tsv"):
                with open(os.path.join(input_dir, filename), "r") as tsv_in:
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
                            print(f"Error processing line: {line}")
                            exit(1)
                        for token in tokens:
                            if len(token) > 2:
                                freq_dist[token] += 1
    with open(output_json, "w") as json_out:
        json.dump(freq_dist, json_out, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Compute frequency distribution and merge TSV files."
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
    args = parser.parse_args()
    compute_frequency_distribution(args.input_dir, args.output_json, args.output_tsv)
