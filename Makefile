# Description: Makefile for multilingual topic inference for newspapers
# Read the README.md for more information on how to use this Makefile.
# Or run `make` for online help.

#### ENABLE LOGGING FIRST
# USER-VARIABLE: LOGGING_LEVEL
# Defines the logging level for the Makefile.

# Load our make logging functions
include cookbook/log.mk


# USER-VARIABLE: CONFIG_LOCAL_MAKE
# Defines the name of the local configuration file to include.
#
# This file is used to override default settings and provide local configuration. If a
# file with this name exists in the current directory, it will be included. If the file
# does not exist, it will be silently ignored. Never add the file called config.local.mk
# to the repository! If you have stored config files in the repository set the
# CONFIG_LOCAL_MAKE variable to a different name.
CONFIG_LOCAL_MAKE ?= config.local.mk
ifdef CFG
  CONFIG_LOCAL_MAKE := $(CFG)
  $(info Overriding CONFIG_LOCAL_MAKE to $(CONFIG_LOCAL_MAKE) from CFG variable)
else
  $(call log.info, CONFIG_LOCAL_MAKE)
endif

# Load local config if it exists (ignore silently if it does not exists)
-include $(CONFIG_LOCAL_MAKE)


# Now we can use the logging function to show the current logging level
  $(call log.info, LOGGING_LEVEL)


#: Show help message
# 
# Main help. More targets are shown when calling remake --tasks 
help::
	@echo ""
	@echo "USAGE for impresso mallet topic inference:  make [target]"
	@echo ""
	@echo " Targets:"
	@echo "  help            # Show this help message: remake --tasks emits help for all targets"
	@echo ""
	@echo " Example:"
	@echo "  make newspaper CFG=configs/config-topics-tm-mallet_infer_seed42_v2.0.1-multilingual_v2-0-1.mk"


# Default target when no target is specified on the command line
.DEFAULT_GOAL := help
PHONY_TARGETS += help


# SETTINGS FOR THE MAKE PROGRAM
include cookbook/make_settings.mk

# If you need to use a different shell than /bin/dash, overwrite it here.
# SHELL := /bin/bash


# SETTINGS FOR THE BUILD PROCESS

# Set the number of parallel launches of newspapers (uses xargs)
# Note: For efficient parallelization the number of cores should be PARALLEL_NEWSPAPERS * MAKE_PARALLEL_PROCESSING_NEWSPAPER_YEAR
#PARALLEL_NEWSPAPERS ?= 1
#  $(call log.debug, PARALLEL_NEWSPAPERS)

# Set the number of parallel jobs of newspaper-year files to process
#  $(call log.debug, MAKE_PARALLEL_PROCESSING_NEWSPAPER_YEAR)
#MAKE_PARALLEL_PROCESSING_NEWSPAPER_YEAR ?= 1 


# SETUP SETTINGS AND TARGETS
include cookbook/setup.mk
include cookbook/setup_python.mk
include cookbook/setup_topics.mk

# Load newspaper list configuration and processing rules
include cookbook/newspaper_list.mk

# SETUP PATHS
include cookbook/paths_rebuilt.mk
include cookbook/paths_langident.mk
include cookbook/paths_lingproc.mk
include cookbook/paths_topics.mk


# MAIN TARGETS
include cookbook/main_targets.mk


# SYNCHRONIZATION TARGETS
include cookbook/sync.mk
include cookbook/sync_rebuilt.mk
include cookbook/sync_langident.mk
include cookbook/sync_lingproc.mk
include cookbook/sync_topics.mk

include cookbook/clean.mk

# PROCESSING TARGETS
include cookbook/processing.mk
include cookbook/processing_topics.mk


# FUNCTION
include cookbook/local_to_s3.mk


# FURTHER ADDONS

.PHONY: $(PHONY_TARGETS)
