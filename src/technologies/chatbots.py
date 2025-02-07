import yaml

from typing import List, Dict

# -------------------------------------------------------------------------------------------------
# AUXILIARY CLASSES
# -------------------------------------------------------------------------------------------------


class Dumper(yaml.Dumper):
    def increase_indent(self, flow=False, *args1, **kwargs1):
        return super().increase_indent(flow=flow, indentless=False)


class ConversationConfiguration:
    def __init__(self,
                 number_conversations: int = 1,
                 steps_in_conversation: int = 1,
                 interaction_style: List[str] = [],
                 change_language: List[str] = []
                 ):
        self.number = number_conversations
        self.steps = steps_in_conversation
        self.interaction_style = interaction_style
        self.change_language = change_language

    def to_dict(self):
        interaction_to_dict: List[str | Dict] = [style for style in self.interaction_style]
        if len(self.change_language):
            interaction_to_dict.append({"change language": self.change_language})
        return [
            {"number": self.number},
            {"goal_style": {"steps": self.steps}},
            {"interaction_style": interaction_to_dict}
        ]


class RoleData:
    def __init__(self,
                 temperature: float = 0.8,
                 isstarter: bool = True,
                 fallback: str = '',
                 role: str = '',
                 context: List[str] = None,
                 ask_about: List[str | Dict] = [],
                 conversations: ConversationConfiguration = ConversationConfiguration(),
                 language: str = 'English',
                 test_name: str = ''
                 ):
        self.temperature = temperature
        self.isstarter = isstarter
        self.fallback = fallback
        self.role = role
        self.context = context
        self.ask_about = ask_about
        self.conversations = conversations
        self.language = language
        self.test_name = test_name

    def to_dict(self) -> dict:
        ret = self.__dict__
        ret['conversations'] = self.conversations.to_dict()
        return ret

    def to_yaml(self, file):
        with open(file, 'w') as outfile:
            yaml.dump(self.to_dict(), outfile, default_flow_style=False, sort_keys=False, Dumper=Dumper)

# -------------------------------------------------------------------------------------------------
# BASE CLASSES
# -------------------------------------------------------------------------------------------------


class ChatbotSpecification:
    def build_user_profile(self, chatbot_folder) -> RoleData:
        """
        :param chatbot_folder: folder containing the chatbot modules
        :returns user profile built from the chatbot specification
        """
        raise TypeError(f"Can't invoke abstract method build_user_profile in class {__class__.__name__}")
