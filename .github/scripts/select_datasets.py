"""
Select the datasets to dry-run for a pull request and print them as
GitHub step outputs: `run` (true/false) and `datasets` (space-separated,
empty for all). Compares the checked-out merge commit with its first
parent, the base branch.

If only src/datasets.yaml or src/datasets.json changed, just the added or
modified datasets are selected. Any other change to the pipeline selects
all datasets.
"""
import subprocess

import yaml

CONFIG_FILES = {'src/datasets.yaml', 'src/datasets.json'}
PIPELINE_FILES = ('src/', '.github/workflows/dry_run.yml',
                  '.github/scripts/select_datasets.py')


def git(*args):
    return subprocess.run(['git', *args], check=True, capture_output=True,
                          text=True).stdout


changed = git('diff', '--name-only', 'HEAD^1', 'HEAD').split()

if any(f.startswith(PIPELINE_FILES) and f not in CONFIG_FILES for f in changed):
    run, datasets = True, []
else:
    old = yaml.safe_load(git('show', 'HEAD^1:src/datasets.yaml'))
    with open('src/datasets.yaml') as f:
        new = yaml.safe_load(f)
    datasets = [name for name, value in new.items() if old.get(name) != value]
    run = bool(datasets)

print(f"run={str(run).lower()}")
print(f"datasets={' '.join(datasets)}")
