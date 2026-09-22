import os
import json
import logging
import glob
import shutil
import pandas as pd
from datetime import datetime
import argparse
import yaml

FILE_INDEX_DIR = '/net/co2/c2sm-services/zephyr/file_index'


def group_consecutive_dates(dates, dataset):
    """
    Groups consecutive dates in the given array and stores them as strings representing ranges.

    Args:
    dates (list): A list of strings representing dates in the format 'YYYYMM'.
    dataset: A dictionary containing the dataset information.

    Returns:
    list: A list containing grouped consecutive dates as strings in the format "start-end".
    """

    pattern = dataset['pattern']['date']
    freq = dataset['freq']
    grouped_dates = []
    current_group = [datetime.strptime(dates[0], pattern)]

    for i in range(1, len(dates)):
        current_date = datetime.strptime(dates[i], pattern)
        previous_date = current_group[-1]

        # Calculate the difference in months or years based on the frequency
        if freq == 'M':
            difference = (current_date.year - previous_date.year
                          ) * 12 + current_date.month - previous_date.month
        elif freq == 'Y':
            difference = current_date.year - previous_date.year
        else:
            raise ValueError(
                "Invalid frequency. Please use 'M' for month or 'Y' for year.")

        if difference == 1:
            current_group.append(current_date)
        else:
            if len(current_group) > 1:
                grouped_dates.append(
                    f"{current_group[0].strftime(pattern)}-{current_group[-1].strftime(pattern)}"
                )
            else:
                grouped_dates.append(current_group[0].strftime(pattern))
            current_group = [current_date]

    if len(current_group) > 1:
        grouped_dates.append(
            f"{current_group[0].strftime(pattern)}-{current_group[-1].strftime(pattern)}"
        )
    else:
        grouped_dates.append(current_group[0].strftime(pattern))

    return grouped_dates


def test_group_consecutive_dates():
    assert group_consecutive_dates([
        '194101', '194102', '194103', '194104', '194105', '194106', '194107',
        '194108', '194109', '194110', '194111', '194201', '194202', '194203',
        '194204', '194205', '194206', '194207', '194208', '194209', '194210',
        '194211', '199901', '202203'
    ], '%Y%M', 'M') == [['194101', '194111'], ['194201', '194211'], '199901',
                        '202203']


def remove_late_historical(dates, dataset):
    result = []

    for date_range in dates:
        if '-' in date_range:
            start, end = date_range.split("-")
            if int(end[:4]) < dataset['historical_before']:
                result.append(date_range)
            else:
                logging.warning(
                    f"Removing entry that exceeds historical end date: {date_range}"
                )
                print(
                    f"WARNING: Removing entry that exceeds historical end date: {date_range}"
                )

    return result


def detect_format(date_str):
    """
    Detects the date format based on the length of the date string.
    """
    if len(date_str) == 12:
        return "%Y%m%d%H%M"
    elif len(date_str) == 10:
        return "%Y%m%d%H"
    elif len(date_str) == 8:
        return "%Y%m%d"
    elif len(date_str) == 6:
        return "%Y%m"
    elif len(date_str) == 4:
        return "%Y"
    return None


def log_and_print_warning(end_current_str, start_next_str):
    """
    Logs and prints a warning for missing dates.
    """
    logging.warning(
        f"Missing date between {end_current_str} and {start_next_str}")
    print(
        f"WARNING: Missing date between {end_current_str} and {start_next_str}"
    )


