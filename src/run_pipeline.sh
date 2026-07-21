# Shared by run_file_index.sh and run_file_size_number.sh - not executable
# on its own, meant to be `source`d for its setup_venv() function. Creates
# a venv and installs this repo's requirements.txt. Does not run any of
# the per-dataset scripts itself; callers loop over datasets.txt
# themselves.
#
# Expects to be run from the uploaded src/ directory (this repo, rsynced
# over by the workflow - see .github/workflows/), on a host with
# filesystem access to /net/atmos/data (dataset source) and
# /net/co2/c2sm-services/zephyr/file_index (JSON destination) - currently
# iacdipl-7.ethz.ch, as user l_c2sm (same account the Jenkins
# "atmos"-labeled agent ran as), and uv already installed for this account
# (~/.local/bin/uv) - see C2SM/zephyr-request's README for setup.

setup_venv() {
    uv="$HOME/.local/bin/uv"

    "$uv" venv .venv &&
    source .venv/bin/activate &&
    "$uv" pip install -r requirements.txt
}
