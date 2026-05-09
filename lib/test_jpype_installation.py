import argparse
import json
import os
import sys
from pathlib import Path
from typing import List, Optional

import jpype
import jpype.imports

try:
    import dotenv
except ModuleNotFoundError:
    dotenv = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check that JPype can import MALLET classes."
    )
    parser.add_argument(
        "--config",
        action="append",
        default=[],
        help="Topic model config JSON file used to select the required MALLET runtime.",
    )
    return parser.parse_args()


def required_mallet_runtime(config_paths: List[str]) -> Optional[str]:
    runtimes = set()
    for config_path in config_paths:
        with open(config_path, encoding="utf-8") as handle:
            config = json.load(handle)
        mallet = config.get("mallet", {})
        if isinstance(mallet, dict) and mallet.get("runtime"):
            runtimes.add(str(mallet["runtime"]))
    if len(runtimes) > 1:
        raise ValueError(f"Conflicting MALLET runtimes in configs: {sorted(runtimes)}")
    return next(iter(runtimes), None)


def find_mallet_home(runtime: Optional[str], current_dir: Path, repo_dir: Path) -> Optional[Path]:
    candidates = []
    if os.environ.get("MALLET_HOME"):
        candidates.append(Path(os.environ["MALLET_HOME"]))
    if runtime:
        candidates.extend(
            [
                current_dir / runtime,
                repo_dir / runtime,
                current_dir.parent / runtime,
                repo_dir.parent / runtime,
            ]
        )
    for candidate in candidates:
        if (candidate / "lib").is_dir():
            return candidate
    return None


def resolve_mallet_classpath(config_paths: List[str]) -> List[str]:
    current_dir = Path.cwd()
    repo_dir = Path(__file__).resolve().parent.parent
    runtime = required_mallet_runtime(config_paths)

    mallet_home = find_mallet_home(runtime, current_dir, repo_dir)
    if mallet_home:
        classpath = sorted(str(path) for path in (mallet_home / "lib").glob("*.jar"))
        if classpath:
            return classpath

    if runtime and runtime != "mallet":
        raise FileNotFoundError(
            f"Model config requires MALLET runtime {runtime}, but no matching runtime "
            "was found. Set TOPICS_MALLET_HOME or MALLET_HOME to the MALLET runtime "
            "directory, or vendor it in the inference repository."
        )

    fallback_classpath = [
        current_dir / "mallet/lib/mallet-deps.jar",
        current_dir / "mallet/lib/mallet.jar",
    ]
    if not all(path.exists() for path in fallback_classpath):
        fallback_classpath = [
            repo_dir / "mallet/lib/mallet-deps.jar",
            repo_dir / "mallet/lib/mallet.jar",
        ]
    if not all(path.exists() for path in fallback_classpath):
        raise FileNotFoundError(
            "Could not locate MALLET jars. Set TOPICS_MALLET_HOME or MALLET_HOME, "
            "or run from the inference repository root."
        )
    return [str(path) for path in fallback_classpath]


def main() -> int:
    if dotenv is not None:
        dotenv.load_dotenv()
    args = parse_args()
    classpath = resolve_mallet_classpath(args.config)
    print(classpath, file=sys.stderr)
    jpype.startJVM("--enable-native-access=ALL-UNNAMED", classpath=classpath)
    from cc.mallet.classify.tui import Csv2Vectors  # noqa: F401

    return 0


if __name__ == "__main__":
    sys.exit(main())
