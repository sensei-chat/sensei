import os
import pandas as pd
import yaml
import json
import configparser
from datetime import datetime, timedelta, date
import re
import random
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import importlib.util
from .exceptions import *
from openai import OpenAI
from user_sim.utils.config import errors
import logging

logger = logging.getLogger('Info Logger')


def check_keys(key_list: list):
    if os.path.exists("keys.properties"):
        logger.info("properties found!")
        config = configparser.ConfigParser()
        config.read('keys.properties')

        # Loop over all keys and values
        for key in config['keys']:
            key = key.upper()
            os.environ[key] = config['keys'][key]

    for k in key_list:
        if not os.environ.get(k):
            raise Exception(f"{k} not found")


check_keys(["OPENAI_API_KEY"])
client = OpenAI()


def save_json(msg, test_name, path):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    file_path = os.path.join(path, f'{test_name}_{timestamp}.json')
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(msg, file, indent=4)


def str_to_bool(s):
    if s.lower() in ['true', '1', 'yes', 'y']:
        return True
    elif s.lower() in ['false', '0', 'no', 'n']:
        return False
    else:
        raise ValueError(f"Cannot convert {s} to boolean")


def execute_list_function(path, function_name, arguments=None):
    spec = importlib.util.spec_from_file_location("my_module", path)
    my_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(my_module)

    function_to_execute = getattr(my_module, function_name)

    if arguments:

        if not isinstance(arguments, list):
            arguments = [arguments]

        args = [item for item in arguments if not isinstance(item, dict)]
        dict_list = [item for item in arguments if isinstance(item, dict)]
        kwargs = {k: v for dic in dict_list for k, v in dic.items()}

        try:
            result = function_to_execute(*args, **kwargs)
        except TypeError as e:
            raise InvalidFormat(f"No arguments needed for this function: {e}")

    else:
        try:
            result = function_to_execute()
        except TypeError as e:
            raise InvalidFormat(f"Arguments are needed for this function: {e}")

    return result


def list_to_phrase(s_list: list, prompted=False):  # todo: cambiar a list_to_askabout
    # s_list: list of strings
    # l_string: string values extracted from s_list in string format
    l_string = s_list[0]

    if len(s_list) <= 1:
        return f"{s_list[0]}"
    else:
        for i in range(len(s_list) - 1):
            if s_list[i + 1] == s_list[-1]:
                l_string = f" {l_string} or {s_list[i + 1]}"
            else:
                l_string = f" {l_string}, {s_list[i + 1]}"

    if prompted:
        l_string = "please, ask about" + l_string

    return l_string


def read_yaml(file):
    with open(file, 'r', encoding="UTF-8") as f:
        yam_file = yaml.safe_load(f)
    return yam_file


def generate_serial():
    now = datetime.now()
    # serial = datetime.now().strftime("%Y%m%d%H%M%S") + f"{now.microsecond // 1000:03d}"
    serial = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    return serial


class MyDumper(yaml.Dumper):
    def write_line_break(self, data=None):
        super().write_line_break(data)
        super().write_line_break(data)


def get_error_stats(error_df):
    error_list = error_df['error_code'].unique()

    error_report = []
    for error in error_list:
        error_report.append({'error': error,
                             'count': error_df[error_df['error_code'] == error].shape[0],
                             'conversations': list(error_df[error_df['error_code'] == error]['conversation'])
                             })

    return error_report


def get_time_stats(response_time):
    times = pd.to_timedelta(response_time, unit='s')

    time_report = {
        'average': round(times.mean().total_seconds(), 6),
        'max': round(times.max().total_seconds(), 6),
        'min': round(times.min().total_seconds(), 6)
    }
    return time_report


