"""Aggregate topic assignments into yearly fingerprints and dominant-topic indexes."""

import argparse
import collections
import json
import logging
import re
import sys
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from smart_open import open as smart_open

from impresso_cookbook import get_s3_client, get_transport_params, parse_s3_path
from impresso_cookbook.common import yield_s3_objects

try:
    import dotenv
except ModuleNotFoundError:
    dotenv = None

log = logging.getLogger(__name__)

YEAR_RE = re.compile(r"-(\d{4})-\d{2}-\d{2}-")


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Aggregate topic-assignment JSONL files into YTDF and DTCI products."
        )
    )
    parser.add_argument(
        "--s3-prefix",
        required=True,
        help="Input topic-assignment S3 prefix, for example s3://bucket/topics/run-id",
    )
    parser.add_argument(
        "--output-prefix",
        help=(
            "Output prefix. Defaults to the input prefix with __AGGREGATED appended, "
            "matching other cookbook aggregation targets."
        ),
    )
    parser.add_argument(
        "--languages",
        nargs="+",
        default=["de", "fr", "en", "lb"],
        help="Languages to aggregate.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level.",
    )
    return parser.parse_args(argv)


def extract_year(ci_id: str) -> str:
    match = YEAR_RE.search(ci_id)
    if not match:
        raise ValueError(f"Could not extract year from content item id: {ci_id}")
    return match.group(1)


def single_or_sorted(values: Set[Any]) -> Any:
    if len(values) == 1:
        return next(iter(values))
    return sorted(values)


def iter_topic_assignments(s3_prefix: str) -> Iterable[Dict[str, Any]]:
    bucket, prefix = parse_s3_path(s3_prefix.rstrip("/") + "/")
    client = get_s3_client()
    transport_params = {"client": client}
    for key in yield_s3_objects(bucket, prefix):
        if not key.endswith(".jsonl.bz2"):
            continue
        uri = f"s3://{bucket}/{key}"
        log.info("Reading %s", uri)
        with smart_open(
            uri,
            "r",
            encoding="utf-8",
            transport_params=transport_params,
        ) as input_file:
            for line in input_file:
                if line.strip():
                    yield json.loads(line)


def write_jsonl(path: str, records: Iterable[Dict[str, Any]]) -> int:
    count = 0
    with smart_open(
        path,
        "w",
        encoding="utf-8",
        transport_params=get_transport_params(path),
    ) as output_file:
        for record in records:
            output_file.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1
    log.info("Wrote %d records to %s", count, path)
    return count


class TopicAggregates:
    def __init__(self, languages: Sequence[str]) -> None:
        self.languages = set(languages)
        self.year_topic_mass: Dict[Tuple[str, str], collections.Counter] = (
            collections.defaultdict(collections.Counter)
        )
        self.year_topic_ci_count: Dict[Tuple[str, str], collections.Counter] = (
            collections.defaultdict(collections.Counter)
        )
        self.year_total_mass: collections.Counter = collections.Counter()
        self.year_ci_count: collections.Counter = collections.Counter()
        self.dtci: Dict[Tuple[str, str], List[Dict[str, Any]]] = collections.defaultdict(list)
        self.min_p_by_language: Dict[str, Set[float]] = collections.defaultdict(set)
        self.topic_models_by_language: Dict[str, Set[str]] = collections.defaultdict(set)
        self.documents_by_language: collections.Counter = collections.Counter()
        self.skipped_no_topics: collections.Counter = collections.Counter()

    def add(self, item: Dict[str, Any]) -> None:
        language = item.get("lg")
        if language not in self.languages:
            return
        topics = item.get("topics") or []
        if not topics:
            self.skipped_no_topics[language] += 1
            return

        ci_id = item["ci_id"]
        year = extract_year(ci_id)
        min_p = item.get("min_p")
        if min_p is not None:
            self.min_p_by_language[language].add(float(min_p))
        topic_model_id = item.get("topic_model_id")
        if topic_model_id:
            self.topic_models_by_language[language].add(topic_model_id)

        year_key = (language, year)
        self.documents_by_language[language] += 1
        self.year_ci_count[year_key] += 1

        top_topic = None
        top_probability = -1.0
        for topic in topics:
            topic_id = topic["t"]
            probability = float(topic["p"])
            self.year_topic_mass[year_key][topic_id] += probability
            self.year_topic_ci_count[year_key][topic_id] += 1
            self.year_total_mass[year_key] += probability
            if probability > top_probability:
                top_topic = topic_id
                top_probability = probability

        if top_topic is not None:
            self.dtci[(language, top_topic)].append(
                {"ci_id": ci_id, "year": year, "p": round(top_probability, 6)}
            )

    def ytdf_records(self, language: str) -> Iterable[Dict[str, Any]]:
        years = sorted(year for lg, year in self.year_topic_mass if lg == language)
        min_p = single_or_sorted(self.min_p_by_language[language])
        topic_model_id = single_or_sorted(self.topic_models_by_language[language])
        for year in years:
            year_key = (language, year)
            total_mass = float(self.year_total_mass[year_key])
            topics = []
            for topic_id, mass in self.year_topic_mass[year_key].most_common():
                topics.append(
                    {
                        "t": topic_id,
                        "p": round(float(mass) / total_mass, 8) if total_mass else 0.0,
                        "mass": round(float(mass), 8),
                        "content_item_count": self.year_topic_ci_count[year_key][topic_id],
                    }
                )
            yield {
                "aggregation": "ytdf",
                "aggregation_name": "yearly topic distribution fingerprint",
                "lg": language,
                "year": year,
                "topic_model_id": topic_model_id,
                "min_p": min_p,
                "normalization": "retained_topic_mass",
                "content_item_count": self.year_ci_count[year_key],
                "retained_topic_mass": round(total_mass, 8),
                "topics": topics,
            }

    def dtci_records(self, language: str) -> Iterable[Dict[str, Any]]:
        min_p = single_or_sorted(self.min_p_by_language[language])
        topic_model_id = single_or_sorted(self.topic_models_by_language[language])
        topics = sorted(topic for lg, topic in self.dtci if lg == language)
        for topic_id in topics:
            items = sorted(self.dtci[(language, topic_id)], key=lambda item: item["ci_id"])
            yield {
                "aggregation": "dtci",
                "aggregation_name": "dominant topic content index",
                "lg": language,
                "topic": topic_id,
                "topic_model_id": topic_model_id,
                "min_p": min_p,
                "content_item_count": len(items),
                "content_items": items,
            }


def main(argv: Optional[Sequence[str]] = None) -> int:
    if dotenv is not None:
        dotenv.load_dotenv()
    args = parse_args(argv)
    logging.basicConfig(
        level=args.log_level,
        format="%(asctime)-15s %(filename)s:%(lineno)d %(levelname)s: %(message)s",
        force=True,
    )

    output_prefix = args.output_prefix or f"{args.s3_prefix.rstrip('/')}__AGGREGATED"
    aggregates = TopicAggregates(args.languages)
    for item in iter_topic_assignments(args.s3_prefix):
        aggregates.add(item)

    for language in args.languages:
        write_jsonl(
            f"{output_prefix}_{language}.ytdf.jsonl.gz",
            aggregates.ytdf_records(language),
        )
        write_jsonl(
            f"{output_prefix}_{language}.dtci.jsonl.gz",
            aggregates.dtci_records(language),
        )
        log.info(
            "STATS: %s documents=%d skipped_no_topics=%d",
            language,
            aggregates.documents_by_language[language],
            aggregates.skipped_no_topics[language],
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
