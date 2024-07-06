from flask import Flask, render_template, request, session, abort
import openai
import csv
import os
from dotenv import load_dotenv
import re
import logging

# Configure logging
logging.basicConfig(filename='conversation_history.log', level=logging.INFO, format='%(message)s')

cancellation_note = "If you do not wish to continue with the process, type 'cancel'."
# Function to log conversation history
def log_conversation_history(conversation_history):
    with open('conversation_history.log', 'w') as file:
        for entry in conversation_history:
            file.write(f"{entry['role']}: {entry['content']}\n")
        file.write("\n")


load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')

app = Flask(__name__)

app.secret_key = 'solomon_insait'

client = openai.OpenAI(api_key=api_key)

# Regular expression to validate the order ID format XXX-XXXXXXX (all digits)
ORDER_ID_PATTERN = re.compile(r'^\d{3}-\d{7}$')


def common_query(user_text):
    conversation = [
        {"role": "system", "content": bot_prompt},
        {"role": "user", "content": user_text}
    ]

    response = client.chat.completions.create(
        messages=conversation,
        model="gpt-3.5-turbo"
    )

    response_text = response.choices[0].message.content.strip()
    return response_text


def get_order_status(order_id):
    try:
        with open('ecommerce_orders.csv', mode='r') as file:
            csv_reader = csv.DictReader(file)
            if 'order_id' not in csv_reader.fieldnames or 'status' not in csv_reader.fieldnames:
                raise KeyError("missing column")
            for row in csv_reader:
                if row['order_id'] == order_id:
                    return row['status']
    except FileNotFoundError:
        return "Error: Orders file not found"
    except csv.Error:
        return "Error: error reading orders file"
    except KeyError:
        return "Error: Missing either 'order_id' or 'status' column (or both), check your csv orders database"


def is_order_status_query(user_text):
    response = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": "You are an e-commerce support bot. Answer with 'yes' if user asks about checking order status (understand it from context), otherwise answer with 'no'."
            },
            {
                "role": "user",
                "content": user_text
            }
        ],
        model="gpt-3.5-turbo"
    )
    intent = response.choices[0].message.content.strip().lower()
    return intent == 'yes'


def is_switch_to_real_person_query(user_text):
    response = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": """
                You are an e-commerce support bot. Your task is to determine if the following query explicitly requests to speak to a human representative or customer support agent. 
                Consider phrases that directly ask for human assistance, such as "I want to talk to a human" or "Can I speak to a real person?". 
                General expressions of dissatisfaction or frustration should not be considered as requests to switch to a human unless they explicitly ask for it.
                Answer with 'yes' if the query explicitly requests a human representative, otherwise answer with 'no'."""
            },
            {
                "role": "user",
                "content": user_text
            }
        ],
        model="gpt-3.5-turbo"
    )
    intent = response.choices[0].message.content.strip().lower()
    return intent == 'yes'


def save_contact_info(full_name, email, phone):
    file_exists = os.path.isfile('contact_info.csv')
    with open('contact_info.csv', mode='a', newline='') as file:
        fieldnames = ['full_name', 'email', 'phone']
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow({'full_name': full_name, 'email': email, 'phone': phone})


def handle_order_status(user_text):
    order_id = user_text
    if ORDER_ID_PATTERN.match(order_id):
        order_status = get_order_status(order_id)
        if order_status:
            if "Error" in order_status:
                session.pop('order_status', None)
                return order_status
            else:
                response_text = f"Your order status is: {order_status}."
        else:
            response_text = "Sorry, I couldn't find an order with that ID."
        session.pop('order_status', None)
    else:
        response_text = "The order ID should be in the format XXX-XXXXXXX. Please provide a valid order ID."
    return response_text


def handle_contact_info(user_text):
    if user_text.lower() == 'cancel':
        session.pop('contact_info', None)
        session.pop('full_name', None)
        session.pop('email', None)
        session.pop('phone', None)
        return "Certainly. How else can I help you?"

    if 'full_name' not in session:
        session['full_name'] = user_text
        response_text = f"Thank you. Please provide your email address.\n{cancellation_note}"
    elif 'email' not in session:
        session['email'] = user_text
        response_text = f"Great. Finally, please provide your phone number.\n{cancellation_note}"
    else:
        session['phone'] = user_text
        save_contact_info(session['full_name'], session['email'], session['phone'])
        response_text = "Thank you! Your information has been saved. A representative will contact you shortly."
        session.pop('contact_info', None)
        session.pop('full_name', None)
        session.pop('email', None)
        session.pop('phone', None)
    return response_text



# Single prompt encapsulating the bot's capabilities
bot_prompt = """
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


@app.route("/")
def index():
    session.clear()
    welcome_message = "Welcome to E-Commerce Support Bot! How can I assist you today?"
    return render_template("index.html", message=welcome_message)


conversation = []


@app.route("/get")
def get_bot_response():
    user_text = request.args.get('msg')
    global conversation
    # Append user's message to the conversation
    conversation.append({"role": "user", "content": user_text})

    if 'order_status' in session:
        # Check if the user's response is negative
        if user_text.lower() == 'cancel':
            response_text = "Understood. How else can I assist you?"
            session.pop('order_status', None)  # Clear the order status session
        else:
            response_text = handle_order_status(user_text)
    elif 'contact_info' in session:
        response_text = handle_contact_info(user_text)
    else:
        # Check if the user's response is unrelated to the current process
        if is_switch_to_real_person_query(user_text):
            response_text = (f"I understand your request for real person interaction. "
                             f"Could you please provide your full name first?\n{cancellation_note}")
            session['contact_info'] = True
        elif is_order_status_query(user_text):
            response_text = (f"Could you please provide your order ID "
                             f"in the following format: XXX-XXXXXXX (all digits)?\n{cancellation_note}")
            session['order_status'] = True
        else:
            # Handle completely different questions here
            response_text = common_query(user_text)

    # Append chatbot's response to the conversation
    conversation.append({"role": "assistant", "content": response_text})
    log_conversation_history(conversation)

    return response_text



if __name__ == "__main__":
    app.run(debug=True)
