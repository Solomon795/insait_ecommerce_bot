from flask import Flask, render_template, request, session
import openai
import csv
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')

app = Flask(__name__)

app.secret_key = 'solomon_insait'

client = openai.OpenAI(api_key=openai.api_key)

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
                "role": "user",
                "content": f"{user_text}\nIs this query asking about order status? Answer with 'yes' or 'no'."
            }
        ],
        model="gpt-3.5-turbo"
    )
    intent = response.choices[0].message.content.strip().lower()
    return intent == 'yes'

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/get")
def get_bot_response():
    user_text = request.args.get('msg')
    if 'order_status' in session:
        order_id = user_text
        order_status = get_order_status(order_id)
        if order_status:
            response_text = f"Your order status is: {order_status}."
        else:
            response_text = "Sorry, I couldn't find an order with that ID."
        session.pop('order_status', None)
    else:
        # Check if the user is asking about order status
        if is_order_status_query(user_text):
            response_text = "Could you please provide your order ID?"
            session['order_status'] = True  # Set the flag to expect an order ID next
        else:
            response = client.chat.completions.create(
                messages=[
                    {
                    "role": "user",
                    "content": user_text
                    }
                ],
                model="gpt-3.5-turbo"
            )
            # Extract the response text from the OpenAI API response
            response_text = response.choices[0].message.content.strip()


    return response_text

if __name__ == "__main__":
    app.run(debug=True)