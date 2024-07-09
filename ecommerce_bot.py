import openai
import re
import csv
import os

class ECommerceSupportBot:
    def __init__(self, api_key, config):
        """
        Initializes the Ecom Bot with the provided API key and configuration.

        Args:
            api_key (str): The API key for the OpenAI service.
            config (configparser.ConfigParser): The configuration object containing prompts and preset outputs for the bot.
        """
        self.client = openai.OpenAI(api_key=api_key)
        self.order_id_pattern = re.compile(r'^\d{3}-\d{7}$')
        self.config = config

    def common_query(self, user_text, conversation_history):
        """
        Processes a common user query and generates a gpt-response.

        Args:
            user_text (str): The user's input text.
            conversation_history (list): A list of dictionaries representing the conversation history.

        Returns:
            str: The chatbot's response text.
        """
        conversation = conversation_history + [{"role": "user", "content": user_text}]
        try:
            response = self.client.chat.completions.create(
                messages=conversation,
                model="gpt-3.5-turbo"
            )
            response_text = response.choices[0].message.content.strip()
        except openai.APIConnectionError:
            response_text = self.config['ERRORS']['NO_INTERNET_ERROR']
        return response_text

    def is_query_type(self, user_text, assistant_prompt):
        """
        Determines if the user's query matches a specific type based on an assistant prompt.

        Args:
            user_text (str): The user's input text.
            assistant_prompt (str): The assistant prompt to match against the user's query.

        Returns:
            bool: True if the query matches the type, False otherwise.
        """
        try:
            response = self.client.chat.completions.create(
                messages=[
                    {"role": "assistant", "content": assistant_prompt},
                    {"role": "user", "content": user_text}
                ],
                model="gpt-3.5-turbo"
            )
            intent = response.choices[0].message.content.strip().lower()
        except openai.APIConnectionError:
            intent = 'no'
        return intent == 'yes'

    def get_order_status(self, order_id):
        """
        Retrieves the status of an order based on the provided order ID.

        Args:
            order_id (str): The ID of the order to retrieve the status for.

        Returns:
            str: The status of the order, or an error message if an error occurs.
        """
        try:
            with open('ecommerce_orders.csv', mode='r') as file:
                csv_reader = csv.DictReader(file)
                if 'order_id' not in csv_reader.fieldnames or 'status' not in csv_reader.fieldnames:
                    raise KeyError("missing column")
                for row in csv_reader:
                    if row['order_id'] == order_id:
                        if row['status'] == '':
                            return "empty"
                        return row['status']
        except FileNotFoundError:
            return self.config['ERRORS']['ERROR_FILE_NOT_FOUND']
        except csv.Error:
            return self.config['ERRORS']['ERROR_CSV']
        except KeyError:
            return self.config['ERRORS']['ERROR_MISSING_COLUMN']

    def save_contact_info(self, full_name, email, phone):
        """
          Saves the provided contact information to a CSV file (when switch to human rep)

          Args:
              full_name (str): The full name of the contact.
              email (str): The email address of the contact.
              phone (str): The phone number of the contact.

          Returns:
              int: 1 if the contact information was saved successfully, 0 if there was a permission error.
          """
        file_exists = os.path.isfile('contact_info.csv')
        try:
            with open('contact_info.csv', mode='a', newline='') as file:
                fieldnames = ['full_name', 'email', 'phone']
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                if not file_exists:
                    writer.writeheader()
                writer.writerow({'full_name': full_name, 'email': email, 'phone': phone})
            return 1
        except PermissionError:
            return 0

    def is_valid_email(self, email):
        """
        Validates if the provided email address is in the correct format.

        Args:
            email (str): The email address to validate.

        Returns:
            bool: True if the email address is valid, False otherwise.
        """
        return re.match(r"[^@]+@[^@]+\.[^@]+", email) is not None

    def is_valid_phone(self, phone):
        """
        Validates if the provided phone number is a valid 10-digit number.

        Args:
            phone (str): The phone number to validate.

        Returns:
            bool: True if the phone number is valid, False otherwise.
        """
        return re.match(r"^\d{10}$", phone) is not None

    def handle_order_status(self, user_text, session):
        """
        Handles the user's request for order status based on their input and session data.

        Args:
            user_text (str): The user's input text, expected to be an order ID.
            session (dict): The session data for the current user.

        Returns:
            str: The response text from the chatbot regarding the order status.
        """
        order_id = user_text
        if self.order_id_pattern.match(order_id):
            order_status = self.get_order_status(order_id)
            if order_status:
                if "Error" in order_status:
                    session.pop('order_status', None)
                    return order_status
                elif not self.is_query_type(order_status, self.config['ORDER_STATUS_STREAM']['IS_ORDER_STATUS_RELEVANT_PROMPT']) \
                        or order_status == 'empty':
                    session.pop('order_status', None)
                    return self.config['ORDER_STATUS_STREAM']['ORDER_STATUS_UNKNOWN']
                else:
                    response_text = f"Your order status is: {order_status}."
            else:
                response_text = self.config['ORDER_STATUS_STREAM']['ORDER_NOT_FOUND']
            session.pop('order_status', None)
        else:
            response_text = self.config['ORDER_STATUS_STREAM']['ORDER_WRONG_PATTERN']
        return response_text

    def clear_switch_to_human_session(self, session):
        """
        Clears the session data related to switching to a human representative.

        Args:
            session (dict): The session data for the current contact asking for human rep.
        """
        session.pop('contact_info', None)
        session.pop('full_name', None)
        session.pop('email', None)
        session.pop('phone', None)

    def handle_contact_info(self, user_text, session):
        """
        Handles the user's input for providing contact information during a session.

        Args:
            user_text (str): The user's input text.
            session (dict): The session data for the user, asking for human rep.

        Returns:
            str: The response text from the chatbot regarding the contact information process.
        """
        if user_text.lower() == 'cancel':
            self.clear_switch_to_human_session(session)
            return self.config['DEFAULT']['ASSIST_AFTER_CANCEL']
        if 'full_name' not in session:
            session['full_name'] = user_text
            response_text = f"{self.config['SWITCH_TO_REP_STREAM']['SWITCH_TO_REP_PROVIDE_EMAIL']}\n{self.config['DEFAULT']['CANCELLATION_NOTE']}"
        elif 'email' not in session:
            if not self.is_valid_email(user_text):
                response_text = f"The email address '{user_text}' is not valid. Please provide a valid email address.\n{self.config['DEFAULT']['CANCELLATION_NOTE']}"
            else:
                session['email'] = user_text
                response_text = f"{self.config['SWITCH_TO_REP_STREAM']['SWITCH_TO_REP_PROVIDE_PHONE']}\n{self.config['DEFAULT']['CANCELLATION_NOTE']}"
        else:
            if not self.is_valid_phone(user_text):
                response_text = f"The phone number '{user_text}' is not valid. Please provide a valid 10-digit phone number.\n{self.config['DEFAULT']['CANCELLATION_NOTE']}"
            else:
                session['phone'] = user_text
                save_result = self.save_contact_info(session['full_name'], session['email'], session['phone'])
                if save_result == 0:
                    response_text = self.config['ERRORS']['ERROR_CSV_SAVE_CONTACT_OPEN']
                else:
                    response_text = self.config['SWITCH_TO_REP_STREAM']['CONTACT_INFO_SAVED_MSG']
                self.clear_switch_to_human_session(session)
        return response_text
