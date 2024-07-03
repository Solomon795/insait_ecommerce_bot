from flask import Flask, render_template, request, session
import openai
import csv
import os
from dotenv import load_dotenv
import re

load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')

app = Flask(__name__)

app.secret_key = 'solomon_insait'

client = openai.OpenAI(api_key=api_key)

# Regular expression to validate the order ID format XXX-XXXXXXX (all digits)
ORDER_ID_PATTERN = re.compile(r'^\d{3}-\d{7}$')

def get_order_status(order_id):
    with open('ecommerce_orders.csv', mode='r') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            if row['order_id'] == order_id:
                return row['status']
    return None

def is_order_status_query(user_text):
    """Function to classify if the user text is asking about order status."""
    response = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": "You are an e-commerce support bot. Determine if the following query is related to checking the status of an order."
            },
            {
                "role": "user",
                "content": user_text
            },
            {
                "role": "system",
                "content": "Answer with 'yes' if it is related to checking order status, otherwise answer with 'no'."
            }
        ],
        model="gpt-3.5-turbo"
    )
    intent = response.choices[0].message.content.strip().lower()
    return intent == 'yes'


def is_switch_to_real_person_query(user_text):
    """Function to classify if the user wants to switch to a real person."""
    response = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": "Is this query asking to speak to human representative?Answer with 'yes' or 'no'."
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
    """Save contact information to a CSV file."""
    file_exists = os.path.isfile('contact_info.csv')
    with open('contact_info.csv', mode='a', newline='') as file:
        fieldnames = ['full_name', 'email', 'phone']
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow({'full_name': full_name, 'email': email, 'phone': phone})

# Single prompt encapsulating the bot's capabilities
bot_prompt = """
You are an e-commerce support bot designed to handle customer queries about products, orders, and policies. You should understand and respond to inquiries regarding:

1. Order Status: Users might ask about the status of their orders using phrases like "What is the status of my order?" or "Has my order shipped?"
2. Return Policies: Users might inquire about return policies and procedures using phrases like "What is your return policy?" or "Can I return items?"
3. Product Information: Users might seek information about products using phrases like "Tell me about your products" or "What are your best-selling items?"

Provide accurate responses and handle multi-turn conversations by asking clarifying questions when necessary. Ensure that the responses are clear, helpful, and reflect the policies and information relevant to the e-commerce platform.

If the user wants to speak to a real person, ask for their full name, email, and phone number and save this information to a CSV file.
"""

@app.route("/")
def index():
    # Clear the session on page load
    session.clear()
    welcome_message = "Welcome to E-Commerce Support Bot! How can I assist you today?"
    return render_template("index.html", message=welcome_message)

@app.route("/get")
def get_bot_response():
    user_text = request.args.get('msg')
    if 'order_status' in session:
        order_id = user_text
        if ORDER_ID_PATTERN.match(order_id):
            order_status = get_order_status(order_id)
            if order_status:
                response_text = f"Your order status is: {order_status}."
            else:
                response_text = "Sorry, I couldn't find an order with that ID."
            session.pop('order_status', None)
        else:
            response_text = "The order ID should be in the format XXX-XXXXXXX. Please provide a valid order ID."
    elif 'contact_info' in session:
        # Collect contact information
        if 'full_name' not in session:
            session['full_name'] = user_text
            response_text = "Thank you. Please provide your email address."
        elif 'email' not in session:
            session['email'] = user_text
            response_text = "Great. Finally, please provide your phone number."
        else:
            session['phone'] = user_text
            save_contact_info(session['full_name'], session['email'], session['phone'])
            response_text = "Thank you! Your information has been saved. A representative will contact you shortly."
            session.pop('contact_info', None)
            session.pop('full_name', None)
            session.pop('email', None)
            session.pop('phone', None)
    else:
        # Check if the user wants to switch to a real person
        if is_switch_to_real_person_query(user_text):
            response_text = "Sure, I can help you with that. Please provide your full name."
            session['contact_info'] = True
        # Check if the user is asking about order status
        elif is_order_status_query(user_text):
            response_text = "Could you please provide your order ID in following format: XXX-XXXXXXX (all digits)?"
            session['order_status'] = True  # Set the flag to expect an order ID next
        else:
            # Include the bot prompt in the conversation
            conversation = [
                {"role": "system", "content": bot_prompt},
                {"role": "user", "content": user_text}
            ]

            response = client.chat.completions.create(
                messages=conversation,
                model="gpt-3.5-turbo"
            )

            # Extract the response text from the OpenAI API response
            response_text = response.choices[0].message.content.strip()

    return response_text

if __name__ == "__main__":
    app.run(debug=True)