def save_test_conv(history, metadata, test_name, path, serial, conversation_time, response_time, av_data, counter):
    print("Saving conversation...")

    cr_time = {'conversation time': conversation_time,
               'assistant response time': response_time,
               "response time report": get_time_stats(response_time)}

    path_folder = path + f"/{test_name}"
    if not os.path.exists(path_folder):
        os.makedirs(path_folder)

    data = [metadata, cr_time, history]
    test_folder = path_folder + f"/{serial}"

    if not os.path.exists(test_folder):
        os.makedirs(test_folder)

    file_path_yaml = os.path.join(test_folder, f'{counter}_{test_name}_{serial}.yml')
    file_path_csv = os.path.join(test_folder, f'{counter}_{test_name}_{serial}.csv')

    with open(file_path_yaml, "w", encoding="UTF-8") as archivo:
        yaml.dump_all(data, archivo, allow_unicode=True, default_flow_style=False, sort_keys=False)
    if av_data[1]:
        #if av_data[0]:
        av_data[0].to_csv(file_path_csv, index=True, sep=';', header=True, columns=['verification', 'data'])
        #else:
        #    logger.warning(f"all_answered export was set to True but no data could be retrieved.")

    print(f"Conversation saved in {path}")
    print('------------------------------')
    errors.clear()


class ExecutionStats:
    def __init__(self, test_cases_folder, serial):

        self.path = test_cases_folder
        self.test_names = []
        self.serial = serial
        self.export = False
        self.profile_art = []
        self.profile_edf = []
        self.global_time_stats = []
        self.global_error_stats = None

    def add_test_name(self, test_name):
        if isinstance(test_name, str):
            self.test_names.append(test_name)
        elif isinstance(test_name, list):
            self.test_names += test_name

    def reset(self):
        self.test_names = []
        self.export = False

    def get_stats(self):

        path_folder = self.path + f"/{self.test_names[-1]}" + f"/{self.serial}" # todo: except for empty test_names list

        assistant_response_times = []
        error_df = pd.DataFrame(columns=["conversation", "error_code"])

        for file in os.listdir(path_folder):
            if file.endswith(('.yaml', '.yml')):
                file_path = os.path.join(path_folder, file)
                file_name = file
                with open(file_path, 'r', encoding='utf-8') as yaml_file:
                    try:
                        yaml_content = list(yaml.safe_load_all(yaml_file))
                        if "assistant response time" in yaml_content[1]:
                            assistant_response_times += yaml_content[1]['assistant response time']

                        if "errors" in yaml_content[0] and 'serial' in yaml_content[0]:
                            for error in yaml_content[0]['errors']:

                                error_df = pd.concat(
                                    [error_df, pd.DataFrame({'conversation': [file_name],
                                                             'error_code': list(error.keys())})],
                                    ignore_index=True
                                )
                    except yaml.YAMLError as e:
                        print(f'error while processing the file {yaml_file}: {e}')

        self.profile_art.append(assistant_response_times)
        self.profile_edf.append(error_df)

    def show_last_stats(self):

        self.get_stats()

        time_stats = get_time_stats(self.profile_art[-1])
        print(f"Average assistant response time: {time_stats['average']} (s)")
        print(f"Maximum assistant response time: {time_stats['max']} (s)")
        print(f"Mínimum assistant response time: {time_stats['min']} (s)")

        error_stats = get_error_stats(self.profile_edf[-1])
        for error in error_stats:
            print(f"Found error {error['error']}: \n "
                  f"- Count: {error['count']} \n "
                  f"- Conversations: {error['conversations']}")

        print('------------------------------\n'
              '------------------------------')

    def show_global_stats(self):

        self.global_time_stats = [time for profile in self.profile_art for time in profile]
        self.global_error_stats = pd.concat(self.profile_edf, ignore_index=True)

        time_stats = get_time_stats(self.global_time_stats)
        print(f"Average assistant response time: {time_stats['average']} (s)")
        print(f"Maximum assistant response time: {time_stats['max']} (s)")
        print(f"Mínimum assistant response time: {time_stats['min']} (s)")

        error_stats = get_error_stats(self.global_error_stats)
        for error in error_stats:
            print(f"Found error {error['error']}: \n "
                  f"- Count: {error['count']} \n "
                  f"- Conversations: {error['conversations']}")

        print('------------------------------\n'
              '------------------------------')

    def export_stats(self):
        export_path = self.path + f"/__report__"

        if not os.path.exists(export_path):
            os.makedirs(export_path)

        single_reports = []
        for index, name in enumerate(self.test_names):
            time_stats = get_time_stats(self.profile_art[index])
            error_stats = get_error_stats(self.profile_edf[index])

            single_reports.append({
                "Test name": name,
                "Average assistant response time": time_stats['average'],
                "Maximum assistant response time": time_stats['max'],
                "Mínimum assistant response time": time_stats['min'],
                "Errors":  error_stats
            })

        glb_time_stats = get_time_stats(self.global_time_stats)
        glb_error_stats = get_error_stats(self.global_error_stats)

        global_reports = {
            "Global report": {
                "Average assistant response time": glb_time_stats['average'],
                "Maximum assistant response time": glb_time_stats['max'],
                "Mínimum assistant response time": glb_time_stats['min'],
                "Errors": glb_error_stats
            }
        }

        export_file_name = export_path + f"/report_{self.serial}.yml"
        data = [global_reports] + single_reports

        with open(export_file_name, "w", encoding="UTF-8") as archivo:
            yaml.dump_all(data, archivo, allow_unicode=True, default_flow_style=False, sort_keys=False)





