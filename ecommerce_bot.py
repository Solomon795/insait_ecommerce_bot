import openai
import re
import csv
import os

class ECommerceSupportBot:
    def __init__(self, api_key, config):
        self.client = openai.OpenAI(api_key=api_key)
        self.order_id_pattern = re.compile(r'^\d{3}-\d{7}$')
        self.config = config

    def common_query(self, user_text, conversation_history):
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
        return re.match(r"[^@]+@[^@]+\.[^@]+", email) is not None

    def is_valid_phone(self, phone):
        return re.match(r"^\d{10}$", phone) is not None

    def handle_order_status(self, user_text, session):
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
        session.pop('contact_info', None)
        session.pop('full_name', None)
        session.pop('email', None)
        session.pop('phone', None)

    def handle_contact_info(self, user_text, session):
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
