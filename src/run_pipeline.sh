# Shared by run_file_index.sh and run_file_size_number.sh - not executable
# on its own, meant to be `source`d for its clone_and_setup() function.
# Clones zephyr, creates a venv, and resolves the dataset list. Does not
# run any of the per-dataset scripts itself; callers loop over
# zephyr/create_json/datasets.txt themselves.
#
# Required environment variables:
#   ZEPHYR_VERSION   git ref of C2SM/zephyr to check out
#
# Expects to be run from an empty directory, on a host with both:
#   - filesystem access to /net/atmos/data (dataset source) and
#     /net/co2/c2sm-services/zephyr/file_index (JSON destination) -
#     currently iacdipl-7.ethz.ch, as user l_c2sm
#   - an SSH key authorized to clone git@github.com:C2SM/zephyr.git (zephyr
#     is a private repo)
#   - uv already installed for this account (~/.local/bin/uv) - see
#     C2SM/zephyr-request's README for setup, this reuses the same account

clone_and_setup() {
    uv="$HOME/.local/bin/uv"

    git clone --depth 1 -b "$ZEPHYR_VERSION" git@github.com:C2SM/zephyr.git &&
    "$uv" venv .venv &&
    source .venv/bin/activate &&
    "$uv" pip install -r zephyr/tools/requirements/requirements.txt &&
    (cd zephyr/create_json && python get_datasets.py datasets.yaml)
}
