import os

from argparse import ArgumentParser
from technologies.taskyto import ChatbotSpecificationTaskyto


def generate(technology: str, chatbot: str, user: str):
    if technology == 'taskyto':
        chatbot_spec = ChatbotSpecificationTaskyto()
    else:
        raise Exception(f"Technology {technology} is not supported.")

    user_profile = chatbot_spec.build_user_profile(chatbot_folder=chatbot)
    chatbot_name = os.path.basename(chatbot)
    test_name = f"{chatbot_name}_test"
    user_profile.test_name = test_name
    if user:
        user_profile_name = f"{user}{os.sep}{chatbot_name}_user_profile.yaml"
    else:
        user_profile_name = f"{chatbot}{os.sep}{chatbot_name}_user_profile.yaml"
    print(f"The following user profile has been created: {user_profile_name}")
    user_profile.to_yaml(user_profile_name)


if __name__ == '__main__':
    parser = ArgumentParser(description='User profile generator from a chatbot specification')
    parser.add_argument('--technology', required=True, choices=['taskyto'], help='Technology the chatbot is implemented in')
    parser.add_argument('--chatbot', required=True, help='Folder that contains the chatbot specification')
    parser.add_argument('--user', required=False, help='Folder to store the user profile (the chatbot folder if none is given)')
    args = parser.parse_args()

    generate(args.technology, args.chatbot, args.user)