def preprocess_text(text):
    # Convertir a minúsculas
    text = text.lower()
    # Eliminar signos de puntuación
    text = re.sub(r'[^\w\s]', '', text)
    return text


def str_to_bool(s):
    return {'true': True, 'false': False}[s.lower()]


def nlp_processor(msg, patterns=None, threshold=0.5):
    read_patterns = [patterns]

    prepro_patterns = [preprocess_text(pattern) for pattern in read_patterns]

    vectorizer = TfidfVectorizer().fit(prepro_patterns)

    processed_msg = preprocess_text(msg)

    # Vectorizar el mensaje y los patrones de fallback
    vectors = vectorizer.transform([processed_msg] + prepro_patterns)
    vector_msg = vectors[0]
    patt_msg = vectors[1:]

    # Calcular similitud de coseno
    similarities = cosine_similarity(vector_msg, patt_msg)
    max_sim = similarities.max()

    # Definir un umbral de similitud para detectar fallback

    return max_sim >= threshold


def build_sequence(pairs):
    mapping = {}
    starts = set()
    ends = set()
    for a, b in pairs:
        mapping[a] = b
        starts.add(a)
        if b is not None:
            ends.add(b)
    # Find starting words (appear in 'starts' but not in 'ends')
    start_words = starts - ends
    start_words.discard(None)
    sequences = []
    for start_word in start_words:
        sequence = [start_word]
        current_word = start_word
        while current_word in mapping and mapping[current_word] is not None:
            current_word = mapping[current_word]
            sequence.append(current_word)
        sequences.append(sequence)

    if not sequences:
        raise ValueError("Cannot determine a unique starting point.")
    return sequences


def get_random_date():
    year = random.randint(0, 3000)
    month = random.randint(1, 12)

    if month in [1, 3, 5, 7, 8, 10, 12]:
        day = random.randint(1, 31)
    elif month == 2:
        if year % 4 == 0:
            day = random.randint(1, 29)
        else:
            day = random.randint(1, 28)
    else:
        day = random.randint(1, 30)

    return f"{day}/{month}/{year}"


def get_date_range(start, end, step, date_type):
    if 'linspace' in date_type:
        total_seconds = (end - start).total_seconds()
        interval_seconds = total_seconds / (step - 1) if step > 1 else 0
        range_date_list = [(start + timedelta(seconds=interval_seconds * i)).strftime('%d/%m/%Y') for i in range(step)]

    elif date_type in ['day', 'month', 'year']:
        if 'month' in date_type:
            step = 30 * step
        elif 'year' in date_type:
            step = 365 * step

        range_date_list = [start.strftime('%d/%m/%Y')]
        while end > start:
            start = start + timedelta(days=step)
            range_date_list.append(start.strftime('%d/%m/%Y'))

    elif 'random' in date_type:
        delta = end - start
        random_dates = [
            (start + timedelta(days=random.randint(0, delta.days))).strftime('%d/%m/%Y') for _ in range(step)
        ]
        return random_dates

    else:
        raise InvalidFormat(f"The following parameter does not belong to date range field: {date_type}")

    return range_date_list

