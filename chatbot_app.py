from flask import Flask, render_template, request, session
import openai
import csv
import os
from dotenv import load_dotenv
import re
import logging

# Configure logging
logging.basicConfig(filename='conversation_history.log', level=logging.INFO, format='%(message)s')

BOT_WELCOME = "Welcome to E-Commerce Support Bot! How can I assist you today?"
CANCELLATION_NOTE = "If you do not wish to continue with the process, type 'cancel'."
ASSIST_AFTER_CANCEL = "Certainly. How else can I help you?"

CONVERSATION_HISTORY = []

ERROR_FILE_NOT_FOUND = "Error: Orders file not found"
ERROR_CSV = "Error: error reading orders file"
ERROR_MISSING_COLUMN = "Error: Missing either 'order_id' or 'status' column (or both), check your csv orders database"
ERROR_CSV_SAVE_CONTACT_OPEN = ("Error: Permission denied while trying to write contact information.\nProbably"
                               "the csv file for saving contact info is open now. Please close it if so and try "
                               "again later.")

NO_INTERNET_ERROR = ("I'm currently experiencing connection issues. "
                     "Please try again later.")

ORDER_ID_INQUIRY = ("Could you please provide your order ID in "
                    "the following format: XXX-XXXXXXX (all digits)?")
ORDER_NOT_FOUND = "Sorry, I couldn't find an order with that ID."
ORDER_WRONG_PATTERN = "The order ID should be in the format XXX-XXXXXXX. Please provide a valid order ID."
ORDER_STATUS_UNKNOWN = "Order status is empty or unknown"



SWITCH_TO_REP_RESP_START = ("I understand your request for real person interaction. "
                            "Could you please provide your full name first?")
SWITCH_TO_REP_PROVIDE_EMAIL = "Thank you. Please provide your email address."
SWITCH_TO_REP_PROVIDE_PHONE = "Great. Finally, please provide your phone number. It should contain 10 digits only, starting with 05.."
CONTACT_INFO_SAVED_MSG = "Thank you! Your information has been saved. A representative will contact you shortly."


IS_ORDER_STATUS_REQUEST_PROMPT = ("You are an e-commerce support bot. "
                                  "Answer with 'yes' if user asks about checking order status specifically "
                                  "understand it from context and sentiment, but the user text should "
                                  "contain something about order or purchased items), otherwise answer with 'no'.")

IS_ORDER_STATUS_RELEVANT_PROMPT = ("You are an e-commerce support bot. Answer with 'yes' if order status retrieved is "
                                   "relevant."
                                   "100% relevant are statuses: Cancelled, Delivered, Shipped, On-hold, Confirmed, "
                                   "Packaging."
                                   "If order status is empty or doesn't make sense in terms of understanding what is "
                                   "whith the order,"
                                   "consists of random characters, etc, answer with 'no'.")
IS_SWITCH_TO_HUMAN_REQUEST_PROMPT = """You are an e-commerce support bot. Your task is to determine if the following query 
explicitly requests to speak to a human representative or customer support agent. Consider phrases that directly ask 
for human assistance, such as "I want to talk to a human" or "Can I speak to a real person?". General expressions of 
dissatisfaction or frustration should not be considered as requests to switch to a human unless they explicitly ask 
for it. Answer with 'yes' if the query explicitly requests a human representative, otherwise answer with 'no'."""

# Single prompt encapsulating the bot's capabilities
BOT_PROMPT = """
You are an e-commerce support bot designed to handle customer queries about products, orders, and policies. You should 
understand and respond to inquiries regarding order status, return policies, and more.
Provide accurate responses and handle multi-turn conversations by asking clarifying questions when necessary. Ensure 
that the responses are clear, helpful, and reflect the policies and information relevant to the e-commerce platform.

You should know following information about the return policies. Return policy for items purchased at the store is that 
customer can return most items within 30 days of purchase for a full refund or exchange. Items must be in their original condition, 
with all tags and packaging intact. The customer should bring his or her receipt or proof of purchase when returning items.

Certain items such as clearance merchandise, perishable goods, and personal care items are non-returnable. 
Offer the customer to check the product description or to ask a store associate for more details if he or she has doubts.

If customer's question is related to how refund can be received, answer based on this: refunds will be 
issued to the original form of payment. If customer paid by credit card, the refund will be credited to customer's card. 
If customer paid by cash or check, the customer will receive a cash refund.

If customer asks anything about refund, don't throw everything you know at him. Try to narrow his question down and give specific question
"""




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
