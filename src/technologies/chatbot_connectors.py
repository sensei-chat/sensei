import json
import uuid
from abc import abstractmethod
import requests
from user_sim.utils.config import errors
import logging

logger = logging.getLogger('Info Logger')

###################################################
# THE CONNECTORS NEED HEAVY REFACTORING TO JUST
# ONE OR TWO CLASSES

class Chatbot:
    def __init__(self, url):
        self.url = url
        self.fallback = 'I do not understand you'

    @abstractmethod
    def execute_with_input(self, user_msg):
        """Returns a pair [bool, str] in which the first element is True if the chatbot returned normally,
           and the second is the message.
           Otherwise, False means that there is an error in the chatbot."""
        raise NotImplementedError()

    @abstractmethod
    def execute_starter_chatbot(self):
        """Returns a pair [bool, str] in which the first element is True if the chatbot returned normally,
           and the second is the message.
           Otherwise, False means that there is an error in the chatbot."""
        raise NotImplementedError()


##############################################################################################################
# RASA
class ChatbotRasa(Chatbot):
    def __init__(self, url):
        Chatbot.__init__(self, url)
        self.id = None

    def execute_with_input(self, user_msg):
        if self.id is None:
            self.id = str(uuid.uuid4())

        new_data = {
            "sender": self.id,
            "message": user_msg
        }
        post_response = requests.post(self.url, json=new_data)
        post_response_json = post_response.json()
        if len(post_response_json) > 0:
            message = '\n'.join([r.get('text') for r in post_response_json])
            return True, message
        else:
            return True, ''


##############################################################################################################
# 1million bot chatbots
class MillionBot(Chatbot):
    def __init__(self, url):
        Chatbot.__init__(self, url)
        self.headers = {}
        self.payload = {}
        self.id = None

        self.reset_url = None
        self.reset_payload = None

    def init_chatbot(self, bot_id, conversation_id, url, sender = "671ab2931382d56e5140f023"):
        self.url = "https://api.1millionbot.com/api/public/messages"
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': 'API-KEY 60553d58c41f5dfa095b34b5'
        }

        # Always generate a new ID for the conversation
        #import uuid
        #unique_id = uuid.uuid4()
        #conversation_id = unique_id.hex

        # Randomly replace a letter in the conversation_id with a hexadecimal digit
        #import random
        #import string
        #conversation_id = list(conversation_id)
        #conversation_id[random.randint(0, len(conversation_id)-1)] = random.choice(string.hexdigits)
        #conversation_id = ''.join(conversation_id)


        self.payload = {"conversation": conversation_id,
                        "sender_type": "User",
                        "sender": sender,
                        "bot": bot_id,
                        "language": "es",
                        "url": url,
                        "message": {"text": "Hola"}}

        self.reset_url = "https://api.1millionbot.com/api/public/live/status"
        self.reset_payload = {"bot": bot_id,
                              "conversation": conversation_id,
                              "status": {
                                  "origin": url,
                                  "online": False,
                                  "typing": False,
                                  "deleted": True,
                                  "attended": {},
                                  "userName": "UAM/UMU"}

                              }
        self.timeout = 10

    def execute_with_input(self, user_msg):
        if self.reset_payload is not None:
            response = requests.post(self.reset_url, headers=self.headers, json=self.reset_payload)
            # print(response)
            assert response.status_code == 200
            self.reset_payload = None

        self.payload['message']["text"] = user_msg
        timeout = self.timeout
        try:
            response = requests.post(self.url, headers=self.headers, json=self.payload, timeout=timeout)
            response_json = response.json()
            if response.status_code == 200:
                text_response = ""
                for answer in response_json['response']:
                    # to-do --> pass the buttons in the answer?
                    if 'text' in answer:
                        text_response += answer['text']+"\n"
                    elif 'payload' in answer:
                        text_response += f"\n\nAVAILABLE BUTTONS:\n\n"
                        if 'cards' in answer['payload']:
                            for card in answer['payload']['cards']:
                                if 'buttons' in card:
                                    text_response += self.__translate_buttons(card['buttons'])
                        elif 'buttons' in answer['payload']:
                            text_response += self.__translate_buttons(answer['payload']['buttons'])

                return True, text_response
            else:
                # There is an error, but it is an internal error
                print(f"Server error {response_json.get('error')}")
                errors.append({500: f"Couldn't get response from the server"})
                return False, response_json.get('error')
        except requests.exceptions.JSONDecodeError as e:
            logger = logging.getLogger('my_app_logger')
            logger.error(f"Couldn't get response from the server: {e}")
            return False, 'chatbot internal error'
        except requests.Timeout:
            logger = logging.getLogger('my_app_logger')
            logger.error(f"No response was received from the server in less than {timeout}")
            errors.append({504: f"No response was received from the server in less than {timeout}"})
            return False, 'timeout'

    def __translate_buttons(self, buttons_list) -> str:
        text_response = ''
        for button in buttons_list:
            if 'text' in button:
                text_response += f"- BUTTON TEXT: {button['text']}"
            if 'value' in button:
                text_response += f" LINK: {button['value']}\n"
            else:
                text_response += f" LINK: <empty>\n"
        return text_response


