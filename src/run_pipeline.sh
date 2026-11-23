# shellcheck shell=bash
# Shared by run_file_index.sh and run_file_size_number.sh - not executable
# on its own, meant to be `source`d for its functions: setup_venv() creates
# a venv and installs this repo's requirements.txt, run_datasets() loops
# one of the per-dataset scripts over the selected datasets.
#
# Expects to be run from the uploaded src/ directory (this repo, rsynced
# over by the workflow - see .github/workflows/), on a host with
# filesystem access to /net/atmos/data (dataset source) and
# /net/co2/c2sm-services/zephyr/file_index (JSON destination) - the
# target host of the workflows (same account the Jenkins "atmos"-labeled
# agent ran as), and uv already installed for this account
# (~/.local/bin/uv) - see C2SM/zephyr-request's README for setup.

setup_venv() {
    uv="$HOME/.local/bin/uv"

    "$uv" venv --clear .venv &&
    source .venv/bin/activate &&
    "$uv" pip install -r requirements.txt
}

# Usage: run_datasets <script.py> [--dry-run] [dataset ...]
# Runs <script.py> for the given datasets, or for every dataset in
# datasets.yaml if none are given. The script is called with --upload to
# publish its JSON files, unless --dry-run is given (local files only).
run_datasets() {
    local script="$1"
    shift
    local upload=(--upload)
    local datasets=()
    for arg in "$@"; do
        case "$arg" in
            --dry-run) upload=() ;;
            *) datasets+=("$arg") ;;
        esac
    done

    if [ ${#datasets[@]} -eq 0 ]; then
        python get_datasets.py datasets.yaml
        mapfile -t datasets < datasets.txt
    fi

    local failures=0
    for dataset in "${datasets[@]}"; do
        [ -z "$dataset" ] && continue
        echo "=== ${script%.py}: $dataset ==="
        python "$script" "$dataset" "${upload[@]}" || failures=$((failures + 1))
    done

    echo "Done. $failures dataset(s) failed."
    return $((failures > 0))
}
