from flask import Flask, render_template, request, session
import openai
import csv
import os
from dotenv import load_dotenv
import re
import logging
import configparser

# Configure logging
logging.basicConfig(filename='conversation_history.log', level=logging.INFO, format='%(message)s')
CONVERSATION_HISTORY = []

# Load configurations from config.ini
config = configparser.ConfigParser()
config.read('config.ini')

# Import variables from sections
BOT_WELCOME = config['DEFAULT']['BOT_WELCOME']
BOT_PROMPT = config['DEFAULT']['BOT_PROMPT']
CANCELLATION_NOTE = config['DEFAULT']['CANCELLATION_NOTE']
ASSIST_AFTER_CANCEL = config['DEFAULT']['ASSIST_AFTER_CANCEL']

ERROR_FILE_NOT_FOUND = config['ERRORS']['ERROR_FILE_NOT_FOUND']
ERROR_CSV = config['ERRORS']['ERROR_CSV']
ERROR_MISSING_COLUMN = config['ERRORS']['ERROR_MISSING_COLUMN']
ERROR_CSV_SAVE_CONTACT_OPEN = config['ERRORS']['ERROR_CSV_SAVE_CONTACT_OPEN']
NO_INTERNET_ERROR = config['ERRORS']['NO_INTERNET_ERROR']

IS_ORDER_STATUS_REQUEST_PROMPT = config['ORDER_STATUS_STREAM']['IS_ORDER_STATUS_REQUEST_PROMPT']
ORDER_ID_INQUIRY = config['ORDER_STATUS_STREAM']['ORDER_ID_INQUIRY']
ORDER_NOT_FOUND = config['ORDER_STATUS_STREAM']['ORDER_NOT_FOUND']
ORDER_WRONG_PATTERN = config['ORDER_STATUS_STREAM']['ORDER_WRONG_PATTERN']
IS_ORDER_STATUS_RELEVANT_PROMPT = config['ORDER_STATUS_STREAM']['IS_ORDER_STATUS_RELEVANT_PROMPT']
ORDER_STATUS_UNKNOWN = config['ORDER_STATUS_STREAM']['ORDER_STATUS_UNKNOWN']

IS_SWITCH_TO_HUMAN_REQUEST_PROMPT = config['SWITCH_TO_REP_STREAM']['IS_SWITCH_TO_HUMAN_REQUEST_PROMPT']
SWITCH_TO_REP_RESP_START = config['SWITCH_TO_REP_STREAM']['SWITCH_TO_REP_RESP_START']
SWITCH_TO_REP_PROVIDE_EMAIL = config['SWITCH_TO_REP_STREAM']['SWITCH_TO_REP_PROVIDE_EMAIL']
SWITCH_TO_REP_PROVIDE_PHONE = config['SWITCH_TO_REP_STREAM']['SWITCH_TO_REP_PROVIDE_PHONE']
CONTACT_INFO_SAVED_MSG = config['SWITCH_TO_REP_STREAM']['CONTACT_INFO_SAVED_MSG']



# Function to log conversation history
def log_conversation_history(conversation_history):
    with open('conversation_history.log', 'w') as file:
        for entry in conversation_history:
            file.write(f"{entry['role']}: {entry['content']}\n")
        file.write("\n")


load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')
secret_key = os.getenv('SECRET_KEY')

app = Flask(__name__)

app.secret_key = secret_key

client = openai.OpenAI(api_key=api_key)

# Regular expression to validate the order ID format XXX-XXXXXXX (all digits)
ORDER_ID_PATTERN = re.compile(r'^\d{3}-\d{7}$')


def common_query(user_text):
    conversation = [
        {"role": "assistant", "content": BOT_PROMPT},
        {"role": "user", "content": user_text}
    ]

    try:
        response = client.chat.completions.create(
            messages=conversation,
            model="gpt-3.5-turbo"
        )
        response_text = response.choices[0].message.content.strip()
    except openai.APIConnectionError:
        response_text = NO_INTERNET_ERROR

    return response_text


