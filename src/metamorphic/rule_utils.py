import ast
import os
import re
from types import SimpleNamespace

import inflect
from openai import OpenAI

from metamorphic import get_filtered_tests
from metamorphic.text_comparison_utils import exact_similarity, tf_idf_cosine_similarity, jaccard_similarity, \
    sequence_similarity

filtered_tests = []
interaction = []

def util_functions_to_dict() -> dict:
    """
    :return: a dict with all functions defined in this module
    """
    return {'extract_float': extract_float,
            'currency': currency,
            'language': language,
            'length': length,
            'tone': tone,
            '_only_talks_about': _only_talks_about,
            'is_unique': is_unique,
            'exists': exists,
            'num_exist': num_exist,
            '_data_collected': _data_collected,
            '_utterance_index': _utterance_index,
            '_conversation_length': _conversation_length,
            '_chatbot_returns': _chatbot_returns,
            '_repeated_answers': _repeated_answers,
            '_missing_slots': _missing_slots,
            '_responds_in_same_language': _responds_in_same_language,
            'semantic_content': semantic_content}

def util_to_wrapper_dict() -> dict:
    return {'_conversation_length':
            "    def conversation_length(who = 'both'):\n        return _conversation_length(interaction, who)\n",
            '_only_talks_about':
            "    def only_talks_about(topics, fallback=None):\n       return _only_talks_about(topics, interaction, fallback)\n",
            '_utterance_index':
            "    def utterance_index(who, what):\n        return _utterance_index(who, what, interaction)\n",
            '_chatbot_returns':
            "    def chatbot_returns(what, and_not=None):\n        return _chatbot_returns(what, and_not, interaction)\n",
            '_repeated_answers':
                "    def repeated_answers(method = 'exact', threshold = 0.4):\n        return _repeated_answers(interaction, method, threshold)\n",
            '_data_collected':
                "    def data_collected():\n        return _data_collected(conv)\n",
            '_missing_slots':
                "    def missing_slots():\n        return _missing_slots(conv)\n",
            '_responds_in_same_language':
                "    def responds_in_same_language():\n        return _responds_in_same_language(interaction)\n",
            }

def semantic_content(variable, content) -> bool:
    """
    checks if variable contents semantically the content
    :param variable:
    :param content:
    :return:
    """
    prompt = f"""Your task it to detect if the text below has the following semantic content: {content}.
            TEXT: {variable} 
            Return only YES or NO"""
    response = call_openai(prompt)
    if response.lower() == 'yes':
        return True
    else:
        return False

def _repeated_answers(interaction, method = 'exact', threshold = 0.4):
    """
    :param interaction: a list with the user-chatbot interactions
    :return: a dictionary of repeated phrases by the chatbot (keys=phrase, value=list of step numbers)
    """
    comparator = build_comparator(method)
    repeated_phrases = dict()
    step_index = 0
    for step in interaction:
        for key, value in step.items():
            if key.lower() in ['chatbot', 'assistant']:
                similar = find_similar(comparator, value, repeated_phrases, threshold)
                if similar is not None:
                    repeated_phrases[similar].append(value)
                else:
                    repeated_phrases[value] = []
        step_index += 1
    for key in list(repeated_phrases.keys()):  # remove phrases that occur only 1
        if len(repeated_phrases[key])<1:
            del repeated_phrases[key]

    #print(f" REPEATED PHRASES {repeated_phrases}")
    return repeated_phrases

def find_similar(comparator, phrase, phrases, threshold):
    for key in phrases:
        similarity = comparator(phrase, key)
        if similarity >= threshold:
            return key
    return None

def build_comparator(method):
    if method.lower() == 'tf-idf':
        return tf_idf_cosine_similarity
    elif method.lower() == 'jaccard':
        return jaccard_similarity
    elif method.lower() == 'sequence-matcher':
        return sequence_similarity
    else:
        return exact_similarity

def _chatbot_returns(what, and_not=None, interaction=None):
    """
    :param what: pattern
    :param and_not: additional pattern that must not be found after what
    :param interaction: list of user-chatbot interactions
    :return: a list with the interactions in which the assistant returns a message that contains the pattern
    To-Do: we could add additional parameters, like and_then, etc
    """

    def contains_first_and_not_second(string, X, Y):
        pos_X = string.find(X)

        if pos_X != -1:
            pos_Y = string.find(Y, pos_X + len(X))
            if pos_Y == -1:
                return True

        return False

    interactions = []
    step_index = 0
    for step in interaction:  # step is a dict
        for key, value in step.items():
            if key.lower() in ['chatbot', 'assistant']:
                if what in value:
                    if and_not is None:
                        interactions.append(step_index)
                    elif contains_first_and_not_second(value, what, and_not):
                        interactions.append(step_index)
        step_index += 1
    return interactions

def _conversation_length(interaction, who = 'both'):
    who = who.lower()
    if who not in ['user', 'chatbot', 'assistant', 'both']:
        raise ValueError(f"Expected 'user', 'chatbot' or 'both', but got '{who}'")
    if who.lower() == 'both':
        return len(interaction)
    else:
        number = 0
        for step in interaction: # step is a dict
            for key, value in step.items():
                if key.lower() == who:
                    number += 1
        return number

