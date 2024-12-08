# Description: Makefile for multilingual topic inference for newspapers
# Read the README.md for more information on how to use this Makefile.
# Or run `make` for online help.

###
# SETTINGS FOR THE MAKE PROGRAM
# Enable warning for undefined variables
export MAKEFLAGS += --warn-undefined-variables

# Define the shell to use for executing commands
SHELL:=/bin/bash

# Enable strict error handling
export SHELLOPTS:=errexit:pipefail

# Keep intermediate files generated for the build process
.SECONDARY:

# Delete intermediate files if the target fails
.DELETE_ON_ERROR:

# suppress all default rules
.SUFFIXES:

###
# SETTINGS FOR THE BUILD PROCESS

# Load local config if it exists (ignore silently if it does not exists)
-include config.local.mk




# Load our make logging functions
include cookbook/log.mk

# Set the logging level: DEBUG, INFO, WARNING, ERROR
LOGGING_LEVEL ?= INFO

  $(call log.info, LOGGING_LEVEL)

# keep make output concise for longish recipes
ifeq "$(filter DEBUG,$(LOGGING_LEVEL))" "DEBUG"
  $(call log.debug, LOGGING_LEVEL)
MAKE_SILENCE_RECIPE ?=
else
MAKE_SILENCE_RECIPE ?= @
endif

# Set the number of parallel embedding jobs to run
MAKE_PARALLEL_OPTION ?= "--jobs 2"
  $(call log.debug, MAKE_PARALLEL_OPTION)


ifndef GIT_VERSION
GIT_VERSION := $(shell git describe --tags --always)
endif
  $(call log.info, GIT_VERSION)
export GIT_VERSION

###
# SETTING DEFAULT VARIABLES FOR THE PROCESSING

# The build directory where all local input and output files are stored
# The content of BUILD_DIR be removed anytime without issues regarding s3
BUILD_DIR ?= build.d
  $(call log.debug, BUILD_DIR)

### Determine the newspaper titles to process
# sets NEWSPAPER if not defined
# 
S3_PREFIX_NEWSPAPER_TO_PROCESS_BUCKET ?= 22-rebuilt-final
  $(call log.debug, S3_PREFIX_NEWSPAPER_TO_PROCESS_BUCKET)
include cookbook/newspaper_to_process.mk

###
# DEFINING THE REQUIRED DATA INPUT PATHS
# all paths are defined as s3 paths and local paths
# local paths are relative to $BUILD_DIR
# s3 paths are relative to the bucket
# The paths are defined as variables to make it easier to change them in the future.
# Input paths start with IN_ and output paths with OUT_
# Make variables for s3 paths are defined as OUT_S3_ or IN_S3_
# If more than one input is needed, the variable names are IN_1_S3_ or OUT_2_S3_
# Make variables for local paths are defined as OUT_LOCAL_ or IN_LOCAL_

# The input bucket
include cookbook/input_paths_lingproc.mk

###
# DEFINING THE OUTPUT PATHS

include cookbook/output_paths_topics.mk


###
# TARGETS FOR THE BUILD PROCESS

include cookbook/setup_topics.mk



# Process a single newspaper
newspaper:
	$(MAKE) sync
	$(MAKE) processing-topics-target


PHONY_TARGETS += newspaper

# Make newspaper from a clean fresh resync
# resync should not be parallel
# actual processing should be parallel
all: 
	$(MAKE) resync 
	$(MAKE) $(MAKE_PARALLEL_OPTION) processing-topics-target

PHONY_TARGETS += all

# Process the text embeddings for each newspaper found in the file $(NEWSPAPERS_TO_PROCESS_FILE)
collection:
	for np in $(file < $(NEWSPAPERS_TO_PROCESS_FILE)) ; do \
		$(MAKE) NEWSPAPER="$$np" all  ; \
	done

PHONY_TARGETS += collection

include cookbook/processing_topics.mk

# SYNCING THE INPUT AND OUTPUT DATA FROM S3 TO LOCAL DIRECTORY

include cookbook/sync_topics.mk


%.d:
	mkdir -p $@

# help: Show this help message
help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  setup     # Create the local directories and store the HF model locally"
	@echo "  newspaper # Sync the data from the S3 bucket to the local directory and process the text embeddings for a single newspaper"
	@echo "  sync      # Sync the data from the S3 bucket to the local directory"
	@echo "  newspaper-list-target  # Create the file containing the newspapers to process: $(NEWSPAPERS_TO_PROCESS_FILE)"
	@echo "  resync    # Remove the local synchronization file stamp and redoes everything, ensuring a full sync with the remote server."
	@echo "  clean-sync # Remove the local synchronization file stamp and redoes everything, ensuring a full sync with the remote server."
	@echo "  each      # Process the text embeddings for each newspaper found in the file $(NEWSPAPERS_TO_PROCESS_FILE)"
	@echo "  help      # Show this help message"
	@echo "# cp config.local.sample.mk config.local.mk and adapt the settings to your needs"

# Default target when no target is specified on the command line
.DEFAULT_GOAL := help
PHONY_TARGETS += help




PHONY_TARGETS += update-requirements


include cookbook/local_to_s3.mk


.PHONY: $(PHONY_TARGETS)
