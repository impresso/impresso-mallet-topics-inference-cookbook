# Topic-model processing config matching the currently used lingproc input run
# and topic output run.
#
# Usage:
#   make newspaper CFG=configs/config-topics-tm-mallet_infer_seed42_v2.0.1-multilingual_v2-0-1.mk
#   make all CFG=configs/config-topics-tm-mallet_infer_seed42_v2.0.1-multilingual_v2-0-1.mk

LOGGING_LEVEL ?= INFO
SHELL ?= /bin/bash

# Input lingproc run:
# s3://42-processed-data-final/lingproc/lingproc-pos-spacy_v3.6.0-multilingual_v1-0-3/<NEWSPAPER>/
S3_BUCKET_LINGPROC ?= 142-processed-data-final
PROCESS_LABEL_LINGPROC ?= lingproc
TASK_LINGPROC ?= pos
MODEL_ID_LINGPROC ?= spacy_v3.6.0-multilingual
RUN_VERSION_LINGPROC ?= v1-0-3

# Output topics run:
# s3://41-processed-data-staging/topics/topics-tm-mallet_infer_seed42_v2.0.1-multilingual_v2-0-1/<NEWSPAPER>/
S3_BUCKET_TOPICS ?= 140-processed-data-sandbox
PROCESS_LABEL_TOPICS ?= topics
TASK_TOPICS ?= tm
MALLET_RANDOM_SEED ?= 42
MODEL_VERSION_TOPICS ?= v2.0.1
LANG_TOPICS ?= multilingual
RUN_VERSION_TOPICS ?= v2-0-1

# Typical processing behavior for this run family.
PROCESSING_KEEP_TIMESTAMP_ONLY_OPTION ?= --keep-timestamp-only
PROCESSING_QUIT_IF_S3_OUTPUT_EXISTS_OPTION ?= --quit-if-s3-output-exists
