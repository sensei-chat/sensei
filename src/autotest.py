import time
import timeit
from argparse import ArgumentParser
from user_sim.utils.config import errors
import pandas as pd
import yaml
from colorama import Fore, Style
from technologies.chatbot_connectors import (Chatbot, ChatbotRasa, ChatbotTaskyto, ChatbotAdaUam, ChatbotMillionBot,
                                             ChatbotLolaUMU, ChatbotServiceform, KukiChatbot, JulieChatbot, ChatbotCatalinaRivas, ChatbotSaicMalaga, \
    ChatbotGenion)
from user_sim.data_extraction import DataExtraction
from user_sim.role_structure import *
from user_sim.user_simulator import UserGeneration
from user_sim.utils.show_logs import *
from user_sim.utils.utilities import *


def print_user(msg): print(f"{Fore.GREEN}User:{Style.RESET_ALL} {msg}")


def print_chatbot(msg): print(f"{Fore.LIGHTRED_EX}Chatbot:{Style.RESET_ALL} {msg}")


def get_conversation_metadata(user_profile, the_user, serial=None):
    def conversation_metadata(up):
        interaction_style_list = []
        conversation_list = []

        for inter in up.interaction_styles:
            interaction_style_list.append(inter.get_metadata())

        # for conv in user_profile.yaml['conversation']:
        #     keys = list(conv.keys())
        #     if keys[0] == 'interaction_style':
        #         conversation_list.append({'interaction_style': interaction_style_list})
        #
        #     elif keys[0] == 'goal_style':
        #         if 'random steps' in conv[keys[0]]:
        #             conversation_list.append({keys[0]: {'steps': user_profile.goal_style[1]}})
        #         else:
        #             conversation_list.append(conv)
        #
        #     else:
        #         conversation_list.append(conv)

        conversation_list.append({'interaction_style': interaction_style_list})

        if isinstance(up.yaml['conversation']['number'], int):
            conversation_list.append({'number': up.yaml['conversation']['number']})
        else:
            conversation_list.append({'number': up.conversation_number})

        if 'random steps' in up.yaml['conversation']['goal_style']:
            conversation_list.append({'goal_style': {'steps': up.goal_style[1]}})
        else:
            conversation_list.append(up.yaml['conversation']['goal_style'])

        return conversation_list

    def ask_about_metadata(up):
        if not up.ask_about.variable_list:
            return up.ask_about.str_list

        return user_profile.ask_about.str_list + user_profile.ask_about.picked_elements

    def data_output_extraction(u_profile, user):
        output_list = u_profile.output
        data_list = []
        for output in output_list:
            var_name = list(output.keys())[0]
            var_dict = output.get(var_name)
            my_data_extract = DataExtraction(user.conversation_history,
                                             var_name,
                                             var_dict["type"],
                                             var_dict["description"])
            data_list.append(my_data_extract.get_data_extraction())

        data_dict = {k: v for dic in data_list for k, v in dic.items()}
        has_none = any(value is None for value in data_dict.values())
        if has_none:
            count_none = sum(1 for value in data_dict.values() if value is None)
            errors.append({1001: f"{count_none} goals left to complete."})

        return data_list

    data_output = {'data_output': data_output_extraction(user_profile, the_user)}
    context = {'context': user_profile.raw_context}
    ask_about = {'ask_about': ask_about_metadata(user_profile)}
    conversation = {'conversation': conversation_metadata(user_profile)}
    language = {'language': user_profile.language}
    serial_dict = {'serial': serial}
    errors_dict = {'errors': errors}
    metadata = {**serial_dict,
                **language,
                **context,
                **ask_about,
                **conversation,
                **data_output,
                **errors_dict
                }

    return metadata


def parse_profiles(user_path):
    def is_yaml(file):
        if not file.endswith(('.yaml', '.yml')):
            return False
        try:
            with open(file, 'r') as f:
                yaml.safe_load(f)
            return True
        except yaml.YAMLError:
            return False

    list_of_files = []
    if os.path.isfile(user_path):
        if is_yaml(user_path):
            yaml_file = read_yaml(user_path)
            return [yaml_file]
        else:
            raise Exception(f'The user profile file is not a yaml: {user_path}')
    elif os.path.isdir(user_path):
        for root, _, files in os.walk(user_path):
            for file in files:
                if is_yaml(os.path.join(root, file)):
                    path = root + '/' + file
                    yaml_file = read_yaml(path)
                    list_of_files.append(yaml_file)

            return list_of_files
    else:
        raise Exception(f'Invalid path for user profile operation: {user_path}')


def build_chatbot(technology, chatbot) -> Chatbot:
    default = Chatbot
    chatbot_builder = {
        'rasa': ChatbotRasa,
        'taskyto': ChatbotTaskyto,
        'ada-uam': ChatbotAdaUam,
        'millionbot': ChatbotMillionBot,
        'lola': ChatbotLolaUMU,
        'rivas_catalina': ChatbotCatalinaRivas,
        'saic_malaga': ChatbotSaicMalaga,
        'serviceform': ChatbotServiceform,
        'kuki': KukiChatbot,
        'julie': JulieChatbot,
        'genion': ChatbotGenion
    }
    if technology in chatbot_builder:
        return chatbot_builder[technology](chatbot)
    else:
        return default(chatbot)


