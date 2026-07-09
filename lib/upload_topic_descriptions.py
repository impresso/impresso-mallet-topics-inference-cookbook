"""Upload topic model description files to the topic run S3 prefix."""

import argparse
import bz2
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple

from smart_open import open as smart_open
from impresso_cookbook import get_transport_params

try:
    import dotenv
except ModuleNotFoundError:
    dotenv = None


def parse_language_config(value: str) -> Tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError(
            f"Expected LANG=CONFIG_PATH, got {value!r}"
        )
    language, config_path = value.split("=", 1)
    language = language.strip()
    config_path = config_path.strip()
    if not language or not config_path:
        raise argparse.ArgumentTypeError(
            f"Expected LANG=CONFIG_PATH, got {value!r}"
        )
    return language, Path(config_path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Recompress topic model descriptions from jsonl.bz2 to jsonl.gz "
            "and upload them to an S3 prefix."
        )
    )
    parser.add_argument(
        "--s3-prefix",
        required=True,
        help="Destination S3 prefix, for example s3://bucket/topics/run-id",
    )
    parser.add_argument(
        "--language-config",
        action="append",
        default=[],
        type=parse_language_config,
        metavar="LANG=CONFIG",
        help="Language code and topic model config JSON path.",
    )
    parser.add_argument(
        "--name-template",
        default="{lang}.topic_model_topic_description.jsonl.gz",
        help="Destination basename template. Supports {lang}.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned uploads without writing to S3.",
    )
    return parser.parse_args()


def read_model_config(config_path: Path) -> Dict[str, Any]:
    with config_path.open(encoding="utf-8") as handle:
        return json.load(handle)


def topic_description_path(config_path: Path, config: Dict[str, Any]) -> Path:
    artifacts = config.get("artifacts", {})
    topic_description = artifacts.get("topic_description")
    if not topic_description:
        raise ValueError(f"{config_path} has no artifacts.topic_description entry")
    path = Path(topic_description)
    if not path.is_absolute():
        path = config_path.parent / path
    if not path.is_file():
        raise FileNotFoundError(f"Topic description file not found: {path}")
    return path


def iter_language_configs(items: Iterable[Tuple[str, Path]]) -> Dict[str, Path]:
    language_configs: Dict[str, Path] = {}
    for language, config_path in items:
        if language in language_configs:
            raise ValueError(f"Duplicate language config for {language}")
        if not config_path.is_file():
            raise FileNotFoundError(f"Topic model config not found: {config_path}")
        language_configs[language] = config_path
    if not language_configs:
        raise ValueError("At least one --language-config is required")
    return language_configs


def canonical_topic_id(model_id: str, topic_number: int, language: str, topic_count: int) -> str:
    padding = max(2, len(str(max(topic_count - 1, 0))))
    return f"{model_id}_tp{topic_number:0{padding}d}_{language}"


def write_canonical_topic_descriptions(
    source: Path,
    target_uri: str,
    model_id: str,
    language: str,
    topic_count: int,
) -> None:
    with bz2.open(source, "rt", encoding="utf-8") as input_file:
        with smart_open(
            target_uri,
            "w",
            encoding="utf-8",
            transport_params=get_transport_params(target_uri),
        ) as output_file:
            for line in input_file:
                if not line.strip():
                    continue
                record = json.loads(line)
                topic_number = int(record["topic"])
                record["topic_model"] = model_id
                record["id"] = canonical_topic_id(
                    model_id,
                    topic_number,
                    language,
                    topic_count,
                )
                output_file.write(json.dumps(record, ensure_ascii=False) + "\n")


def main() -> int:
    if dotenv is not None:
        dotenv.load_dotenv()
    args = parse_args()
    s3_prefix = args.s3_prefix.rstrip("/")
    language_configs = iter_language_configs(args.language_config)

    for language, config_path in sorted(language_configs.items()):
        config = read_model_config(config_path)
        model_id = config["model_id"]
        topic_count = int(config["topic_count"])
        source = topic_description_path(config_path, config)
        destination_name = args.name_template.format(lang=language)
        destination = f"{s3_prefix}/{destination_name}"
        print(f"{source} -> {destination}", file=sys.stderr)
        if args.dry_run:
            continue
        write_canonical_topic_descriptions(
            source,
            destination,
            model_id,
            language,
            topic_count,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
