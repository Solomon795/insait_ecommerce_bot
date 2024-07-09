# Insait E-Commerce Customer Support Chatbot
## Overview
This project implements a conversational agent (chatbot) powered by a Large Language Model (LLM) using the OpenAI API. The chatbot handles customer support queries for an e-commerce platform, managing multi-turn conversations and providing accurate responses to inquiries about order status, return policies, and more.

## Setup Instructions
### Prerequisites
Ensure you have the following installed:
* Python 3.11.4 or higher
* pip (Python package installer)
* git 2.45 or higher

### Setting up
1. Clone the Repository and enter it (all the code should be run inside it)
`git clone https://github.com/Solomon795/insait_ecommerce_bot.git`
`cd insait_ecommerce_bot`
2. Create and activate a virtual environment (very preferably)
Create: `python -m venv venv` (or python3 depending on your installed python package, make sure that python added to PATH)
Activate: 
`venv\Scripts\activate` (Windows)
`source venv/bin/activate` (Linux-based)

3. Install all the dependencies in requirements.txt file:
`pip install -r requirements.txt`

4. Create your .env file with environmnent variables, including your openAI API key (make sure that it allows usage of gpt-3.5-turbo) and secret key for using Flask (feel free to type any you like, it's for session management):
`OPENAI_API_KEY=your_api_key_without_quotes`
`SECRET_KEY=your_key_without_quotes`

5. To run the app enter:
`python insait_my_app.py`
To access the web page of Flask app, go to localhost:5000

6. To run pytest (to make sure app runs correctly; optionally):
`pytest`

7. Evaluation (optional)
7.1 Accuracy and Response Relevance
The chatbot's performance can be evaluated using predefined dialogues (they should be in the same folder. Run the evaluation script (the flask app should be running at the same time! go to evaluation directory prior to running scripts!):
`python evaluation_accuracy_and_resp_relevance.py`

    Logs will be stored in ../logs/evaluation_accuracy_and_resp_relevance.log.

    7.2 User Satisfaction
    Analyze user satisfaction from the conversation history log (make sure there is one in 'insait_ecommerce_bot/logs/conversation_history.log', it's the path that hardcoded in script):
`python analyze_satisfaction.py`

    Logs will be stored in insait_ecommerce_bot/logs/evaluation_user_satisfaction.log.

## Functionalities
1) **Order Status**: When a user asks for the status of an order, the agent requests the order ID and responds with the order status from an orders CSV database.

2) **Request Human Representative**: Gathers contact information for users who prefer to interact with a human representative. This includes full name, email, and phone number. The information is saved to a CSV file in the same directory as the execution file.

3) **Return Policies**: Provides detailed information about return policies, including: general return policy (returns within 30 days with original receipt and condition), non-returnable items (clearance merchandise, perishable goods, and personal care items), refund process (issued to the original form of payment)

## Evaluation
The chatbot's performance is evaluated based on:

* Accuracy: correctness of responses compared to expected answers.
* Response Relevance: cosine similarity between generated and expected responses embeddings.
* User Satisfaction: Sentiment analysis of user messages.

## Contributing
Feel free to submit issues or pull requests if you have suggestions for improvements or new features.

## TO ADD
usage cases, improvent plans

## License
This project is open-source