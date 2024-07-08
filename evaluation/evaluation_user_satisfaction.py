import logging
from textblob import TextBlob
import re

# Configure logging
logging.basicConfig(filename='../logs/evaluation_user_satisfaction.log', level=logging.INFO, format='%(message)s')

# Read the conversation log
with open('../logs/conversation_history.log', 'r') as file:
    lines = file.readlines()

# Initialize a list to store all satisfaction scores
satisfaction_scores = []

# Regular expression pattern for lines with 'user: ' after a timestamp
pattern = re.compile(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}: user: ')

# Extract user messages and calculate sentiment
for line in lines:
    # Check if the line matches the pattern
    if pattern.match(line):
        # Extract the message content (remove the timestamp and 'user: ' prefix)
        message = re.sub(r'.+?user: ', '', line).strip()
        # Calculate the sentiment of the message
        sentiment = TextBlob(message).sentiment.polarity
        # Adjust the sentiment score to be on a scale of 1 to 5
        satisfaction_score = ((sentiment + 1) / 2) * 4 + 1
        # Log the user message and its satisfaction score
        logging.info(f"Message: {message}")
        logging.info(f"Satisfaction Score: {satisfaction_score:.2f} / 5.0\n")
        # Add the satisfaction score to the list
        satisfaction_scores.append(satisfaction_score)

# Calculate the average satisfaction score
if satisfaction_scores:
    average_satisfaction_score = sum(satisfaction_scores) / len(satisfaction_scores)
    logging.info(f"Average Satisfaction Score: {average_satisfaction_score:.2f} / 5.0")
else:
    logging.info("No user messages found in the conversation history.")
