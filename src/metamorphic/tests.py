from pydantic import BaseModel, Field
from typing import List, Optional


class Test(BaseModel):
    ask_about: list
    conversation: list
    data_output: Optional[list] = []
    interaction: Optional[list] = []
    language: Optional[str] = None
    serial: str
    file_name: Optional[str] = None
    conversation_time: Optional[str] = None
    errors: Optional[list] = []
    assistant_times: Optional[list] = []

    @staticmethod
    def build_test(file, documents):
        test_metadata = next(documents)  # unpack the 1st YAML document: meta_data
        test = Test(**test_metadata)
        test.file_name = file
        times_doc = next(documents)
        test.conversation_time = times_doc['conversation time']    # 2nd YAML document is time
        if 'assistant response time' in times_doc:
            test.assistant_times = times_doc['assistant response time']
        test.interaction = next(documents)['interaction']         # 3rd YAML document is the conversation
        return test

    def to_dict(self):
        variable_dict = self.__get_ask_about_dict()
        variable_dict.update(self.__get_parameters_dict(self.conversation, 'conversation'))
        variable_dict.update(self.__get_parameters_dict(self.data_output, 'data_output'))
        variable_dict.update(self.__get_interactions_dict(self.interaction))
        variable_dict.update({'data_output': self.data_output})
        #print(f"Dict = {variable_dict}")
        return variable_dict


    def __get_interactions_dict(self, interactions_dict):
        """
        return a dictionary with, the interactions, the chatbot_phrases and the user_phrases
        :param interactions_dict:
        :return:
        """
        clean_dict = dict()
        clean_dict.update({'interaction': interactions_dict})
        chatbot_phrases = []
        for phrase in interactions_dict:
            if 'Assistant' in phrase:
                chatbot_phrases.append(phrase['Assistant'])
        clean_dict.update({'chatbot_phrases': chatbot_phrases})
        user_phrases = []
        for phrase in interactions_dict:
            if 'User' in phrase:
                user_phrases.append(phrase['User'])
        clean_dict.update({'user_phrases': user_phrases})
        return clean_dict


    def __get_ask_about_dict(self):
        clean_dict = dict()
        for item in self.ask_about:
            if isinstance(item, dict):
                for key in item:
                    clean_dict[key] = item[key]
        return clean_dict

    def __get_parameters_dict(self, attribute, name):
        clean_dict = dict()
        for item in attribute:
            if isinstance(item, dict):
                clean_dict.update(self.__flatten_dict(name, item))
        return clean_dict

    def __flatten_dict(self, name, map):
        flatten_dict = dict()
        for key in map:
            if not isinstance(map[key], dict):
                flatten_dict[name + '_' + key] = map[key]
                flatten_dict[key] = map[key]
            else:
                flatten_dict.update(self.__flatten_dict(name + '_' + key, map[key]))
        return flatten_dict
