# IAC Metadata

GitHub Actions replacement for the Jenkins `FileIndex` and `FileSizeNumber`
jobs that used to run in [C2SM/zephyr](https://github.com/C2SM/zephyr).
Keeps the metadata that drives the [zephyr-frontend](https://github.com/C2SM/zephyr-frontend)
dataset browser up to date: for every dataset in [`src/datasets.yaml`](src/datasets.yaml),
it scans `/net/atmos/data` and publishes the result to
`/net/co2/c2sm-services/zephyr/file_index`, served at
[https://data.iac.ethz.ch/zephyr/file_index/](https://data.iac.ethz.ch/zephyr/file_index/).

This is a standalone repo: [`src/file_tree.py`](src/file_tree.py),
[`src/file_size_number.py`](src/file_size_number.py),
[`src/get_datasets.py`](src/get_datasets.py) and
[`src/datasets.yaml`](src/datasets.yaml) were moved here from
`C2SM/zephyr`'s former `create_json/` directory - they only ever generated
this metadata and weren't used by zephyr's actual extraction engine, so
there's nothing left to keep in sync between the two repos.

## Workflows

| Workflow | Schedule | Runs |
|---|---|---|
| [`file_index.yml`](.github/workflows/file_index.yml) | Daily, 02:00 UTC | `file_tree.py` for every dataset -> `file_tree_*.json` |
| [`file_size_number.yml`](.github/workflows/file_size_number.yml) | Daily, 03:00 UTC | `file_size_number.py` for every dataset -> `meta_*.json` |

Both also accept `workflow_dispatch` for a manual run:

```bash
gh workflow run file_index.yml --repo C2SM/iac-metadata
gh workflow run file_size_number.yml --repo C2SM/iac-metadata
```

## How it works

GitHub-hosted runners can't reach `iacdipl-7.ethz.ch` directly (ETH's
firewall drops non-ETH-network SSH), so each workflow proxies through
`fog.ethz.ch`, uploads [`src/`](src/) over `rsync`, and runs the
corresponding script on iacdipl-7 - the same ssh pattern used by
[C2SM/zephyr-request](https://github.com/C2SM/zephyr-request), reusing the
same `l_c2sm` account on iacdipl-7 that the Jenkins `atmos`-labeled agent
ran as (it has filesystem access to both `/net/atmos/data` and
`/net/co2/c2sm-services/zephyr/file_index`).

```
GitHub Actions (ubuntu-latest) --ssh--> fog.ethz.ch --ssh--> iacdipl-7.ethz.ch
                                                              (l_c2sm)
                                                              /net/atmos/data (read)
                                                              /net/co2/c2sm-services/zephyr/file_index (write)
```

Unlike the old Jenkins jobs, which ran each dataset as a parallel branch,
[`src/run_file_index.sh`](src/run_file_index.sh) and
[`src/run_file_size_number.sh`](src/run_file_size_number.sh) process
datasets sequentially in a single ssh session - simpler, at the cost of
wall-clock time. The workflow timeouts (300 minutes each) are sized
generously for this; if a daily run starts running too long in practice,
switching to a per-dataset GitHub Actions matrix (like
`zephyr-request`'s [`testsuite.yml`](https://github.com/C2SM/zephyr-request/blob/main/.github/workflows/testsuite.yml))
would restore parallelism at the cost of more concurrent ssh sessions
through the fog bastion.

The old Jenkins `FileIndex` job also triggered a downstream `zephyr-daily`
Jenkins job on success; that trigger has not been carried over here since
its purpose wasn't documented in the Jenkinsfile - add it back (e.g. as a
final step calling `gh workflow run` in some other repo) if it's still
needed.

## Setup

### Repository secrets

Configure under **Settings -> Secrets and variables -> Actions**:

| Name | Type | Purpose |
|---|---|---|
| `FOG_SSH_KEY` | Secret | Private key for `ti16102` on `fog.ethz.ch` (bastion hop only) |
| `IACDIPL7_SSH_KEY` | Secret | Private key for `l_c2sm` on `iacdipl-7.ethz.ch` |

These can be the same key pairs already configured on
`C2SM/zephyr-request` (same accounts, same hosts), or dedicated keys
authorized for the same accounts - either way they need to be added here
explicitly, secrets aren't shared across repositories.

### `uv` on iacdipl-7

Both scripts use [`uv`](https://docs.astral.sh/uv/) (`~/.local/bin/uv`,
referenced by absolute path since non-interactive SSH sessions don't
source `~/.bashrc`) to create a fresh virtual environment per run and
install [`src/requirements.txt`](src/requirements.txt) (`pandas`,
`PyYAML`, `tqdm`) into it. This is the same `uv` install already required
by `C2SM/zephyr-request` on the `l_c2sm` account - no extra setup needed
if that's already in place.

## Repository structure

```
.
├── src/
│   ├── datasets.yaml             # Dataset definitions (paths, labels, patterns)
│   ├── file_tree.py              # Scans a dataset -> file_tree_<dataset>*.json
│   ├── file_size_number.py       # Computes a dataset's size/count -> meta_<dataset>.json
│   ├── get_datasets.py           # Extracts dataset names from datasets.yaml -> datasets.txt
│   ├── requirements.txt          # pandas, PyYAML, tqdm
│   ├── run_pipeline.sh           # Shared: create venv, install requirements
│   ├── run_file_index.sh         # Loops file_tree.py over all datasets
│   └── run_file_size_number.sh   # Loops file_size_number.py over all datasets
└── .github/workflows/
    ├── file_index.yml            # Daily: runs run_file_index.sh on iacdipl-7
    └── file_size_number.yml      # Daily: runs run_file_size_number.sh on iacdipl-7
```

## Related repositories

- **[C2SM/zephyr](https://github.com/C2SM/zephyr)** - core extraction engine consuming the file index this repo publishes; no longer contains `create_json/`
- **[C2SM/zephyr-request](https://github.com/C2SM/zephyr-request)** - GitHub Issues-based request processing; this repo's fog/iacdipl-7 SSH pattern is copied from its `process_request.yml`
- **[C2SM/zephyr-frontend](https://github.com/C2SM/zephyr-frontend)** - consumes the JSON files this repo publishes
