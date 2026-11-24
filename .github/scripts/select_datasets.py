"""
Select the datasets to run for a pull request (dry_run.yml) or a push to
main (file_index.yml, file_size_number.yml) and print them as GitHub step
outputs: `run` (true/false) and `datasets` (space-separated, empty for
all). Compares the checked-out commit with its first parent: the base
branch for a pull request's merge commit, the previous main for a squash
merge.

If only src/datasets.yaml or src/datasets.json changed, just the added or
modified datasets are selected. Any other change to the pipeline selects
all datasets, unless --config-only is given: then other changes are
ignored, and the nightly runs pick them up instead.
"""
import subprocess
import sys

import yaml

CONFIG_FILES = {'src/datasets.yaml', 'src/datasets.json'}
PIPELINE_FILES = ('src/', '.github/workflows/dry_run.yml',
                  '.github/scripts/select_datasets.py')


def git(*args):
    return subprocess.run(['git', *args], check=True, capture_output=True,
                          text=True).stdout


changed = git('diff', '--name-only', 'HEAD^1', 'HEAD').split()

if '--config-only' not in sys.argv and any(
        f.startswith(PIPELINE_FILES) and f not in CONFIG_FILES for f in changed):
    run, datasets = True, []
else:
    old = yaml.safe_load(git('show', 'HEAD^1:src/datasets.yaml'))
    with open('src/datasets.yaml') as f:
        new = yaml.safe_load(f)
    datasets = [name for name, value in new.items() if old.get(name) != value]
    run = bool(datasets)

print(f"run={str(run).lower()}")
print(f"datasets={' '.join(datasets)}")
