import glob
from pathlib import Path

import yaml
import sys

from pydantic import ValidationError
from argparse import ArgumentParser

from metamorphic.results import Result
from metamorphic.rules import *
from metamorphic.tests import Test
from user_sim.utils.utilities import check_keys
import user_sim.errors as errors

def __get_object_from_yaml_files(file_or_dir, operation, name):
    objects = []
    if os.path.isfile(file_or_dir):
        yaml_files = [file_or_dir]
    else:
        yaml_files = (glob.glob(os.path.join(file_or_dir, '**/*.yaml'), recursive=True) +
                      glob.glob(os.path.join(file_or_dir, '**/*.yml'), recursive=True))

    for file_path in yaml_files:
        if "__report__" in file_path:
            continue

        with open(file_path, 'r', encoding='utf-8') as file:
            if name=='rule':
                yaml_data = yaml.safe_load(file.read())
            else:
                yaml_data = yaml.safe_load_all(file.read())
        try:
            object = operation(file_path, yaml_data)
        except ValidationError as e:
            raise ValueError(f"Validation error for {name}:\n {e}")
        objects.append(object)
    return objects


def get_rules_from_yaml_files(directory):
    return __get_object_from_yaml_files(directory, lambda file_path, data: Rule(**data), 'rule')


def get_tests_from_yaml_files(conversations):
    return __get_object_from_yaml_files(conversations, lambda file_path, data: Test.build_test(file_path, data), 'test')


def check_rules(rules, conversations, verbose, csv_file):
    """
    Processes metamorphic rules against a set of conversations
    :param rules: the folder to the metamorphic rules
    :param conversations: the folder to the conversations
    :raises ValueError when paths rules or conversations do not exist
    """
    for folder in [rules, conversations]:
        if not os.path.exists(folder):
            raise ValueError(f"Invalid path: {folder}.")

    print(f"Testing rules at {rules} into conversations at {conversations}")
    rules = get_rules_from_yaml_files(rules)
    rules = [rule for rule in rules if rule.active] # filter the inactive rules
    tests = get_tests_from_yaml_files(conversations)
    result_store = Result()
    for rule in rules:
        results = rule.test(tests, verbose)
        result_store.add(rule.name, results)

    report_generic_error(result_store, tests)

    if csv_file is not None:
        result_store.to_csv(csv_file)


# Add to the report generic checks
def report_generic_error(result_store, tests):
    by_error = {}
    for e in errors.all_errors.keys():
        by_error[e] = {'pass': [], 'fail': [], 'not_applicable': []}
    for c in tests:
        for name, error_code in errors.all_errors.items():
            if error_code in [next(iter(e)) for e in c.errors]:
                by_error[name]['fail'].append(c.file_name)
            else:
                by_error[name]['pass'].append(c.file_name)
    for name, results in by_error.items():
        result_store.add(name, results)


if __name__ == '__main__':
    parser = ArgumentParser(description='Tester of conversations against metamorphic rules')
    parser.add_argument('--rules', required=True, help='Folder with the yaml files containing the metamorphic rules')
    parser.add_argument('--conversations', required=True, help='Folder with the conversations to analyse')
    parser.add_argument('--verbose', default=False, action='store_true')
    parser.add_argument('--dump', required=False, help='CSV file to store the statistics')
    args = parser.parse_args()
    check_keys(["OPENAI_API_KEY"])

    try:
        check_rules(args.rules, args.conversations, args.verbose, args.dump)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
