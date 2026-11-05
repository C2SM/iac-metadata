# shellcheck shell=bash
# Shared by run_file_index.sh and run_file_size_number.sh - not executable
# on its own, meant to be `source`d for its functions: setup_venv() creates
# a venv and installs this repo's requirements.txt, run_datasets() loops
# one of the per-dataset scripts over the selected datasets.
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

    "$uv" venv --clear .venv &&
    source .venv/bin/activate &&
    "$uv" pip install -r requirements.txt
}

# Usage: run_datasets <script.py> [--dry-run] [dataset ...]
# Runs <script.py> for the given datasets, or for every dataset in
# datasets.yaml if none are given. --dry-run is passed on to the script,
# which then writes its JSON files locally without publishing them.
run_datasets() {
    local script="$1"
    shift
    local dry_run=()
    local datasets=()
    for arg in "$@"; do
        case "$arg" in
            --dry-run) dry_run=(--dry-run) ;;
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
        python "$script" "$dataset" "${dry_run[@]}" || failures=$((failures + 1))
    done

    echo "Done. $failures dataset(s) failed."
    return $((failures > 0))
}
