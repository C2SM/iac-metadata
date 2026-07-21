#!/usr/bin/env bash
set -uo pipefail

# Runs the pipeline that used to be the Jenkins "FileSizeNumber" job.
# Invoked over ssh from .github/workflows/file_size_number.yml. Runs
# create_json/file_size_number.py for every dataset in
# create_json/datasets.yaml; each run writes its own meta_<dataset>.json
# and copies it to /net/co2/c2sm-services/zephyr/file_index (see
# FILE_INDEX_DIR in file_size_number.py), served at
# https://data.iac.ethz.ch/zephyr/file_index/.
#
# Datasets are processed sequentially, one ssh session for the whole run -
# unlike the old Jenkins job, which ran datasets in parallel branches. See
# the workflow file for the resulting timeout.

source "$(dirname "$0")/run_pipeline.sh"

clone_and_setup || exit 1

cd zephyr/create_json

failures=0
while IFS= read -r dataset; do
    [ -z "$dataset" ] && continue
    echo "=== file_size_number: $dataset ==="
    python file_size_number.py "$dataset" || failures=$((failures + 1))
done < datasets.txt

echo "Done. $failures dataset(s) failed."
exit $((failures > 0))
