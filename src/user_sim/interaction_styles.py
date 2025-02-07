import random
import logging
logger = logging.getLogger('Info Logger')


def find_instance(instances, i_class):
    for instance in instances:
        if isinstance(instance, i_class):
            return instance
    return None


def create_instance(class_list, interaction_styles):
    instances = []
    for class_info in class_list:
        class_name = class_info['clase']
        args = class_info.get('args', [])
        kwargs = class_info.get('kwargs', {})
        if class_name in interaction_styles:
            instance = interaction_styles[class_name](*args, **kwargs)
            instances.append(instance)
        else:
            raise ValueError(f"Couldn't find {class_name} in interaction list.")
    return instances


class InteractionStyle:

    def __init__(self, inter_type):
        self.inter_type = inter_type
        self.change_language_flag = False
        self.languages_options = []

    def get_prompt(self):
        return

    def get_metadata(self):
        return


class LongPhrases(InteractionStyle):
    def __init__(self):
        super().__init__(inter_type='long phrases')

    def get_prompt(self):
        return "use very long phrases to write anything. "

    def get_metadata(self):
        return self.inter_type


class ChangeYourMind(InteractionStyle):
    def __init__(self):
        super().__init__(inter_type='change your mind')

    def get_prompt(self):
        return "eventually, change your mind about any information you provided. "

    def get_metadata(self):
        return self.inter_type


class ChangeLanguage(InteractionStyle):
    # TODO: add chance variable with *args
    def __init__(self, default_language):
        super().__init__(inter_type='change language')
        self.default_language = default_language
        self.languages_list = []

    def get_prompt(self):

        lang = self.language()
        prompt = f"""Please, always talk in {lang}, even If the assistant tells you that he doesn't understand, 
                or you had a conversation in another language before. """
        return prompt

    def language(self, chance=30):

        rand_number = random.randint(1, 100)
        if rand_number <= chance:
            lang = random.choice(self.languages_options)
            # logging.getLogger().verbose(f'the language is: {lang}')
            logger.info(f'Language was set to {lang}')
            self.languages_list.append(lang)
            return lang
        else:
            self.languages_list.append(self.default_language)
            logger.info(f'Language was set to default ({self.default_language})')
            return self.default_language

    def reset_language_list(self):
        self.languages_list.clear()

    def get_metadata(self):
        language_list = self.languages_list.copy()
        self.reset_language_list()
        return {'change languages': language_list}


class MakeSpellingMistakes(InteractionStyle):
    def __init__(self):
        super().__init__(inter_type='make spelling mistakes')

    def get_prompt(self):
        prompt = """
                 please, make several spelling mistakes during the conversation. Minimum 5 typos per 
                 sentence if possible. 
                 """
        return prompt

    def get_metadata(self):
        return self.inter_type


class SingleQuestions(InteractionStyle):
    def __init__(self):
        super().__init__(inter_type='single questions')

    def get_prompt(self):
        return "ask only one question per interaction. "

    def get_metadata(self):
        return self.inter_type


class AllQuestions(InteractionStyle):
    # todo: all questions should only get questions from ask_about
    def __init__(self):
        super().__init__(inter_type='all questions')

    def get_prompt(self):
        return "ask everything you have to ask in one sentence. "

    def get_metadata(self):
        return self.inter_type


class Default(InteractionStyle):
    def __init__(self):
        super().__init__(inter_type='default')

    def get_prompt(self):
        return "Ask about one or two things per interaction, don't ask everything you want to know in one sentence."

    def get_metadata(self):
        return self.inter_type