def check_completeness(file_list, dataset, path):
    """
    Check the completeness of a file list based on the file names.

    This function takes a list of file names and checks for missing dates in the file names.
    It extracts the common substring from the file names and the year and month from each file name.
    It then creates a date range from the start to the end of the extracted dates and compares it with the actual dates.
    Finally, it returns a dictionary containing information about the file, the date range, and any missing dates.

    Args:
        file_list (list): A list of file names.
        dataset: A dictionary containing the dataset information.

    Returns:
        dict: A dictionary containing the following keys:
            - "file": A string representing the file name pattern with placeholders for the year and common substring.
            - "date_range": A string representing the date range in the format "start_date, end_date".
            - "missing": A list of strings representing the missing dates in the format pattern.

    Example:
        >>> file_list = [
        ...     "file_202101.nc",
        ...     "file_202102.nc",
        ...     "file_202104.nc",
        ...     "file_202105.nc"
        ... ]
        >>> check_completeness(file_list, 'M')
        {
            "file": "{YYYY}/file_{YYYYMM}.nc",
            "date_range": "202101, 202105",
            "missing": ["202103"]
        }
    """

    # Extract the year and month from each file name
    dates = [file.split('_')[-1].split('.')[0] for file in file_list]

    # Extract the parts of the file name
    file_parts = [file.split('_') for file in file_list]

    # Handle files with "fx" in the name
    if any('fx' in parts for parts in file_parts):
        # 'fx' files do not have time information -> return an empty dict
        return {}

    # Patterns for ERA5 and CERRA
    if 'freq' in dataset:
        # Convert the dates to pandas datetime objects
        dates = pd.to_datetime(dates, format=dataset['pattern']['date'])
        freq = dataset['freq']

        # Convert 'M' to 'ME' for pandas compatibility
        if freq == 'M':
            freq = 'ME'

        # Create a date range from the start to the end
        date_range = pd.date_range(start=dates.min(),
                                   end=dates.max(),
                                   freq=freq)

        # Convert the date range back to the same format as in the file names
        date_range = date_range.strftime(dataset['pattern']['date'])

        # Find the missing dates
        missing = list(
            set(date_range) - set(dates.strftime(dataset['pattern']['date'])))

        # Sort and group consecutive dates into ranges
        if missing:
            missing.sort()
            missing = group_consecutive_dates(missing, dataset)

        result = {
            "date_range":
            f"{dates.min().strftime(dataset['pattern']['date'])}-{dates.max().strftime(dataset['pattern']['date'])}"
        }

        # Only append missing if it's not empty
        if missing:
            result["missing"] = missing

        return result

    else:
        # Remove files that exceed historical end date
        dates = remove_late_historical(
            dates, dataset) if 'historical' in path else dates

        # If dates is empty, return an empty dict
        if not dates:
            return {}

        # Group dates by format
        grouped_dates = {}
        for date_str in dates:
            date_format = detect_format(date_str.split('-')[0])
            if date_format not in grouped_dates:
                grouped_dates[date_format] = []
            grouped_dates[date_format].append(date_str)

        result = {}

        for date_format, date_list in grouped_dates.items():
            # Sort the dates
            date_list.sort()

            # Find the minimum and maximum dates
            start_date = date_list[0].split('-')[0]
            end_date = date_list[-1].split('-')[-1]

            result["date_range"] = f"{start_date}-{end_date}"

        return result


def build_flat_leaf_tree(file_list, labels, label_index):
    """
    Builds a nested dictionary from a flat list of files whose names encode
    the remaining labels as underscore-separated tokens, one token per
    label, in the same order as `labels` (e.g. cmip6-ng, where GCM,
    scenario, ensemble_member and grid all live in the filename rather than
    as further subdirectories).
    FOr CORDEX-FPSCONV the last label is the date which needs to

    Args:
        file_list (list): File names (no directory component).
        labels (list): The dataset's full labels list.
        label_index (int): Index of the first label still to be resolved;
            labels before this index are already represented by the
            directory path and are skipped when splitting each filename.

    Returns:
        dict: Nested dictionary representing the remaining labels.
    """
    tree = {}
    logging.info(f"Building tree with label_index: {label_index}")
    print(f"Building tree with label_index: {label_index}")
    for filename in file_list:
        stem = filename.rsplit('.', 1)[0]
        tokens = stem.split('_')
        if len(tokens) != len(labels[label_index:]):
            #logging.warning(f"Skipping file with unexpected name shape: {filename}")
            #print(f"WARNING: Skipping file with unexpected name shape: {filename}")
            logging.warning(f"Expected {len(labels)} labels ({', '.join(labels)}) got {len(tokens)} tokens: {tokens}")
            #print(f"WARNING: Expected {len(labels)} labels ({', '.join(labels)}) tokens, got {len(tokens)}: {tokens}")
            #continue
        node = tree
        for token in tokens[label_index:-1]:
            node = node.setdefault(token, {})
        if "-" in tokens[-1]:
            # for CORDEX-FPSCONV the last label is the date which needs to be stored as a set of date ranges
            node.setdefault("date_range", {tokens[-1]})
        else:
            # for cmip6-ng there is no date in the last label, so we just store the last token as a key with an empty dict as value
            node.setdefault(tokens[-1], {})
    return tree


