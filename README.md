# IAC Metadata

GitHub Actions replacement for the Jenkins `FileIndex` and `FileSizeNumber`
jobs that used to run in [C2SM/zephyr](https://github.com/C2SM/zephyr).
Keeps the metadata that drives the [zephyr-frontend](https://github.com/C2SM/zephyr-frontend)
dataset browser up to date: for every dataset in [`src/datasets.yaml`](src/datasets.yaml),
it scans `/net/atmos/data` and publishes the result to
`/net/co2/c2sm-services/zephyr/file_index`, served at
[https://data.iac.ethz.ch/zephyr/file_index/](https://data.iac.ethz.ch/zephyr/file_index/).
[`src/datasets.json`](src/datasets.json) - the dataset picker's own button
list - is published the same way; see [datasets.json](#datasetsjson) below.

This is a standalone repo: [`src/file_tree.py`](src/file_tree.py),
[`src/file_size_number.py`](src/file_size_number.py),
[`src/get_datasets.py`](src/get_datasets.py) and
[`src/datasets.yaml`](src/datasets.yaml) were moved here from
`C2SM/zephyr`'s former `create_json/` directory - they only ever generated
this metadata and weren't used by zephyr's actual extraction engine, so
there's nothing left to keep in sync between the two repos.

## Workflows

| Workflow | Trigger | Runs |
|---|---|---|
| [`file_index.yml`](.github/workflows/file_index.yml) | Daily, 02:00 UTC | `file_tree.py` for every dataset -> `file_tree_*.json` |
| [`file_size_number.yml`](.github/workflows/file_size_number.yml) | Daily, 03:00 UTC | `file_size_number.py` for every dataset -> `meta_*.json` |
| [`publish_datasets.yml`](.github/workflows/publish_datasets.yml) | Push to `main` touching `src/datasets.json` | Copies `datasets.json` straight to the file index - no script, no venv |

All three also accept `workflow_dispatch` for a manual run:

```bash
gh workflow run file_index.yml --repo C2SM/iac-metadata
gh workflow run file_size_number.yml --repo C2SM/iac-metadata
gh workflow run publish_datasets.yml --repo C2SM/iac-metadata
```

`file_index.yml` and `file_size_number.yml` take an optional `dataset`
input (a top-level key in [`src/datasets.yaml`](src/datasets.yaml)) to
process only that dataset instead of all of them:

```bash
gh workflow run file_index.yml --repo C2SM/iac-metadata -f dataset=cmip7
gh workflow run file_size_number.yml --repo C2SM/iac-metadata -f dataset=cmip7
```

### Dry run

To test changes without publishing anything, run the scripts by hand on a
host that mounts the dataset directories (e.g. iacdipl-7) with
`--dry-run`. The JSON files are then written to the current directory
only and are not copied to `/net/co2/c2sm-services/zephyr/file_index`:

```bash
rsync -a src/ iacdipl-7:/tmp/iac-metadata-test/
ssh iacdipl-7
cd /tmp/iac-metadata-test
bash run_file_index.sh --dry-run cmip7        # one or more datasets
bash run_file_size_number.sh --dry-run cmip7
```

Leaving out the dataset names processes every dataset in `datasets.yaml`.

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

## datasets.json

[`src/datasets.json`](src/datasets.json) is the list behind the dataset
picker buttons in zephyr-frontend - `{key, name, description}` per dataset.
It's maintained by hand, not generated from `datasets.yaml`: it's a
deliberate curated subset (`datasets.yaml` also has narrower per-scenario
CMIP6 entries like `cmip6_ssp126` that exist only to let `file_tree.py`
scan scenarios separately, not to be offered as their own button) with
user-facing `name`s that don't need to match any internal key. Before this
was moved into the repo it lived only as a hand-edited file directly on
the HTTPS server; now editing `src/datasets.json` and pushing to `main`
publishes it automatically via
[`publish_datasets.yml`](.github/workflows/publish_datasets.yml).

Each entry's `key` has to satisfy two independent constraints at once,
since the frontend uses the same string for both:

- it's sent verbatim as `files_query_options.dataset` in the generated
  request, so it must match a key in zephyr's own
  [`builder_classes`](https://github.com/C2SM/zephyr/blob/main/src/zephyr/path_constructor.py)
  dict (e.g. `era5-land_cds`, not `era5-land`)
- it's used to fetch `file_tree_<key>_noindent.json`, so it must also
  match the corresponding top-level key in `datasets.yaml` (since
  `file_tree.py` names its output after whatever key it was invoked with)

These two constraints happened to disagree for ERA5-Land (`datasets.yaml`
had it as `era5-land`, zephyr expects `era5-land_cds`) until both were
aligned on `era5-land_cds`. If you rename a key here, rename it in
`datasets.yaml` too (and vice versa) - and make sure `file_index.yml` has
run at least once under the new name so `file_tree_<new-key>_noindent.json`
actually exists before `datasets.json` starts pointing at it, or the
frontend will 404 fetching it for that one dataset in the gap.

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
│   ├── datasets.json             # Curated dataset-picker list - see datasets.json above
│   ├── file_tree.py              # Scans a dataset -> file_tree_<dataset>*.json
│   ├── file_size_number.py       # Computes a dataset's size/count -> meta_<dataset>.json
│   ├── get_datasets.py           # Extracts dataset names from datasets.yaml -> datasets.txt
│   ├── requirements.txt          # pandas, PyYAML, tqdm
│   ├── run_pipeline.sh           # Shared: create venv, loop scripts over datasets
│   ├── run_file_index.sh         # Loops file_tree.py over all or selected datasets
│   └── run_file_size_number.sh   # Loops file_size_number.py over all or selected datasets
└── .github/workflows/
    ├── file_index.yml            # Daily: runs run_file_index.sh on iacdipl-7
    ├── file_size_number.yml      # Daily: runs run_file_size_number.sh on iacdipl-7
    └── publish_datasets.yml      # On push: copies datasets.json to iacdipl-7
```

## Related repositories

- **[C2SM/zephyr](https://github.com/C2SM/zephyr)** - core extraction engine consuming the file index this repo publishes; no longer contains `create_json/`
- **[C2SM/zephyr-request](https://github.com/C2SM/zephyr-request)** - GitHub Issues-based request processing; this repo's fog/iacdipl-7 SSH pattern is copied from its `process_request.yml`
- **[C2SM/zephyr-frontend](https://github.com/C2SM/zephyr-frontend)** - consumes the JSON files this repo publishes
