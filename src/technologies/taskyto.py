import glob
import inflect
import os
import yaml

from .chatbots import RoleData, ChatbotSpecification
from typing import List, Dict


class ChatbotSpecificationTaskyto (ChatbotSpecification):
    def build_user_profile(self, chatbot_folder) -> RoleData:
        """
        :param chatbot_folder: folder containing the chatbot modules
        :returns user profile built from the chatbot specification
        """
        formatter = inflect.engine()
        profile = RoleData()
        profile.role = 'You have to act as a user of a chatbot.'
        profile.context = [
                 "Never indicate that you are the user, like 'user: bla bla'.", #todo: these prompts should be removed since they are added internaly in the code. A.
                 "Sometimes, interact with what the assistant just said.",
                 "Never act as the assistant.",
                 "Don't end the conversation until you've asked everything you need."
             ]
        # profile.conversations.interaction_style.append('long phrase')
        profile.conversations.interaction_style.append('change your mind')
        profile.conversations.interaction_style.append('make spelling mistakes')
        profile.conversations.interaction_style.append('single question')
        profile.conversations.interaction_style.append('all questions')
        # profile.conversations.interaction_style.append('default')

        # chatbot modules
        modules = self.__class__.__load_chatbot_modules(chatbot_folder)
        for module in modules:
            if module.get("modules"):
                modules.extend(module.get("modules"))
                continue
            # menu module ...........................................
            kind = module.get("kind")
            if kind == "menu":
                if module.get("items"):
                    modules.extend(module.get("items"))
                if not profile.fallback:
                    profile.fallback = module.get("fallback")
                if module.get("presentation"):
                    profile.role += f' This chatbot is described as follows: \"{module.get("presentation").strip()}\"'
            # data gathering module .................................
            elif kind == "data_gathering":
                for data in module.get("data"):
                    for item in data.keys():
                        item_values = data.get(item)
                        if item_values.get("type") == "enum":
                            if formatter.singular_noun(item) is True:
                                item = formatter.plural(item)
                            ask_about = 'Consider the following ' + item + ': {{' + item + '}}.'
                            ask_values = self.__class__.__flatten(item_values.get("values"))
                            profile.ask_about.append(ask_about)
                            profile.ask_about.append({item: ask_values})
            # answer module .........................................
            elif kind == "answer":
                profile.ask_about.append(module.get("title"))

        # chatbot configuration
        config = self.__class__.__load_configuration_file(chatbot_folder)
        if config.get("languages"):
            languages = [language.strip() for language in config.get("languages").split(",")]
            profile.conversations.change_language.extend(languages)
            profile.language = languages[0]

        return profile

    @staticmethod
    def __flatten(list_values: List[str | Dict[str, List[str]]]) -> List[str]:
        """
        :param list_values: list of values, which can be strings or dictionaries
        :returns list of string values (dicts are flattened -- their keys and values are added to the list)
        """
        list_flattened = []
        for value in list_values:
            if isinstance(value, Dict):
                for key in value.keys():
                    list_flattened.append(key)
                    list_flattened.extend(value.get(key))
            else:
                list_flattened.append(value)
        return list_flattened

    @staticmethod
    def __load_chatbot_modules(chatbot_folder) -> List[Dict]:
        """
        :param chatbot_folder: folder containing the chatbot modules
        :returns yaml files in chatbot_folder
        """
        modules = []
        for file_path in glob.glob(os.path.join(chatbot_folder, '*.yaml')):
            with open(file_path) as yaml_file:
                modules.append(yaml.safe_load(yaml_file.read()))
        return modules

    @staticmethod
    def __load_configuration_file(chatbot_folder) -> Dict:
        """
        :param chatbot_folder: folder containing the chatbot modules
        :returns file chatbot_folder/configuration/default.yaml
        """
        configuration_file = os.path.join(chatbot_folder, "configuration", "default.yaml")
        if os.path.isfile(configuration_file):
            with open(configuration_file) as yaml_file:
                return yaml.safe_load(yaml_file.read())
        return {}
