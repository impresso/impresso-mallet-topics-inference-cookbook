# Description: Makefile for multilingual topic inference for newspapers
# Read the README.md for more information on how to use this Makefile.
# Or run `make` for online help.

#### ENABLE LOGGING FIRST
# USER-VARIABLE: LOGGING_LEVEL
# Defines the logging level for the Makefile.

# Load our make logging functions
include cookbook/log.mk

# Load the help system (must come early so help:: can be extended by later includes)
include cookbook/help.mk


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
# Main help.
help::
	@echo ""
	@echo "USAGE for impresso mallet topic inference:  make [target]"
	@echo ""
	@echo " Targets:"
	@echo "  help            # Show this help message"
	@echo ""
	@echo " Example:"
	@echo "  make newspaper CFG=configs/config-topics-tm-mallet_infer_seed42_v3.0.0-multilingual_v3-0-0.mk"


# Default target when no target is specified on the command line
.DEFAULT_GOAL := help
PHONY_TARGETS += help


# SETTINGS FOR THE MAKE PROGRAM
include cookbook/make_settings.mk


# SETUP SETTINGS AND TARGETS
include cookbook/setup.mk
include cookbook/setup_python.mk
include cookbook/setup_topics.mk
include cookbook/setup_aws.mk

# Load newspaper list configuration and processing rules
S3_BUCKET_REBUILT ?= 122-rebuilt-final
include cookbook/newspaper_list.mk

# S3 PATH CONVERSION UTILITIES
include cookbook/local_to_s3.mk

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


# FURTHER ADDONS
include cookbook/aggregators_topics.mk

.PHONY: $(PHONY_TARGETS)
