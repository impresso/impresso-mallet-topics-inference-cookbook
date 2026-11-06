#!/usr/bin/env bash
set -euo pipefail

# Script to run topic inference on sample data without requiring S3 credentials or configuration.
# Usage: ./samples/run_sample.sh [output_path]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

OUTPUT_FILE="${1:-${SCRIPT_DIR}/sample_output_topics.jsonl}"
INPUT_FILE="${SCRIPT_DIR}/sample_lingproc.jsonl"

PYTHON="${REPO_ROOT}/.venv/bin/python"
if [ ! -x "${PYTHON}" ]; then
    PYTHON="python3"
fi

echo "=== Impresso Topic Inference Sample Run ==="
echo "Input:   ${INPUT_FILE}"
echo "Output:  ${OUTPUT_FILE}"
echo "Python:  $(${PYTHON} --version)"
echo "Working directory: ${REPO_ROOT}"
echo "==========================================="

cd "${REPO_ROOT}"

"${PYTHON}" -m lib.mallet_topic_inferencer \
  --input "${INPUT_FILE}" \
  --input-format impresso \
  --output "${OUTPUT_FILE}" \
  --languages fr de \
  --fr_config models/tm/tm-fr-all-v3.0.config.json \
  --de_config models/tm/tm-de-all-v3.0.config.json \
  --impresso-model-id topics-v3.0.0-sample

echo ""
echo "=== Sample Processing Complete ==="
echo "Inference succeeded! Output preview:"
head -n 5 "${OUTPUT_FILE}"
