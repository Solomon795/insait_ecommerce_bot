import json
import requests
import logging
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# Configure logging
logging.basicConfig(filename='../logs/evaluation_accuracy_and_resp_relevance.log', level=logging.INFO, format='%(message)s')

# Load the test cases
with open('predefined_dialogues_for_evaluation.json', 'r') as file:
    test_cases = json.load(file)

correct_responses = 0
total_responses = 0
relevance_scores = []

# URLs of your Flask app
url = "http://127.0.0.1:5000/get"
reset_url = "http://127.0.0.1:5000/reset"

# Create a session object
s = requests.Session()

# Initialize the sentence transformer model
model = SentenceTransformer('all-MiniLM-L6-v2')

def get_embeddings(text):
    # Get the embeddings of the text
    return model.encode([text])

def calculate_relevance(original_answer, generated_answer):
    # Get the embeddings of the original answer and the generated answer
    original_answer_embedding = get_embeddings(original_answer)
    generated_answer_embedding = get_embeddings(generated_answer)
    # Calculate the cosine similarity
    return cosine_similarity(original_answer_embedding, generated_answer_embedding)[0][0]

# Iterate over the test cases
for i, test_case in enumerate(test_cases):
    logging.info(f"Processing test dialogue {i + 1}/{len(test_cases)}")
    interactions = len(test_case['dialogue']) // 2
    for j in range(interactions):
        logging.info(f"Interaction {j + 1}/{interactions}")

        # User turn
        user_turn = test_case['dialogue'][j * 2]
        user_text = user_turn['content']
        logging.info(f" User: {user_text}")
        # Make a GET request to the Flask app using the session object
        response = s.get(url, params={'msg': user_text})
        bot_response = response.text.strip()
        logging.info(f" Bot response: {bot_response}")

        # Assistant turn
        assistant_turn = test_case['dialogue'][j * 2 + 1]
        expected_response = assistant_turn['content']
        logging.info(f"Expected response: {expected_response}")
        # Compare the bot's response to the expected response
        if bot_response == expected_response:
            correct_responses += 1
            logging.info("Correct response")
        else:
            logging.info("Incorrect response")
        total_responses += 1
        # Calculate the relevance score
        relevance_score = calculate_relevance(expected_response, bot_response)
        relevance_scores.append(relevance_score)

    # Reset the session after each dialogue
    s.get(reset_url)
    logging.info("Session reset\n")

# Calculate the accuracy and the average relevance score
accuracy = correct_responses / total_responses if total_responses > 0 else 0
average_relevance_score = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0
logging.info(f'Accuracy: {accuracy * 100:.0f}%')
logging.info(f'Average Relevance Score: {average_relevance_score:.2f}')
