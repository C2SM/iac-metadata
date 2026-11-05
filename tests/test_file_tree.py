import json

import pytest
import yaml

import file_tree as ft

MONTHLY = {'pattern': {'file': '*.nc', 'date': '%Y%m'}, 'freq': 'M'}
YEARLY = {'pattern': {'file': '*.nc', 'date': '%Y'}, 'freq': 'YE'}
CMIP = {'pattern': {'file': '*.nc'}, 'historical_before': 2015}


def touch(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()


def test_group_consecutive_dates_monthly():
    dates = ['200001', '200002', '200003', '200006', '200008', '200009']
    assert ft.group_consecutive_dates(dates, MONTHLY) == [
        '200001-200003', '200006', '200008-200009'
    ]


def test_group_consecutive_dates_yearly():
    assert ft.group_consecutive_dates(['2000', '2002', '2003'],
                                      YEARLY) == ['2000', '2002-2003']


def test_group_consecutive_dates_rejects_unknown_frequency():
    dataset = {'pattern': {'date': '%Y'}, 'freq': 'D'}
    with pytest.raises(ValueError):
        ft.group_consecutive_dates(['2000', '2002'], dataset)


@pytest.mark.parametrize('date, expected', [
    ('202101011200', '%Y%m%d%H%M'),
    ('2021010112', '%Y%m%d%H'),
    ('20210101', '%Y%m%d'),
    ('202101', '%Y%m'),
    ('2021', '%Y'),
    ('21', None),
])
def test_detect_format(date, expected):
    assert ft.detect_format(date) == expected


def test_remove_late_historical():
    dates = ['185001-201412', '201501-210012', '2000']
    assert ft.remove_late_historical(dates, CMIP) == ['185001-201412']


def test_check_completeness_monthly_with_gaps():
    files = [f'2000/tas_2000{m:02d}.nc' for m in (1, 2, 5, 6, 9)]
    assert ft.check_completeness(files, MONTHLY, '/x') == {
        'date_range': '200001-200009',
        'missing': ['200003-200004', '200007-200008'],
    }


def test_check_completeness_yearly_with_gaps():
    files = ['tas_2000.nc', 'tas_2002.nc', 'tas_2004.nc']
    assert ft.check_completeness(files, YEARLY, '/x') == {
        'date_range': '2000-2004',
        'missing': ['2001', '2003'],
    }


def test_check_completeness_complete():
    files = ['tas_2000.nc', 'tas_2001.nc']
    assert ft.check_completeness(files, YEARLY, '/x') == {
        'date_range': '2000-2001'
    }


def test_check_completeness_without_frequency():
    files = [
        'gn/tas_Amon_GCM_ssp126_r1i1p1f1_gn_201501-210012.nc',
        'gn/tas_Amon_GCM_ssp126_r1i1p1f1_gn_210101-230012.nc',
    ]
    assert ft.check_completeness(files, CMIP, '/data/ssp126') == {
        'date_range': '201501-230012'
    }


def test_check_completeness_drops_late_historical():
    files = [
        'gn/tas_Amon_GCM_historical_r1i1p1f1_gn_185001-201412.nc',
        'gn/tas_Amon_GCM_historical_r1i1p1f1_gn_201501-202012.nc',
    ]
    assert ft.check_completeness(files, CMIP, '/data/historical') == {
        'date_range': '185001-201412'
    }


def test_check_completeness_fixed_fields():
    files = ['gn/orog_fx_GCM_historical_r0i0p0f0_gn.nc']
    assert ft.check_completeness(files, CMIP, '/data/historical') == {}


CMIP6_NG_LABELS = ['variable', 'temporal_resolution', 'grid', 'GCM',
                   'scenario', 'ensemble_member']


def test_build_flat_leaf_tree():
    # cmip6-ng file names end with the grid, which therefore appears twice
    files = [
        'tas_mon_ACCESS-CM2_ssp126_r1i1p1f1_g025.nc',
        'tas_mon_ACCESS-CM2_ssp585_r1i1p1f1_g025.nc',
        'tas_mon_unexpected_g025.nc',
    ]
    assert ft.build_flat_leaf_tree(files, CMIP6_NG_LABELS, 2) == {
        'ACCESS-CM2': {
            'ssp126': {'r1i1p1f1': {'g025': {}}},
            'ssp585': {'r1i1p1f1': {'g025': {}}},
        }
    }


def test_build_file_tree(tmp_path):
    dataset = {**YEARLY, 'labels': ['variable', 'temporal resolution', 'grid'],
               'blacklist': ['work']}
    for year in (2000, 2001, 2003):
        touch(tmp_path / 'tas' / 'day' / 'native' / f'tas_day_{year}.nc')
    (tmp_path / 'tas' / 'mon' / 'native').mkdir(parents=True)
    touch(tmp_path / 'tas' / 'work' / 'native' / 'tas_work_2000.nc')

    assert ft.build_file_tree(str(tmp_path / 'tas'), dataset, 0) == {
        'day': {'native': {'date_range': '2000-2003', 'missing': ['2002']}},
        'mon': {'native': {}},
    }


def test_build_file_tree_with_files_above_last_label(tmp_path):
    # cmip6-ng keeps the remaining labels in the file names
    dataset = {'labels': CMIP6_NG_LABELS, 'pattern': {'file': '*.nc'},
               'blacklist': []}
    grid = tmp_path / 'tas' / 'mon' / 'g025'
    touch(grid / 'tas_mon_GCM-A_ssp126_r1i1p1f1_g025.nc')
    touch(grid / 'tas_mon_GCM-B_ssp585_r1i1p1f1_g025.nc')

    assert ft.build_file_tree(str(tmp_path / 'tas'), dataset, 0) == {
        'mon': {'g025': {
            'GCM-A': {'ssp126': {'r1i1p1f1': {'g025': {}}}},
            'GCM-B': {'ssp585': {'r1i1p1f1': {'g025': {}}}},
        }}
    }


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    """A datasets.yaml in the working directory and a fake file index."""
    index = tmp_path / 'index'
    index.mkdir()
    monkeypatch.setattr(ft, 'FILE_INDEX_DIR', str(index))
    monkeypatch.chdir(tmp_path)

    def write_config(**datasets):
        (tmp_path / 'datasets.yaml').write_text(yaml.safe_dump(datasets))
        out = tmp_path / 'out'
        out.mkdir(exist_ok=True)
        return out

    return tmp_path, write_config


def test_main_with_map_root(workspace):
    tmp_path, write_config = workspace
    root = tmp_path / 'data' / 'historical'
    touch(root / 'mon' / 'tas' / 'gn' / 'tas_mon_gn_185001-201412.nc')
    touch(root / 'work' / 'tas' / 'gn' / 'tas_mon_gn_185001-201412.nc')
    out = write_config(demo={
        **CMIP, 'directory_paths': [str(root)], 'map_root': True,
        'labels': ['scenario', 'temporal_resolution', 'variable', 'grid'],
        'blacklist': ['work']
    })

    ft.main('demo', str(out))

    tree = json.loads((out / 'file_tree_demo.json').read_text())
    assert tree['data'] == {
        'historical': {'mon': {'tas': {'gn': {'date_range': '185001-201412'}}}}
    }
    assert (out / 'file_tree_demo_noindent.json').exists()


def test_main_exits_without_data(workspace):
    tmp_path, write_config = workspace
    (tmp_path / 'data' / 'tas').mkdir(parents=True)
    out = write_config(demo={
        **YEARLY, 'directory_paths': [str(tmp_path / 'data')],
        'labels': ['variable'], 'blacklist': []
    })

    with pytest.raises(SystemExit) as exit_info:
        ft.main('demo', str(out))

    assert exit_info.value.code != 0
    assert not list(out.glob('*.json'))
    assert not list((tmp_path / 'index').iterdir())