def build_file_tree(directory, dataset, label_index, tree=None):
    """
    Recursively builds a nested dictionary representing the file tree starting from `directory`.
    Args:
        directory (str): The root directory from which to build the file tree.
        dataset: A dictionary containing the dataset information.
        label_index (int): The index in the labels list for the current directory level.
        tree (dict, optional): Used for recursive calls to represent the current state of the tree.
    Returns:
        dict: Nested dictionary representing the file tree.
    """
    if tree is None:
        tree = {}

    # CORDEX, CMIP5 and CMIP6 fold the scenario into directory_paths itself
    # (map_root=True, labels[0]='scenario'), so the first real subdirectory
    # already represents labels[1], not labels[0].
    is_dataset_with_scenario_label = (dataset.get('map_root', False) and
                                      dataset.get('labels', [''])[0].lower()
                                      == 'scenario')

    # Increment the label_index + 1
    if is_dataset_with_scenario_label and label_index == 0:
        label_index += 1

    # If is_dataset_with_scenario_label = False, check to avoid out of index
    if label_index < len(dataset['labels']):
        logging.info(
            f"Entering directory: {directory} with label: {dataset['labels'][label_index]}"
        )
        print(f"Entering directory {directory}")
    print(dataset)
    if dataset['labels'][label_index] == dataset['labels'][-1] and not any(os.path.isdir(os.path.join(directory, item)) for item in os.listdir(directory)):
        logging.info(f"Reached final label for directory: {directory}")
        print(f"Reached final label for directory: {directory}")
        path = directory
        # Return a file list
        file_list = sorted(glob.glob(f"{path}/{dataset['pattern']['file']}"))
        file_list = [
            os.sep.join(os.path.normpath(path).split(os.sep)[-2:])
            for path in file_list
        ]
        if file_list:
            if 'fx' in file_list[0]:
                tree = {}
            else:
                result = check_completeness(file_list, dataset, path)
                tree = result
        else:
            logging.warning(f"Skipping empty directory '{path}'")
            print(f"Skipping empty directory '{path}'")
    else:
        logging.info(f"Processing directory: {directory} with label: {dataset['labels'][label_index]}"
        )
        print(f"Processing directory: {directory} with label: {dataset['labels'][label_index]}"
        )
        items = sorted(os.listdir(directory))

        # Some datasets (e.g. cmip6-ng) stop nesting subdirectories before
        # the last label: the remaining labels are encoded in the file
        # names instead. Detect that by checking whether this directory
        # holds files rather than further subdirectories.
        if items and all(
                not os.path.isdir(os.path.join(directory, item))
                for item in items):
            file_list = sorted(
                os.path.basename(f) for f in glob.glob(
                    f"{directory}/{dataset['pattern']['file']}"))
            print(
                f"Reached final label for directory: {directory}, building flat leaf tree")
            if file_list:
                tree = build_flat_leaf_tree(file_list, dataset['labels'],
                                           label_index)
            else:
                logging.warning(f"Skipping empty directory '{directory}'")
                print(f"Skipping empty directory '{directory}'")
            return tree

        for item in items:
            path = os.path.join(directory, item)
            # Normalize the path and blacklist items to lowercase for case-insensitive comparison
            if any(
                    os.path.normpath(path).lower().endswith(
                        blacklisted_item.lower())
                    for blacklisted_item in dataset['blacklist']):
                logging.info(
                    f"Skipping directory '{path}' as it contains a blacklisted item"
                )
                print(
                    f"Skipping directory '{path}' as it contains a blacklisted item"
                )
                continue  # Skip the blacklisted directory
            if os.path.isdir(path):
                subtree = {}
                tree[item] = build_file_tree(path, dataset, label_index + 1,
                                             subtree)
            logging.info(f"Finished processing directory: {item} at {path}")

    logging.info(f"Completed mapping directory: {directory}")
    return tree


