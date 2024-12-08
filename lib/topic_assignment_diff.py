#!/usr/bin/env python3

import argparse
import json
import logging
from typing import List, Optional, Dict, Any, Tuple
from collections import Counter
from smart_open import (
    open,
)  # assuming `smart_open` is installed for handling various file types

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def read_json(file_path: str) -> Dict[str, Any]:
    """Reads a JSON file and returns its content as a dictionary.

    Args:
        file_path (str): The path to the JSON file.

    Returns:
        dict: The JSON content as a dictionary.
    """
    with open(file_path, "r") as f:
        return json.load(f)


def read_jsonl(file_path: str, ci_ids: Optional[set] = None) -> List[Dict[str, Any]]:
    """Reads a JSONL file and filters entries by given ci_ids if provided.

    Args:
        file_path (str): The path to the JSONL file.
        ci_ids (Optional[set]): A set of IDs to filter entries.

    Returns:
        list: A list of dictionaries representing the JSONL entries.
    """
    entries = []
    with open(file_path, "r") as f:
        for line in f:
            entry = json.loads(line)
            if ci_ids:
                if entry.get("ci_id", entry.get("id", entry.get("ci_ref"))) in ci_ids:
                    entries.append(entry)
            else:
                entries.append(entry)
    return entries


def compare_topics(
    json1: List[Dict[str, Any]], json2: List[Dict[str, Any]], threshold: float = 0.005
) -> List[Tuple[str, float, float]]:
    """Compares topics between two JSON objects and identifies differences.

    Args:
        json1 (list): First list of topics as dictionaries.
        json2 (list): Second list of topics as dictionaries.
        threshold (float): Threshold for identifying significant differences.

    Returns:
        list: List of tuples with topic IDs and their probabilities in both JSONs.
    """
    differences = []
    topics1 = {topic["t"]: topic["p"] for topic in json1}
    topics2 = {topic["t"]: topic["p"] for topic in json2}

    all_topic_ids = set(topics1.keys()).union(set(topics2.keys()))

    for topic_id in all_topic_ids:
        p1 = topics1.get(topic_id, 0)
        p2 = topics2.get(topic_id, 0)
        if abs(p1 - p2) > threshold:
            differences.append((topic_id, p1, p2))
    return differences


def compare_topic_assignments(
    json_file1: str, json_file2: str, threshold: float = 0.05
) -> None:
    """Compares topic assignments between two JSON files.

    Args:
        json_file1 (str): Path to the first JSON file.
        json_file2 (str): Path to the second JSON file.
        threshold (float): Threshold for identifying significant differences.
    """
    topics1 = read_json(json_file1)["topics"]
    topics2 = read_json(json_file2)["topics"]

    differences = compare_topics(topics1, topics2, threshold)

    if differences:
        logger.debug("The topic assignments are substantially different.")
        for diff in differences:
            logger.debug(f"Topic ID: {diff[0]}, File1: {diff[1]}, File2: {diff[2]}")
    else:
        logger.debug("The topic assignments are not substantially different.")


