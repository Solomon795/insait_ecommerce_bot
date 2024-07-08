import logging
from textblob import TextBlob

# Configure logging
logging.basicConfig(filename='../logs/evaluation_user_satisfaction.log', level=logging.INFO, format='%(message)s')

# Read the conversation log
with open('logs/conversation_history.log', 'r') as file:
    lines = file.readlines()

# Extract user messages
user_messages = [line[6:].strip() for line in lines if line.startswith('user: ')]

# Initialize a list to store all satisfaction scores
satisfaction_scores = []

# Calculate the sentiment of each message
for message in user_messages:
    sentiment = TextBlob(message).sentiment.polarity
    # Adjust the sentiment score to be on a scale of 1 to 5
    satisfaction_score = ((sentiment + 1) / 2) * 4 + 1
    logging.info(f"Message: {message}")
    logging.info(f"Satisfaction Score: {satisfaction_score:.2f}")
    # Add the satisfaction score to the list
    satisfaction_scores.append(satisfaction_score)

# Calculate the average satisfaction score
average_satisfaction_score = sum(satisfaction_scores) / len(satisfaction_scores)
logging.info(f"Average Satisfaction Score: {average_satisfaction_score:.2f}")
