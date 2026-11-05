"""
Check the JSON files written by a (dry) run of file_tree.py or
file_size_number.py. A script can exit successfully and still produce an
empty result, e.g. for a wrong directory path, label or file pattern in
datasets.yaml, so every dataset must have a non-empty result.

Usage: python check_outputs.py {file_tree,file_size_number} [-o DIR] [dataset ...]
"""
import argparse
import json
import os
import sys

import yaml


def check(script, dataset, output_dir):
    """Return an error message for the dataset's JSON file, or None if it is fine."""
    if script == 'file_tree':
        path = os.path.join(output_dir, f'file_tree_{dataset}.json')
    else:
        path = os.path.join(output_dir, f'meta_{dataset}.json')

    try:
        with open(path) as f:
            content = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        return f'cannot read {path}: {e}'

    if script == 'file_tree' and not content.get('data'):
        return f'{path} contains no data'
    if script == 'file_size_number' and not content.get('file_count'):
        return f'{path} reports no files ({content.get("total_size")})'
    return None


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('script', choices=['file_tree', 'file_size_number'])
    parser.add_argument('datasets',
                        nargs='*',
                        help='Datasets to check (default: all in datasets.yaml)')
    parser.add_argument('-o',
                        '--output',
                        help='Directory holding the JSON files',
                        default='.')
    args = parser.parse_args()

    with open('datasets.yaml') as f:
        datasets = args.datasets or list(yaml.safe_load(f))

    errors = [e for d in datasets if (e := check(args.script, d, args.output))]
    for error in errors:
        print(f'ERROR: {error}')
    print(f'{len(datasets) - len(errors)}/{len(datasets)} dataset(s) OK.')
    sys.exit(1 if errors else 0)