##############################################################################################################
# ADA-UAM
class ChatbotAdaUam(MillionBot):
    def __init__(self, url):
        MillionBot.__init__(self, url)
        self.init_chatbot(bot_id = "60a3be81f9a6b98f7659a6f9",
                          conversation_id="670577afe0d59bbc894897b2",
                          url="https://www.uam.es/uam/tecnologias-informacion",
                          sender="670577af4e61b2bc9462703f")

class ChatbotMillionBot(MillionBot):
    def __init__(self, url):
        MillionBot.__init__(self, url)
        self.init_chatbot(bot_id = "6465e8319de7b94a9cf01387",
                          conversation_id="670cf272ddbe1af483229440",
                          url="https://1millionbot.com/",
                          sender="670cf2727516491d1c6f69a5")

class ChatbotLolaUMU(MillionBot):
    def __init__(self, url):
        MillionBot.__init__(self, url)
        self.init_chatbot(bot_id = "5af00c50f9639920a0e4769b",
                          conversation_id="670d14d95771b0aa274c97fa",
                          url="https://www.um.es/web/estudios/acceso/estudiantes-bachillerato-y-ciclos-formativos",
                          sender="670d14d97516491d1c7109c1")

class ChatbotCatalinaRivas(MillionBot):
    def __init__(self, url):
        MillionBot.__init__(self, url)
        self.init_chatbot(bot_id = "639324ddd7a900eb516c4b13",
                          conversation_id="671ab293167d72734b1b8a55",
                          url="https://www.rivasciudad.es/",
                          sender="671ab2931382d56e5140f023")


class ChatbotSaicMalaga(MillionBot):
    def __init__(self, url):
        MillionBot.__init__(self, url)
        self.init_chatbot(bot_id = "64e5d1af081211d24e2cfec8",
                          conversation_id="671c0efd25d7e43ed46b0745",
                          url="https://saic.malaga.eu/",
                          sender="671c0efd167d72734b243bd4")

class ChatbotGenion(MillionBot):
    def __init__(self, url):
        MillionBot.__init__(self, url)
        self.init_chatbot(bot_id = "65157185ba7cc62753c7d3e2",
                          conversation_id="671f76dc9f9ee7cf16af0a59",
                          url="https://1millionbot.com/chatbot-genion-2/",
                          sender="671f76dc9f9ee7cf16af0a54")
        self.timeout = 20

