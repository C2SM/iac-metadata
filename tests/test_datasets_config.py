"""Validate src/datasets.yaml and src/datasets.json without access to the data."""
import json
import re
from pathlib import Path

import pytest
import yaml

SRC = Path(__file__).resolve().parent.parent / 'src'
DATASETS = yaml.safe_load((SRC / 'datasets.yaml').read_text())
PICKER = json.loads((SRC / 'datasets.json').read_text())

# Extend these sets when the scripts learn a new option.
REQUIRED_KEYS = {'directory_paths', 'labels', 'pattern', 'blacklist'}
OPTIONAL_KEYS = {'freq', 'historical_before', 'map_root'}
PATTERN_KEYS = {'file', 'date', 'prefix', 'suffix', 'filename_labels'}
FREQUENCIES = {'M', 'YE'}


def is_str_list(value):
    return isinstance(value, list) and all(isinstance(v, str) for v in value)


@pytest.mark.parametrize('name', DATASETS)
def test_dataset_definition(name):
    # Dataset names end up on the command line of the pipeline scripts
    assert re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', name)

    dataset = DATASETS[name]
    assert REQUIRED_KEYS <= dataset.keys(), 'missing required keys'
    assert dataset.keys() <= REQUIRED_KEYS | OPTIONAL_KEYS, 'unknown keys'

    paths = dataset['directory_paths']
    assert is_str_list(paths) and paths
    assert all(p.startswith('/') for p in paths), 'paths must be absolute'

    labels = dataset['labels']
    assert is_str_list(labels) and labels
    assert len(set(labels)) == len(labels), 'duplicate labels'

    pattern = dataset['pattern']
    assert isinstance(pattern, dict) and pattern.keys() <= PATTERN_KEYS
    assert isinstance(pattern.get('file'), str) and pattern['file']

    assert is_str_list(dataset['blacklist'])

    if 'freq' in dataset:
        assert dataset['freq'] in FREQUENCIES
        assert 'date' in pattern, 'freq requires pattern.date'
    if 'historical_before' in dataset:
        assert isinstance(dataset['historical_before'], int)
    if 'map_root' in dataset:
        assert isinstance(dataset['map_root'], bool)


def test_picker_entries():
    keys = [entry['key'] for entry in PICKER]
    assert len(set(keys)) == len(keys), 'duplicate keys in datasets.json'
    for entry in PICKER:
        assert entry.keys() == {'key', 'name', 'description'}, entry
        assert entry['key'] in DATASETS, f"{entry['key']} not in datasets.yaml"
        assert entry['name'], entry
