"""Upload topic model description files to the topic run S3 prefix."""

import argparse
import bz2
import gzip
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, Iterable, Tuple


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


def topic_description_path(config_path: Path) -> Path:
    with config_path.open(encoding="utf-8") as handle:
        config = json.load(handle)
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


def recompress_bz2_to_gzip(source: Path, target: Path) -> None:
    with bz2.open(source, "rb") as input_file:
        with gzip.open(target, "wb") as output_file:
            shutil.copyfileobj(input_file, output_file)


def upload_file(local_path: Path, s3_uri: str) -> None:
    subprocess.run(
        ["aws", "s3", "cp", str(local_path), s3_uri],
        check=True,
    )


def main() -> int:
    args = parse_args()
    s3_prefix = args.s3_prefix.rstrip("/")
    language_configs = iter_language_configs(args.language_config)

    with tempfile.TemporaryDirectory(prefix="topic-descriptions-") as tmp_dir_name:
        tmp_dir = Path(tmp_dir_name)
        for language, config_path in sorted(language_configs.items()):
            source = topic_description_path(config_path)
            destination_name = args.name_template.format(lang=language)
            destination = f"{s3_prefix}/{destination_name}"
            tmp_output = tmp_dir / destination_name
            print(f"{source} -> {destination}", file=sys.stderr)
            if args.dry_run:
                continue
            recompress_bz2_to_gzip(source, tmp_output)
            upload_file(tmp_output, destination)
    return 0


if __name__ == "__main__":
    sys.exit(main())