def is_query_type(user_text, assistant_prompt):
    try:
        response = client.chat.completions.create(
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


def get_order_status(order_id):
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
        return ERROR_FILE_NOT_FOUND
    except csv.Error:
        return ERROR_CSV
    except KeyError:
        return ERROR_MISSING_COLUMN



def save_contact_info(full_name, email, phone):
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


def is_valid_email(email):
    # Basic email validation regex
    return re.match(r"[^@]+@[^@]+\.[^@]+", email) is not None


def is_valid_phone(phone):
    # Basic phone number validation (10 digits)
    return re.match(r"^\d{10}$", phone) is not None


def handle_order_status(user_text):
    order_id = user_text
    if ORDER_ID_PATTERN.match(order_id):
        order_status = get_order_status(order_id)
        if order_status:
            if "Error" in order_status:
                session.pop('order_status', None)
                return order_status
            elif not is_query_type(order_status, IS_ORDER_STATUS_RELEVANT_PROMPT) or order_status == 'empty':
                session.pop('order_status', None)
                return ORDER_STATUS_UNKNOWN
            else:
                response_text = f"Your order status is: {order_status}."
        else:
            response_text = ORDER_NOT_FOUND
        session.pop('order_status', None)
    else:
        response_text = ORDER_WRONG_PATTERN
    return response_text

def clear_switch_to_human_session():
    session.pop('contact_info', None)
    session.pop('full_name', None)
    session.pop('email', None)
    session.pop('phone', None)

def handle_contact_info(user_text):
    if user_text.lower() == 'cancel':
        clear_switch_to_human_session()
        return ASSIST_AFTER_CANCEL

    if 'full_name' not in session:
        session['full_name'] = user_text
        response_text = f"{SWITCH_TO_REP_PROVIDE_EMAIL}\n{CANCELLATION_NOTE}"
    elif 'email' not in session:
        if not is_valid_email(user_text):
            response_text = f"The email address '{user_text}' is not valid. Please provide a valid email address.\n{CANCELLATION_NOTE}"
        else:
            session['email'] = user_text
            response_text = f"{SWITCH_TO_REP_PROVIDE_PHONE}\n{CANCELLATION_NOTE}"
    else:
        if not is_valid_phone(user_text):
            response_text = f"The phone number '{user_text}' is not valid. Please provide a valid 10-digit phone number.\n{CANCELLATION_NOTE}"
        else:
            session['phone'] = user_text
            save_result = save_contact_info(session['full_name'], session['email'], session['phone'])
            if save_result == 0:
                response_text = ERROR_CSV_SAVE_CONTACT_OPEN
            else:
                response_text = CONTACT_INFO_SAVED_MSG
            clear_switch_to_human_session()
    return response_text


@app.route("/")
def index():
    session.clear()
    welcome_message = BOT_WELCOME
    return render_template("index.html", message=welcome_message)


@app.route("/get")
def get_bot_response():
    user_text = request.args.get('msg')
    global CONVERSATION_HISTORY
    # Append user's message to the conversation
    CONVERSATION_HISTORY.append({"role": "user", "content": user_text})

    if 'order_status' in session:
        # Check if the user's response is negative
        if user_text.lower() == 'cancel':
            response_text = ASSIST_AFTER_CANCEL
            session.pop('order_status', None)  # Clear the order status session
        else:
            response_text = handle_order_status(user_text)
    elif 'contact_info' in session:
        response_text = handle_contact_info(user_text)
    else:
        # Check if the user's response is unrelated to the current process
        if is_query_type(user_text, IS_SWITCH_TO_HUMAN_REQUEST_PROMPT):
            response_text = f"{SWITCH_TO_REP_RESP_START}\n{CANCELLATION_NOTE}"
            session['contact_info'] = True
        elif is_query_type(user_text, IS_ORDER_STATUS_REQUEST_PROMPT):
            response_text = f"{ORDER_ID_INQUIRY}\n{CANCELLATION_NOTE}"
            session['order_status'] = True
        else:
            response_text = common_query(user_text)

    # Append chatbot's response to the conversation
    CONVERSATION_HISTORY.append({"role": "assistant", "content": response_text})
    log_conversation_history(CONVERSATION_HISTORY)

    return response_text


if __name__ == "__main__":
    app.run(debug=True)