##############################################################################################################
# Taskyto
class ChatbotTaskyto(Chatbot):
    def __init__(self, url):
        Chatbot.__init__(self, url)
        self.id = None

    def execute_with_input(self, user_msg):
        if self.id is None:
            try:
                post_response = requests.post(self.url + '/conversation/new')
                post_response_json = post_response.json()
                self.id = post_response_json.get('id')
            except requests.exceptions.ConnectionError:
                logger.error(f"Couldn't connect with chatbot")
                errors.append({500: f"Couldn't connect with chatbot"})
                return False, 'cut connection'
            except Exception:
                logger.error(f"Server error: invalid payload")
                errors.append({post_response.status_code: f"Server error"})
                return False, 'chatbot server error'

        if self.id is not None:
            new_data = {
                "id": self.id,
                "message": user_msg
            }

            try:
                timeout = 20
                try:
                    post_response = requests.post(self.url + '/conversation/user_message', json=new_data, timeout=timeout)
                except requests.Timeout:
                    logger.error(f"No response was received from the server in less than {timeout}")
                    errors.append({504: f"No response was received from the server in less than {timeout}"})
                    return False, 'timeout'
                except requests.exceptions.ConnectionError as e:
                    logger.error(f"Couldn't get response from the server: {e}")
                    errors.append({500: f"Couldn't get response from the server"})
                    return False, 'chatbot internal error'

                post_response_json = post_response.json()

                if post_response.status_code == 200:
                    assistant_message = post_response_json.get('message')
                    return True, assistant_message

                else:
                    # There is an error, but it is an internal error
                    errors.append({500: "Chatbot internal error"})
                    return False, post_response_json.get('error')
            except requests.exceptions.JSONDecodeError as e:
                logger.error(f"Couldn't get response from the server: {e}")
                errors.append({500: f"Couldn't get response from the server"})
                return False, 'chatbot internal error'

        return True, ''

    def execute_starter_chatbot(self):
        timeout = 20
        try:
            post_response = requests.post(self.url + '/conversation/new')
            post_response_json = post_response.json()
            self.id = post_response_json.get('id')
            if post_response.status_code == 200:
                assistant_message = post_response_json.get('message')
                if assistant_message is None:
                    return True, 'Hello'
                else:
                    return True, assistant_message
            else:
                # There is an error, but it is an internal error
                logger.error(f"Chatbot internal error")
                errors.append({500: "Chatbot internal error"})
                return False, post_response_json.get('error')
        except requests.exceptions.ConnectionError:
            logger.error(f"Couldn't connect with chatbot")
            errors.append({500: f"Couldn't connect with chatbot"})
            return False, 'cut connection'
        except requests.Timeout:
            logger.error(f"No response was received from the server in less than {timeout}")
            errors.append({504: f"No response was received from the server in less than {timeout}"})
            return False, 'timeout'

##############################################################################################################
# Serviceform
class ChatbotServiceform(Chatbot):
    def __init__(self, url):
        Chatbot.__init__(self, url)
        self.url = "https://dash.serviceform.com/api/ai"
        self.headers = {
            'Content-Type': 'text/plain;charset=UTF-8'
        }
        self.payload = {"sid":"1729589460223tvzbcxe5zocgr5hs",
                        "tid":"haGDRXUPY9tQOsOS44jY",
                        "message":"Hello",
                        "extraTraining":"",
                        "assistant_id":"asst_PUNPPDAFOgHRLrlmHhDuQhCM"}

    def execute_with_input(self, user_msg):
        self.payload['message'] = user_msg
        timeout = 10000
        try:
            response = requests.post(self.url, headers=self.headers, json=self.payload, timeout=timeout)
            if response.status_code == 200:
                data_bytes = response.content
                data_str = data_bytes.decode('utf-8')
                data_dict = json.loads(data_str)
                return True, data_dict['response']
            else:
                # There is an error, but it is an internal error
                print(f"Server error {response.status_code}")
                errors.append({response.status_code: f"Couldn't get response from the server"})
                return False, f"Something went wrong. Status Code: {response.status_code}"
        except requests.exceptions.JSONDecodeError as e:
            logger = logging.getLogger('my_app_logger')
            logger.log(f"Couldn't get response from the server: {e}")
            return False, 'chatbot internal error'
        except requests.Timeout:
            logger = logging.getLogger('my_app_logger')
            logger.error(f"No response was received from the server in less than {timeout}")
            errors.append({504: f"No response was received from the server in less than {timeout}"})
            return False, 'timeout'