def compare_jsonl_files(
    jsonl_file1: str,
    jsonl_file2: str,
    threshold: float = 0.05,
    mallet_csv1: Optional[str] = None,
    mallet_csv2: Optional[str] = None,
) -> None:
    """Compares two JSONL files and optionally Mallet CSV files based on topic and word assignments.

    Args:
        jsonl_file1 (str): Path to the first JSONL file.
        jsonl_file2 (str): Path to the second JSONL file.
        threshold (float): Threshold for identifying significant differences.
        mallet_csv1 (Optional[str]): Path to the first Mallet CSV file.
        mallet_csv2 (Optional[str]): Path to the second Mallet CSV file.
    """
    data1 = read_jsonl(jsonl_file1)
    ci_ids1 = {
        entry.get("ci_id", entry.get("id", entry.get("ci_ref"))) for entry in data1
    }
    logger.debug(f"IDs in first file: {ci_ids1}")
    data2 = read_jsonl(jsonl_file2, ci_ids=ci_ids1)
    logger.debug(f"Entries in second file: {len(data2)}")

    data2_dict = {entry.get("ci_id", entry.get("id")): entry for entry in data2}

    # Read words from Mallet CSV files if provided
    words_data1 = {}
    words_data2 = {}
    if mallet_csv1 and mallet_csv2:
        words_data1 = read_mallet_csv(mallet_csv1)
        words_data2 = read_mallet_csv(mallet_csv2)

    if not data2_dict:
        logger.warning("No data found in the second file.")
        return

    for entry1 in data1:
        ci_id1 = entry1.get("ci_id", entry1.get("id"))
        entry2 = data2_dict.get(ci_id1)
        if not entry2:
            logger.warning(f"ID {ci_id1} not found in second file.")
            continue

        # Compare topics
        differences = compare_topics(entry1["topics"], entry2["topics"], threshold)
        if differences:
            print(ci_id1, "TOPICS", end="\t")
            for diff in differences:
                print(diff[0], diff[1], diff[2], end="\t")
            print()
        else:
            print(ci_id1, "TOPICS", "-", sep="\t")

        # Compare words if Mallet CSV files are provided
        if mallet_csv1 and mallet_csv2:
            words1 = words_data1.get(ci_id1, Counter())
            words2 = words_data2.get(ci_id1, Counter())

            additional_words = words2 - words1
            missing_words = words1 - words2

            if additional_words or missing_words:
                print(ci_id1, "WORDS", end="\t")
                for word, count in additional_words.items():
                    print(f"+{word}({count})", end=" ")
                for word, count in missing_words.items():
                    print(f"-{word}({count})", end=" ")
                print()
            else:
                print(ci_id1, "WORDS", "-", sep="\t")
        else:
            # If words are included in JSONL files
            words1 = Counter(entry1.get("words", []))
            words2 = Counter(entry2.get("words", []))

            additional_words = words2 - words1
            missing_words = words1 - words2

            if additional_words or missing_words:
                print(ci_id1, "WORDS", end="\t")
                for word, count in additional_words.items():
                    print(f"+{word}({count})", end=" ")
                for word, count in missing_words.items():
                    print(f"-{word}({count})", end=" ")
                print()
            else:
                print(ci_id1, "WORDS", "-", sep="\t")


def read_mallet_csv(file_path: str) -> Dict[str, Counter]:
    """Reads a Mallet CSV file and returns its content as a dictionary.

    Args:
        file_path (str): The path to the Mallet CSV file.

    Returns:
        dict: A dictionary with DOCID as keys and Counter of words as values.
    """
    data = {}
    with open(file_path, "r") as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) >= 3:
                doc_id = parts[0]
                words = parts[2].split()
                data[doc_id] = Counter(words)
    return data


def compare_mallet_csv(file1: str, file2: str) -> None:
    """Compares two Mallet CSV files and prints the differences in words.

    Args:
        file1 (str): Path to the first Mallet CSV file.
        file2 (str): Path to the second Mallet CSV file.
    """
    data1 = read_mallet_csv(file1)
    data2 = read_mallet_csv(file2)

    all_doc_ids = set(data1.keys()).union(set(data2.keys()))

    for doc_id in all_doc_ids:
        words1 = data1.get(doc_id, Counter())
        words2 = data2.get(doc_id, Counter())

        additional_words = words2 - words1
        missing_words = words1 - words2

        if additional_words or missing_words:
            print(f"{doc_id}\tWORDS", end="\t")
            for word, count in additional_words.items():
                print(f"+{word}({count})", end=" ")
            for word, count in missing_words.items():
                print(f"-{word}({count})", end=" ")
            print()
        else:
            print(f"{doc_id}\tWORDS\t-")


def main() -> None:
    """Main function to handle command-line arguments and execute comparison."""
    parser = argparse.ArgumentParser(
        description=(
            "Compare JSONL files and Mallet CSV files based on topic assignments and"
            " word differences."
        )
    )
    parser.add_argument("jsonl_file1", type=str, help="Path to the first JSONL file.")
    parser.add_argument("jsonl_file2", type=str, help="Path to the second JSONL file.")
    parser.add_argument(
        "--threshold", type=float, default=0.05, help="Threshold for topic comparison."
    )
    parser.add_argument(
        "--mallet_csv1", type=str, help="Path to the first Mallet CSV file."
    )
    parser.add_argument(
        "--mallet_csv2", type=str, help="Path to the second Mallet CSV file."
    )

    args = parser.parse_args()

    compare_jsonl_files(
        args.jsonl_file1,
        args.jsonl_file2,
        args.threshold,
        args.mallet_csv1,
        args.mallet_csv2,
    )


if __name__ == "__main__":
    main()