def generate(technology, chatbot, user, personality, extract):
    profiles = parse_profiles(user)
    serial = generate_serial()
    my_execution_stat = ExecutionStats(extract, serial)

    for profile in profiles:
        user_profile = RoleData(profile, personality)
        test_name = user_profile.test_name
        start_time_test = timeit.default_timer()

        for i in range(user_profile.conversation_number):
            the_chatbot = build_chatbot(technology, chatbot)

            the_chatbot.fallback = user_profile.fallback
            the_user = UserGeneration(user_profile, the_chatbot)
            bot_starter = user_profile.is_starter
            response_time = []

            start_time_conversation = timeit.default_timer()
            response = ''
            while True:
                if not bot_starter:
                    user_msg = the_user.open_conversation()
                    print_user(user_msg)

                    start_response_time = timeit.default_timer()
                    is_ok, response = the_chatbot.execute_with_input(user_msg)
                    end_response_time = timeit.default_timer()
                    response_time.append(timedelta(seconds=end_response_time - start_response_time).total_seconds())

                    if not is_ok:
                        if response is not None:
                            the_user.update_history("Assistant", "Error: " + response)  # added by JL
                        else:
                            the_user.update_history("Assistant", "Error: The server did not respond.")  # added by JL
                        break
                    else:
                        if response is None:
                            the_user.update_history("Assistant", "Error: The server did not respond.")

                    print_chatbot(response)
                    bot_starter = True

                elif not the_user.conversation_history['interaction']:
                    is_ok, response = the_chatbot.execute_starter_chatbot()
                    if not is_ok:
                        if response is not None:
                            the_user.update_history("Assistant", "Error: " + response)
                        else:
                            the_user.update_history("Assistant", "Error: The server did not respond.")
                        break

                    print_chatbot(response)
                    user_msg = the_user.open_conversation(response)
                else:
                    user_msg = the_user.get_response(response)

                if user_msg == "exit":
                    break
                else:
                    print_user(user_msg)

                    start_response_time = timeit.default_timer()
                    is_ok, response = the_chatbot.execute_with_input(user_msg)
                    end_response_time = timeit.default_timer()
                    time_sec = timedelta(seconds=end_response_time - start_response_time).total_seconds()
                    response_time.append(time_sec)

                    if response == 'timeout':
                        break

                    print_chatbot(response)

                    if not is_ok:
                        if response is not None:
                            the_user.update_history("Assistant", "Error: " + response)  # added by JL
                        else:
                            the_user.update_history("Assistant", "Error: The server did not respond.")  # added by JL
                        break

            if extract:
                end_time_conversation = timeit.default_timer()
                conversation_time = end_time_conversation - start_time_conversation
                formatted_time_conv = timedelta(seconds=conversation_time).total_seconds()
                print(f"Conversation Time: {formatted_time_conv} (s)")

                history = the_user.conversation_history
                metadata = get_conversation_metadata(user_profile, the_user, serial)
                dg_dataframe = the_user.data_gathering.gathering_register
                csv_extraction = the_user.goal_style[1] if the_user.goal_style[0] == 'all_answered' else False
                answer_validation_data = (dg_dataframe, csv_extraction)
                save_test_conv(history, metadata, test_name, extract, serial,
                               formatted_time_conv, response_time, answer_validation_data, counter=i)

            user_profile.reset_attributes()

        end_time_test = timeit.default_timer()
        execution_time = end_time_test - start_time_test
        formatted_time = timedelta(seconds=execution_time).total_seconds()
        print(f"Execution Time: {formatted_time} (s)")
        print('------------------------------')

        my_execution_stat.add_test_name(test_name)
        my_execution_stat.show_last_stats()

    if extract:
        my_execution_stat.show_global_stats()
        my_execution_stat.export_stats()


if __name__ == '__main__':
    parser = ArgumentParser(description='Conversation generator for a chatbot')
    parser.add_argument('--technology', required=True,
                        choices=['rasa', 'taskyto', 'ada-uam', 'millionbot', 'genion', 'lola', 'serviceform', 'kuki', 'julie', 'rivas_catalina', 'saic_malaga'],
                        help='Technology the chatbot is implemented in')
    parser.add_argument('--chatbot', required=True, help='URL where the chatbot is deployed')
    parser.add_argument('--user', required=True, help='User profile to test the chatbot')
    parser.add_argument('--personality', required=False, help='Personality file')
    parser.add_argument("--extract", default=False, help='Path to store conversation user-chatbot')
    parser.add_argument('--verbose', action='store_true', help='Shows debug prints')
    args = parser.parse_args()

    logger = create_logger(args.verbose, 'Info Logger')
    logger.info('Logs enabled!')

    check_keys(["OPENAI_API_KEY"])
    generate(args.technology, args.chatbot, args.user, args.personality, args.extract)
