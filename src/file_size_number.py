import argparse
import os
import shutil
import yaml
import json
import math
import time
import logging
from tqdm import tqdm

FILE_INDEX_DIR = '/net/co2/c2sm-services/zephyr/file_index'


def bytes_to_readable_format(size_in_bytes):
    if size_in_bytes == 0:
        return '0 B'
    size_names = ('B', 'KB', 'MB', 'GB', 'TB')
    i = int(math.floor(math.log(size_in_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_in_bytes / p, 2)
    return f'{s} {size_names[i]}'


def calculate_directory_metrics(directory_path):
    total_size = 0
    file_count = 0
    total_files = sum([len(files) for r, d, files in os.walk(directory_path)])
    if not os.path.exists(directory_path):
        return 'Directory does not exist', 0
    with tqdm(total=total_files, desc="Reading Files", unit="files") as pbar:
        for root, dirs, files in os.walk(directory_path, followlinks=True):
            for file in files:
                file_path = os.path.join(root, file)
                # Resolve the path if it's a symbolic link
                if os.path.islink(file_path):
                    file_path = os.path.realpath(file_path)
                # Check if it's a file after resolving the link
                if os.path.isfile(file_path):
                    file_count += 1
                    total_size += os.path.getsize(file_path)
                pbar.update(1)
    readable_total_size = bytes_to_readable_format(total_size)
    return readable_total_size, file_count


def save_json_file(meta_dict, output_file, indent=None):
    """
    Save the generated file tree dictionary to a JSON file.
    Args:
        meta_dict (dict): The dataset meta information to save.
        output_file (str): The path where the JSON file will be saved.
        indent (int, optional): The number of spaces to use for indentation.
    """
    with open(output_file, 'w') as f:
        json.dump(meta_dict, f, indent=indent)
    logging.info(f"File tree successfully saved to {output_file}")

    shutil.copy2(output_file, FILE_INDEX_DIR)
    logging.info(f"File {output_file} copied to {FILE_INDEX_DIR}")


def main(dataset_name, output_path=False):
    with open('datasets.yaml', 'r') as file:
        datasets = yaml.safe_load(file)

    results = {}
    if dataset_name in datasets:
        dataset = datasets[dataset_name]
        directory_path = dataset['directory_paths'][0]
        if len(dataset['directory_paths']) > 1:
            # Go one level up in the directory structure
            directory_path = os.path.dirname(directory_path)

        logging.info(f"Processing {directory_path}...")
        start_time = time.time()
        total_size, file_count = calculate_directory_metrics(directory_path)
        end_time = time.time()
        time_passed = end_time - start_time
        last_updated = time.strftime('%Y-%m-%d %H:%M:%S',
                                     time.localtime(end_time))

        results = {
            'total_size': total_size,
            'file_count': file_count,
            'time_passed': f"{time_passed:.2f} seconds",
            'last_updated': last_updated
        }
    else:
        logging.error(f"Dataset name '{dataset_name}' not found in datasets.")

    output_filename = f'meta_{dataset_name}.json'
    output_json_path = os.path.join(output_path, output_filename)
    save_json_file(results, output_json_path, indent=4)
    logging.info(f"JSON file saved to {output_json_path}")


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