def _data_collected(conv):
    outputs = conv[0].data_output
    for data in outputs:
        for key, value in data.items():
            if value is None or value == 'None':
                return False
    return True


def _missing_slots(conv):
    missing = []
    outputs = conv[0].data_output
    for data in outputs:
        for key, value in data.items():
            if value is None or value == 'None':
                missing.append(key)
    return missing

def interaction_to_str(interaction, numbered=False):
    result = ''
    index = 1
    for step in interaction: # step is a dict
        for key, value in step.items():
            if numbered:
                result+=f"{index} - "
                index += 1
            result+=f"{key} : {value}\n"
    return result


def _utterance_index(who, what, conversation) -> int:
    """
    :param who: 'user', 'assistant', 'chatbot'
    :param what: what is to be checked
    :return: the conversation turn where it happened
    """
    numbered_conversation = interaction_to_str(conversation, True)
    prompt = f"""The following is a conversation between a user and an assistant chatbot. 
        Your task it to detect the conversation turn where the {who} talked about {what}". 
        Return only the conversation turn number, and nothing else, just the number.\n\n {numbered_conversation}"""
    response = call_openai(prompt)
    if response.isnumeric():
        return int(response)
    else:
        return -1

def _only_talks_about(topics, conversation, fallback = None) -> bool:
    """
     checks if the chatbot only talks about certain topics
     """
    if isinstance(topics, str):
        topics = [topics]
    if not isinstance(topics, list):
        raise ValueError(f"Expecting a list of strings, or a string, but got {topics}")

    if not isinstance(conversation, list):
        raise ValueError(f"Expecting a list with the chatbot-user interaction, but got {conversation}")

    if fallback is not None:
        fallback_phrase = f', using phrases like "{fallback}"'
    else:
        fallback_phrase = ''

    talk_topics = ','.join(topics)
    phrases = interaction_to_str(conversation)
    prompt = f"""The following is a conversation between a user and an assistant chatbot:\n\n
    {phrases}
    ----
    Your task it to detect if the assistant deviates from the following topics "{talk_topics}".
    The assistant is not allowed to follow the conversation of the user, if the user tries to talk on topics different
    from the previous ones. In that case, the chatbot should redirect the conversation to the previous topics.
    The assistant is allowed to ask for clarifications or to express that it does not understand the user{fallback_phrase}. 
    Return the following:
     - ONLY 'True' if the chatbot sticks to "{talk_topics}", even if the user tries to talk about another topic.   
     - ONLY the list of assistant answers that deviate from the previous topics."""
    response = call_openai_o1(prompt)
    if response.lower() == "true":
        return True
    else:
        #error_phrases = ast.literal_eval(response)
        return f"The following chatbot responses are out of scope: {response}"
        #raise TestError(error_phrases, f"The following chatbot responses are out of scope: {error_phrases}")

def num_exist(condition: str) -> int:
    num = 0
    for test in get_filtered_tests():
        test_dict = test.to_dict()
        conv = [SimpleNamespace(**test_dict)]
        test_dict['conv'] = conv
        test_dict.update(util_functions_to_dict())
        if eval(condition, test_dict):
            num += 1
    return num

def exists(condition: str) -> bool:
    for test in get_filtered_tests():
        test_dict = test.to_dict()
        conv = [SimpleNamespace(**test_dict)]
        test_dict['conv'] = conv
        test_dict.update(util_functions_to_dict())
        if eval(condition, test_dict):
            # print(f"   Satisfied on {test.file_name}")
            return True
    return False


def is_unique(property: str) -> bool:
    values = dict() # a dictionary of property values to test file name
    for test in get_filtered_tests():
        var_dict = test.to_dict()
        if property not in var_dict:
            continue
        if var_dict[property] in values:
            print(f"   Tests: {test.file_name} and {values[var_dict[property]]} have value {var_dict[property]} for {property}.")
            return False
        elif var_dict[property] is not None:
            values[var_dict[property]] = test.file_name
    return True

def extract_float(string: str) -> float:
    """
    Function that returns the first float number inside the string
    :param string: the string the float number is to be extracted
    :return: the first float number inside the string
    """
    # remove , as marker of thousands
    pattern = r'(?<=\d),(?=\d)'
    cleaned_text = re.sub(pattern, '', string)
    pattern = r'[-+]?\d*\.\d+|\d+'  # A regular expression pattern for a float number
    match = re.search(pattern, cleaned_text)

    if match:
        return float(match.group())
    else:
        return None


def currency(string: str) -> str:
    """
    Extracts the first currency within the string, either as symbol (e.g. €), abbreviation (e.g. 'EUR') or full name
    ('euro')
    :param string:
    :return:
    """
    for extractor in [currency_symbol, currency_abbreviation, currency_name]:
        curr = extractor(string)
        if curr is not None:
            return curr
    return None


def currency_symbol(string: str) -> str:
    pattern = r'[$€£¥₹]'
    map_currency = {'$': 'USD', '€': 'EUR', '£': 'GBP', '¥': 'JPY', '₹': 'INR'}
    match = re.search(pattern, string)

    if match:
        return map_currency[match.group()]
    else:
        return None


