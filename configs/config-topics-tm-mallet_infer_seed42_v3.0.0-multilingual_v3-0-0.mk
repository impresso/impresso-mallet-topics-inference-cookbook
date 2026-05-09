# Topic-model processing config for the v3 MALLET inference bundle.
#
# Usage:
#   make newspaper CFG=configs/config-topics-tm-mallet_infer_seed42_v3.0.0-multilingual_v3-0-0.mk
#   make all CFG=configs/config-topics-tm-mallet_infer_seed42_v3.0.0-multilingual_v3-0-0.mk

LOGGING_LEVEL ?= INFO
SHELL ?= /bin/bash

# Input lingproc run. v3 topic models expect input produced by the same
# linguistic-processing family used during training.
S3_BUCKET_LINGPROC ?= 142-processed-data-final
PROCESS_LABEL_LINGPROC ?= lingproc
TASK_LINGPROC ?= pos
MODEL_ID_LINGPROC ?= spacy_v3.6.0-multilingual
RUN_VERSION_LINGPROC ?= v1-0-3

# Output topics run:
# s3://41-processed-data-staging/topics/topics-tm-mallet_infer_seed42_v3.0.0-multilingual_v3-0-0/<NEWSPAPER>/
S3_BUCKET_TOPICS ?= 141-processed-data-staging
PROCESS_LABEL_TOPICS ?= topics
TASK_TOPICS ?= tm
MALLET_RANDOM_SEED ?= 42
MODEL_VERSION_TOPICS ?= v3.0.0
LANG_TOPICS ?= multilingual
RUN_VERSION_TOPICS ?= v3-0-0

TOPICS_LANGUAGES ?= de fr en lb
TOPICS_DE_CONFIG ?= models/tm/tm-de-all-v3.0.config.json
TOPICS_FR_CONFIG ?= models/tm/tm-fr-all-v3.0.config.json
TOPICS_EN_CONFIG ?= models/tm/tm-en-all-v3.0.config.json
TOPICS_LB_CONFIG ?= models/tm/tm-lb-all-v3.0.config.json

# Set this to a local MALLET 2.1.0 directory if it is not vendored in this repo.
TOPICS_MALLET_HOME ?=

# Typical topics-side S3 behavior for this run family.
TOPICS_KEEP_TIMESTAMP_ONLY_OPTION ?= --keep-timestamp-only
TOPICS_SKIP_IF_OUTPUT_EXISTS_OPTION ?= --quit-if-s3-output-exists
# TOPICS_DRY_RUN_OPTION ?= --s3-output-dry-run
# TOPICS_FORCE_OVERWRITE_OPTION ?= --force-overwrite
