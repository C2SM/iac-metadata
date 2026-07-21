import argparse
import os
import yaml

# Set up argument parser
parser = argparse.ArgumentParser(
    description="Load datasets from a YAML file and write them to a text file."
)
parser.add_argument("datasets_yaml_path",
                    help="The path to the datasets.yaml file",
                    type=str)

# Parse arguments
args = parser.parse_args()

# Get the current directory
current_dir = os.path.dirname(os.path.realpath(__file__))

# Load the datasets from the YAML file
datasets = list(yaml.safe_load(open(args.datasets_yaml_path)).keys())

# Provide the absolute path to the datasets.txt file
datasets_txt_path = os.path.join(current_dir, "datasets.txt")

# Write the datasets to the datasets.txt file
with open(datasets_txt_path, "w") as file:
    for dataset in datasets:
        file.write(dataset + "\n")