def currency_abbreviation(string: str) -> str:
    pattern = r'\b(USD|EUR|GBP|JPY|INR)\b'
    match = re.search(pattern, string)

    if match:
        return match.group()
    else:
        return None


def currency_name(string: str):
    pattern = r'\b(dollars|euros|pounds|yen|rupees)\b'
    map_currency = {'dollars': 'USD', 'euros': 'EUR', 'pounds': 'GBP', 'yen': 'JPY', 'rupees': 'INR'}
    match = re.search(pattern, string, re.IGNORECASE)

    if match:
        return map_currency[match.group()]
    else:
        return None


def length(item, kind='min'):
    """
    :param item: a string or a list of strings
    :param kind: which length to provide. Accepted values are min, max or average
    :return: the desired length
    """
    if isinstance(item, str):
        item = [item]
    if not isinstance(item, list):
        raise ValueError(f"Expecting a list of strings, or a string, but got {item}")
    kind = kind.lower()
    if kind not in ['min', 'max', 'average']:
        raise ValueError(f"Expecting one of min, max or average, but got {kind}")

    inits = {
        'min': 100000000,
        'max': 0,
        'average': 0
    }
    current = inits[kind]
    operations = {
        'min': lambda x, n: x if x < current else current,
        'max': lambda x, n: x if x > current else current,
        'average': lambda x, n: (current + x) / n
    }
    iteration = 1
    for element in item:
        current = operations[kind](len(element), iteration)
        iteration += 1
    return current


def language(string):
    """
    returns the language of the given string, or list of strings
    :param string: a list of strings or a string
    :return: One of the codes of the languages dictionary
    """
    languages = {'ENG': 'English',
                 'ESP': 'Spanish',
                 'FR': 'French',
                 'GER': 'German',
                 'IT': 'Italian',
                 'POR': 'Portuguese',
                 'CHI': 'Chinese',
                 'JAP': 'Japanese',
                 'OTHER': 'other language'}

    p = inflect.engine()
    lang_list = [f"{k} for {v}" for k, v in languages.items()]
    prompt = f"""What is the language of the following text?: \n {string}. \n Return {p.join(tuple(lang_list))}."""
    response = call_openai(prompt)
    return response


def tone(item):
    """
    returns the tone ('POSITIVE', 'NEGATIVE', 'NEUTRAL') of each text in the parameter
    :param string: the text
    :return: a list with 'POSITIVE', 'NEGATIVE', 'NEUTRAL' for each text in item
    """
    if isinstance(item, str):
        item = [item]
    if not isinstance(item, list):
        raise ValueError(f"Expecting a list of strings, or a string, but got {item}")

    responses = []
    for element in item:
        prompt = f"""What is the tone of the following text: \n {element}. \n Return only POSTIVE, NEGATIVE or NEUTRAL."""
        response = call_openai(prompt)
        responses.append(response)
    return responses


def call_openai(message: str, llm="gpt-4o", temp = 0, stream_mode = True):
    """
    Send a message to OpenAI and returns the answer.
    :param str message: The message to send
    :return The answer to the message
    """
    client = OpenAI()
    stream = client.chat.completions.create(
        # model="gpt-3.5-turbo",
        model=llm,
        messages=[{"role": "user", "content": message}],
        temperature=temp,
        stream=stream_mode)
    chunks = ''
    for chunk in stream:
        for choice in chunk.choices:
            if choice.delta.content is not None:
                chunks += choice.delta.content
    return chunks

def call_openai_o1(message: str):
    """
    Send a message to OpenAI o1 and returns the answer.
    :param str message: The message to send
    :return The answer to the message
    """
    client = OpenAI()
    response = client.chat.completions.create(
        # model="gpt-3.5-turbo",
        model="o1-mini",
        messages=[{"role": "user", "content": message}])
    chunks = ''
    for choice in response.choices:
        chunks += choice.message.content
    return chunks

def _responds_in_same_language(interaction):
    """
    returns if the chatbot responds in the same language as the user
    :param interaction: a list with the interaction
    :return: the turn in which the assistant responds in a different language
    """
    def filter_errors(interaction):
        for step in interaction[:]:  # step is a dict, we iterate over copu
            for key, value in step.items():
                if key.lower() in ['chatbot', 'assistant']:
                    if value.startswith('Error: The server'):
                        interaction.remove(step)
        return interaction

    # filter the errrors of the chatbot, which always are shown as English text
    filtered_interaction = filter_errors(interaction)
    if len(filtered_interaction) == 1: # nothing to do
        return True
    prompt = f"""You are an assistant that checks conversations between a chatbot and a human.
                 Your task is to assess if the chatbot always responds in the same language as the
                 human. For example, if the human speaks in Spanish, the chatbot should respond in Spanish, too.
                 Given the conversation below, return:
                 - YES if the chatbot responds in the same language.
                 - NO if the chatbot sometimes responds in a different language.
                 CONVERSATION:
                 {filtered_interaction}"""
    response = call_openai(prompt)
    if response.lower() == 'yes':
        return True
    return False