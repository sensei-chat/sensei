
import ast
import pandas as pd

import re
from .utils.exceptions import *

import json

from openai import OpenAI
client = OpenAI()

import logging
logger = logging.getLogger('Info Logger')


def extract_dict(in_val):
    reg_ex = r'\{[^{}]*\}'
    coincidence = re.search(reg_ex, in_val, re.DOTALL)

    if coincidence:
        return coincidence.group(0)
    else:
        return None


def to_dict(in_val):
    try:
        dictionary = ast.literal_eval(extract_dict(in_val))
    except (BadDictionaryGeneration, ValueError) as e:
        logger.error(f"Bad dictionary generation: {e}. Setting empty dictionary value.")
        dictionary = {}
    return dictionary


class ChatbotAssistant:
    def __init__(self, ask_about):

        self.properties = self.process_ask_about(ask_about)
        self.system_message = {"role": "system",
                               "content": "You are a helpful assistant that detects when a query in a conversation "
                                          "has been answered or confirmed by the chatbot."}
        self.messages = [self.system_message]
        self.gathering_register = []


    @staticmethod
    def process_ask_about(ask_about):
        properties = {
        }
        for ab in ask_about:
            properties[ab.replace(' ', '_')] = {
                "type": "object",
                "properties": {
                    "verification": {
                        "type": "boolean",
                        "description": f"the following has been answered or confirmed by the chatbot: {ab}"
                    },
                    "data": {
                        "type": ["string", "null"],
                        "description": f"the piece of the conversation where the following has been answered "
                                       f"or confirmed by the assistant. Don't consider the user's interactions: {ab} "
                    }
                },
                "required": ["verification", "data"],
                "additionalProperties": False
            }
        return properties

    def add_message(self, history):     # adds directly the chat history from user_simulator "self.conversation_history"
        text = ""
        for entry in history['interaction']:
            for speaker, message in entry.items():
                text += f"{speaker}: {message}\n"

        user_message = {"role": "user",
                        "content": text}

        self.messages = [self.system_message] + [user_message]
        self.gathering_register = self.create_dataframe()

    def get_json(self):
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=self.messages,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "ask_about_validation",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": self.properties,
                        "required": list(self.properties.keys()),
                        "additionalProperties": False
                    }
                }
            }
        )
        data = json.loads(response.choices[0].message.content)
        return data

    def create_dataframe(self):
        data_dict = self.get_json()
        df = pd.DataFrame.from_dict(data_dict, orient='index')
        return df