def save_file_tree_to_json(file_tree, output_file, indent=None):
    """
    Save the generated file tree dictionary to a JSON file.
    Args:
        file_tree (dict): The file tree to save.
        output_file (str): The path to the JSON file where the file tree will be saved.
        indent (int, optional): The number of spaces to use for indentation.
    """
    with open(output_file, 'w') as f:
        json.dump(file_tree, f, indent=indent)
    logging.info(f"File tree successfully saved to {output_file}")

    shutil.copy2(output_file, FILE_INDEX_DIR)
    logging.info(f"File {output_file} copied to {FILE_INDEX_DIR}")


def main(dataset, output_path):
    # Setup basic configuration for logging
    logging.basicConfig(filename=f'{output_path}/file_tree_{dataset}.log',
                        level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s',
                        filemode='w')

    with open('datasets.yaml', 'r') as f:
        datasets = yaml.safe_load(f)

    directory_paths = datasets[dataset]['directory_paths']
    labels = datasets[dataset]['labels']
    pattern = datasets[dataset]['pattern']
    freq = datasets[dataset]['freq'] if 'freq' in datasets[dataset] else None
    blacklist = datasets[dataset]['blacklist']
    map_root = datasets[dataset].get('map_root', False)

    logging.info("Starting to create file trees.")
    file_tree_root = {}
    file_tree_root['labels'] = labels
    #file_tree_root['freq'] = freq
    file_tree_root['data'] = {}
    for path in directory_paths:
        logging.info(
            f"Starting file tree creation for the root directory at {path}")

        if map_root:  # Check if map_root is True
            # Initialize the nested structure with the root directory name
            root_dir_name = os.path.basename(path.rstrip(os.sep))
            file_tree_root['data'][root_dir_name] = {}

            # Apply labels starting with the first label for each sub-directory, skipping 'work'
            for item in sorted(os.listdir(path)):
                item_path = os.path.join(path, item)
                if any(blacklisted_item in item.lower()
                       for blacklisted_item in blacklist):
                    logging.info(
                        f"Skipping directory '{item}' as it contains a blacklisted item"
                    )
                    print(
                        f"Skipping directory '{item}' as it contains a blacklisted item"
                    )
                    continue  # Skip the blacklisted directory
                if os.path.isdir(item_path):
                    # Use the nested structure
                    file_tree_root['data'][root_dir_name][
                        item] = build_file_tree(item_path, datasets[dataset],
                                                0)
                    logging.info(f"File tree creation for {item} completed.")
        else:
            # Apply labels starting with the first label for each sub-directory, skipping 'work'
            for item in sorted(os.listdir(path)):
                item_path = os.path.join(path, item)
                if any(blacklisted_item in item.lower()
                       for blacklisted_item in blacklist):
                    logging.info(
                        f"Skipping directory '{item}' as it contains a blacklisted item"
                    )
                    print(
                        f"Skipping directory '{item}' as it contains a blacklisted item"
                    )
                    continue  # Skip the blacklisted directory
                if os.path.isdir(item_path):
                    file_tree_root['data'][item] = build_file_tree(
                        item_path, datasets[dataset], 0)
                    logging.info(f"File tree creation for {item} completed.")

    # Save the file trees to a JSON file
    output_filename = f'file_tree_{dataset}.json'
    output_json_path = os.path.join(output_path, output_filename)
    save_file_tree_to_json(file_tree_root, output_json_path, indent=2)
    logging.info(
        f"File tree JSON file (human-readable) saved to {output_json_path}")

    # Save the file trees to a JSON file without indentation
    output_filename = f'file_tree_{dataset}_noindent.json'
    output_json_path = os.path.join(output_path, output_filename)
    save_file_tree_to_json(file_tree_root, output_json_path)
    logging.info(
        f"File tree JSON file (without indentation) saved to {output_json_path}"
    )


if __name__ == "__main__":
    # Load the datasets from the yaml file
    with open('datasets.yaml', 'r') as file:
        datasets = yaml.safe_load(file)

    # Extract the top-level keys from the datasets
    dataset_names = list(datasets.keys())

    parser = argparse.ArgumentParser()
    parser.add_argument("dataset",
                        help="Name of the dataset",
                        choices=dataset_names)
    parser.add_argument("-o",
                        "--output",
                        help="Output path for the JSON files",
                        default=".")
    args = parser.parse_args()
    main(args.dataset, args.output)