##############################################################################################################
# Kuki chatbot
class KukiChatbot(Chatbot):
    def __init__(self, url):
        Chatbot.__init__(self, url)
        self.url = "https://kuli.kuki.ai/cptalk"
        self.headers = {
            'Content-Type': 'application/x-www-form-urlencoded'  # Standard for form data
        }
        self.payload = {
            'uid': '54d5a563617d1999',
            'input': 'And before?',
            'sessionid': '485198820'
        }

    def execute_with_input(self, user_msg):
        self.payload['input'] = user_msg
        timeout = 10000
        try:
            response = requests.post(self.url, headers=self.headers, data=self.payload, timeout=timeout)
            if response.status_code == 200:
                response_dict = json.loads(response.text)
                responses = response_dict['responses']
                all_responses = '\n'.join(responses)
                return True, all_responses
            else:
                # There is an error, but it is an internal error
                print(f"Server error {response.status_code}")
                errors.append({response.status_code: f"Couldn't get response from the server"})
                return False, f"Something went wrong. Status Code: {response.status_code}"
        except requests.exceptions.JSONDecodeError as e:
            logger = logging.getLogger('my_app_logger')
            logger.log(f"Couldn't get response from the server: {e}")
            return False, 'chatbot internal error'
        except requests.Timeout:
            logger = logging.getLogger('my_app_logger')
            logger.error(f"No response was received from the server in less than {timeout}")
            errors.append({504: f"No response was received from the server in less than {timeout}"})
            return False, 'timeout'

##############################################################################################################
# Julie chatbot
class JulieChatbot(Chatbot):
    def __init__(self, url):
        Chatbot.__init__(self, url)
        self.url = 'https://askjulie2.nextit.com/AlmeAPI/api/Conversation/Converse'
        self.headers = headers = {
            'Content-Type': 'application/json',
        }
        self.payload = {"userId":"4b62a896-85f0-45dd-b94c-a6496f831107",
           "sessionId":"724e371e-9917-4ab2-9da4-6809199366eb",
           "question":"How are you?",
           "origin":"Typed",
           "displayText":"How are you?",
           "parameters":{
               "Context":{
                   "CurrentUrl":
                       {
                           "AbsolutePath":"https://www.amtrak.com/home.html",
                           "Protocol":"https:",
                           "Host":"www.amtrak.com",
                           "HostName":"www.amtrak.com",
                           "Port":"",
                           "Uri":"/home.html",
                           "Query":"",
                           "Fragment":"",
                           "Origin":"https://www.amtrak.com",
                           "Type":"embedded",
                           "PageName":"Amtrak Tickets, Schedules and Train Routes"
                       }
                },
               "UiVersion":"1.33.17"
           },
           "channel":"Web",
           "language":"en-US",
           "accessKey":"00000000-0000-0000-0000-000000000000"
        }

    def execute_with_input(self, user_msg):
        self.payload['question'] = user_msg
        self.payload['displayText'] = user_msg
        timeout = 10000
        try:
            response = requests.post(self.url, headers=self.headers, json=self.payload, timeout=timeout)
            if response.status_code == 200:
                response_dict = json.loads(response.text)
                chat_response = response_dict['text']
                if 'displayLinkCollection' in response_dict and response_dict['displayLinkCollection']:
                    buttons = self.__translate_buttons(response_dict['displayLinkCollection'])
                    chat_response += f"\n\n{buttons}"
                return True, chat_response
            else:
                # There is an error, but it is an internal error
                print(f"Server error {response.status_code}")
                errors.append({response.status_code: f"Couldn't get response from the server"})
                return False, f"Something went wrong. Status Code: {response.status_code}"
        except requests.exceptions.JSONDecodeError as e:
            logger = logging.getLogger('my_app_logger')
            logger.log(f"Couldn't get response from the server: {e}")
            return False, 'chatbot internal error'
        except requests.Timeout:
            logger = logging.getLogger('my_app_logger')
            logger.error(f"No response was received from the server in less than {timeout}")
            errors.append({504: f"No response was received from the server in less than {timeout}"})
            return False, 'timeout'

    def __translate_buttons(self, buttons_dict) -> str:
        button_description = 'AVAILABLE BUTTONS: '
        for section in buttons_dict['Sections']:
            for button in section["Links"]:
                button_text = ""
                if 'DisplayText' in button:
                    button_text += f"- BUTTON TEXT: {button['DisplayText']}"
                if 'Metadata' in button and 'UnitUID' in button['Metadata']:
                    button_text += f" LINK: {button['Metadata']['UnitUID']}\n"
                else:
                    button_text += f" LINK: <empty>\n"
                button_description += f'\n {button_text}'
        return button_description