def get_fake_date():

    fake_day = random.randint(29, 99)
    fake_month = random.randint(13, 99)
    fake_year = random.randint(2000, 2099)

    return f"{fake_day}/{fake_month}/{fake_year}"


def get_date_list(date):
    custom_dates = []
    generated_dates = []
    if 'custom' in date:
        if isinstance(date['custom'], list):
            custom_dates = date['custom']
        else:
            custom_dates = [date['custom']]

    if 'random' in date:
        value = date['random']
        random_dates = []
        for i in range(value):
            str_date = get_random_date()
            random_dates.append(str_date)
        generated_dates += random_dates

    if 'set' in date:
        value = int(re.findall(r'today\((.*?)\)', date['set'])[0])

        if '>today' in date['set']:
            today = datetime.now()
            next_dates = [
                (today + timedelta(days=random.randint(1, 365))).strftime('%d/%m/%Y') for _ in range(value)
            ]
            generated_dates += next_dates

        elif '<today' in date['set']:
            today = datetime.now()
            previous_dates = [
                (today - timedelta(days=random.randint(1, 365))).strftime('%d/%m/%Y') for _ in range(value)
            ]
            generated_dates += previous_dates

    if 'range' in date:
        start = datetime.strptime(date['range']['min'], '%d/%m/%Y')
        end = datetime.strptime(date['range']['max'], '%d/%m/%Y')
        if 'step' in date['range']:
            step_value = int(re.findall(r'\((.*?)\)', date['range']['step'])[0])

            if 'linspace' in date['range']['step']:
                list_of_dates = get_date_range(start, end, step_value, 'linspace')
                generated_dates += list_of_dates

            elif 'day' in date['range']['step']:
                list_of_dates = get_date_range(start, end, step_value, 'day')
                generated_dates += list_of_dates

            elif 'month' in date['range']['step']:
                list_of_dates = get_date_range(start, end, step_value, 'month')
                generated_dates += list_of_dates

            elif 'year' in date['range']['step']:
                list_of_dates = get_date_range(start, end, step_value, 'year')
                generated_dates += list_of_dates
            else:
                raise InvalidFormat(f"The following parameter does not belong "
                                    f"to date range field: {date['range']['step']}")

        elif 'random' in date['range']:
            value = date['range']['random']
            list_of_dates = get_date_range(start, end, value, 'random')
            generated_dates += list_of_dates

    if 'fake' in date:
        num_dates = date["fake"]

        fake_date_list = []
        while len(fake_date_list) < num_dates:
            fake_date = get_fake_date()
            if fake_date not in fake_date_list:
                fake_date_list.append(get_fake_date())

        generated_dates += fake_date_list

    final_date_list = generated_dates + custom_dates
    return final_date_list


def get_any_items(any_list, item_list):
    response_format = {
        "type": "json_schema",
        "json_schema": {
            "name": "List_of_values",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "answer": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    }
                },
                "required": ["answer"],
                "additionalProperties": False
            }
        }
    }
    output_list = item_list.copy()

    for data in any_list:
        content = re.findall(r'any\((.*?)\)', data)
        message = [{"role": "system",
                    "content": "You are a helpful assistant that creates a list of whatever the user asks."},
                   {"role": "user",
                    "content": f"A list of any of these: {content}. Avoid putting any of these: {output_list}"}]

        response = client.chat.completions.create(
            model="gpt-4o-2024-08-06",
            messages=message,
            response_format=response_format
        )

        raw_data = json.loads(response.choices[0].message.content)
        output_data = raw_data["answer"]

        output_list += output_data

    return output_list
