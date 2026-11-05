import json

import pytest
import yaml

import file_size_number as fsn


@pytest.mark.parametrize('size, expected', [
    (0, '0 B'),
    (512, '512.0 B'),
    (1536, '1.5 KB'),
    (3 * 1024**4, '3.0 TB'),
])
def test_bytes_to_readable_format(size, expected):
    assert fsn.bytes_to_readable_format(size) == expected


def test_calculate_directory_metrics(tmp_path):
    (tmp_path / 'a').mkdir()
    (tmp_path / 'a' / 'one.nc').write_bytes(b'x' * 10)
    (tmp_path / 'two.nc').write_bytes(b'x' * 20)

    assert fsn.calculate_directory_metrics(str(tmp_path)) == ('30.0 B', 2)


def test_calculate_directory_metrics_missing_directory(tmp_path):
    assert fsn.calculate_directory_metrics(str(tmp_path / 'missing')) == (
        'Directory does not exist', 0)


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    """A datasets.yaml pointing to tmp_path/data, and a fake file index."""
    index = tmp_path / 'index'
    index.mkdir()
    monkeypatch.setattr(fsn, 'FILE_INDEX_DIR', str(index))
    monkeypatch.chdir(tmp_path)
    data = tmp_path / 'data'
    data.mkdir()
    (tmp_path / 'datasets.yaml').write_text(
        yaml.safe_dump({'demo': {'directory_paths': [str(data)]}}))
    out = tmp_path / 'out'
    out.mkdir()
    return data, out, index


def test_main(workspace):
    data, out, _ = workspace
    (data / 'tas.nc').write_bytes(b'x' * 2048)

    fsn.main('demo', str(out))

    meta = json.loads((out / 'meta_demo.json').read_text())
    assert meta['file_count'] == 1
    assert meta['total_size'] == '2.0 KB'


def test_main_exits_without_files(workspace):
    _, out, index = workspace

    with pytest.raises(SystemExit) as exit_info:
        fsn.main('demo', str(out))

    assert exit_info.value.code != 0
    assert not list(out.iterdir())
    assert not list(index.iterdir())
