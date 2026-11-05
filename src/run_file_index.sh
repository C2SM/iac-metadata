#!/usr/bin/env bash
set -uo pipefail

# Runs the pipeline that used to be the Jenkins "FileIndex" job. Invoked
# over ssh from .github/workflows/file_index.yml. Runs file_tree.py for
# every dataset in datasets.yaml; each run writes its own
# file_tree_<dataset>*.json and copies it to
# /net/co2/c2sm-services/zephyr/file_index (see FILE_INDEX_DIR in
# file_tree.py), served at https://data.iac.ethz.ch/zephyr/file_index/.
#
# Usage: bash run_file_index.sh [--dry-run] [dataset ...]
# Without datasets, all datasets in datasets.yaml are processed. With
# --dry-run, the JSON files are written to the current directory only.
#
# Datasets are processed sequentially, one ssh session for the whole run -
# unlike the old Jenkins job, which ran datasets in parallel branches. See
# the workflow file for the resulting timeout.

source "$(dirname "$0")/run_pipeline.sh"

setup_venv || exit 1

run_datasets file_tree.py "$@"
