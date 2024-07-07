import json
import requests
import logging

# Configure logging
logging.basicConfig(filename='evaluation.log', level=logging.INFO, format='%(message)s')

# Load the test cases
with open('predefined_dialogues_for_evaluation.json', 'r') as file:
    test_cases = json.load(file)

correct_responses = 0
total_responses = 0

# URLs of your Flask app
url = "http://127.0.0.1:5000/get"
reset_url = "http://127.0.0.1:5000/reset"

# Create a session object
s = requests.Session()

# Iterate over the test cases
for i, test_case in enumerate(test_cases):
    logging.info(f"Processing test case {i + 1}/{len(test_cases)}")
    for j, turn in enumerate(test_case['dialogue']):
        logging.info(f"Turn {j + 1}/{len(test_case['dialogue'])}")

        # User turn
        if turn['role'] == 'user':
            user_text = turn['content']
            logging.info(f"User: {user_text}")
            # Make a GET request to the Flask app using the session object
            response = s.get(url, params={'msg': user_text})
            bot_response = response.text.strip()
            logging.info(f"Bot response: {bot_response}")
        # Assistant turn
        else:
            expected_response = turn['content']
            logging.info(f"Expected response: {expected_response}")
            # Compare the bot's response to the expected response
            if bot_response == expected_response:
                correct_responses += 1
                logging.info("Correct response")
            else:
                logging.info("Incorrect response")
            total_responses += 1

    # Reset the session after each dialogue
    s.get(reset_url)
    logging.info("Session reset\n")

# Calculate the accuracy
accuracy = correct_responses / total_responses if total_responses > 0 else 0
logging.info(f'Accuracy: {accuracy * 100}%')
