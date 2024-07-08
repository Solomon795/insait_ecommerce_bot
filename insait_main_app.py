from flask import Flask, render_template, request, session
import datetime
from dotenv import load_dotenv
import os
from ecommerce_bot import ECommerceSupportBot
import configparser

# Load configurations from config.ini
config = configparser.ConfigParser()
config.read('config.ini')

# Function to log conversation history
def log_conversation_history(conversation_history):
    with open('logs/conversation_history.log', 'a') as file:
        # Only log the last message in the conversation history
        last_message = conversation_history[-1]
        # Get the current time and format it
        now = datetime.datetime.now()
        formatted_now = now.strftime('%Y-%m-%d %H:%M')
        # Log the message with a timestamp
        file.write(f"{formatted_now}: {last_message['role']}: {last_message['content']}\n")
        # Add a newline after each assistant message for readability
        if last_message['role'] == 'assistant':
            file.write("\n")



load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')
secret_key = os.getenv('SECRET_KEY')

app = Flask(__name__)
app.secret_key = secret_key

bot = ECommerceSupportBot(api_key=api_key, config=config)
CONVERSATION_HISTORY = [{"role": "assistant", "content": bot.config['DEFAULT']['BOT_PROMPT']}]

@app.route("/")
def index():
    reset()
    welcome_message = bot.config['DEFAULT']['BOT_WELCOME']
    return render_template("index.html", message=welcome_message)

@app.route("/get", methods=['GET', 'POST'])
def get_bot_response():
    user_text = request.args.get('msg')

    global CONVERSATION_HISTORY
    # Append user's message to the conversation
    CONVERSATION_HISTORY.append({"role": "user", "content": user_text})
    log_conversation_history(CONVERSATION_HISTORY)

    if 'order_status' in session:
        # Check if the user's response is negative
        if user_text.lower() == 'cancel':
            response_text = bot.config['DEFAULT']['ASSIST_AFTER_CANCEL']
            session.pop('order_status', None)  # Clear the order status session
        else:
            response_text = bot.handle_order_status(user_text, session)
    elif 'contact_info' in session:
        response_text = bot.handle_contact_info(user_text, session)
    else:
        # Check if the user's response is unrelated to the current process
        if bot.is_query_type(user_text, bot.config['SWITCH_TO_REP_STREAM']['IS_SWITCH_TO_HUMAN_REQUEST_PROMPT']):
            response_text = (f"{bot.config['SWITCH_TO_REP_STREAM']['SWITCH_TO_REP_RESP_START']}"
                             f"\n{bot.config['DEFAULT']['CANCELLATION_NOTE']}")
            session['contact_info'] = True
        elif bot.is_query_type(user_text, bot.config['ORDER_STATUS_STREAM']['IS_ORDER_STATUS_REQUEST_PROMPT']):
            response_text = f"{bot.config['ORDER_STATUS_STREAM']['ORDER_ID_INQUIRY']}\n{bot.config['DEFAULT']['CANCELLATION_NOTE']}"
            session['order_status'] = True
        else:
            response_text = bot.common_query(user_text, CONVERSATION_HISTORY)


    # Append chatbot's response to the conversation
    CONVERSATION_HISTORY.append({"role": "assistant", "content": response_text})
    log_conversation_history(CONVERSATION_HISTORY)

    return response_text

@app.route("/reset", methods=['GET'])
def reset():
    session.clear()
    # Log a separator between sessions
    with open('logs/conversation_history.log', 'a') as file:
        file.write("----- New Session -----\n")
    return "Session reset."

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')
