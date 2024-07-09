import logging
from textblob import TextBlob
import re


def configure_logging():
    """
    Configures logging settings for evaluating user satisfaction.
    """
    logging.basicConfig(filename='../logs/evaluation_user_satisfaction.log', level=logging.INFO, format='%(message)s')


def read_conversation_log(file_path):
    """
    Reads the conversation log from a specified file path.

    Args:
        file_path (str): The path to the conversation log file.

    Returns:
        list: A list of lines read from the conversation log file.
    """
    with open(file_path, 'r') as file:
        lines = file.readlines()
    return lines


def extract_and_evaluate_sentiment(lines):
    """
    Extracts user messages from the conversation log, evaluates sentiment,
    calculates satisfaction scores, and logs the results.

    Args:
        lines (list): A list of lines from the conversation log.
    """
    satisfaction_scores = []
    pattern = re.compile(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}: user: ')

    for line in lines:
        if pattern.match(line):
            message = re.sub(r'.+?user: ', '', line).strip()
            sentiment = TextBlob(message).sentiment.polarity
            satisfaction_score = ((sentiment + 1) / 2) * 4 + 1

            # Log message and satisfaction score
            logging.info(f"Message: {message}")
            logging.info(f"Satisfaction Score: {satisfaction_score:.2f} / 5.0\n")

            satisfaction_scores.append(satisfaction_score)

    return satisfaction_scores


def calculate_average_satisfaction(satisfaction_scores):
    """
    Calculates the average satisfaction score from a list of scores.

    Args:
        satisfaction_scores (list): A list of satisfaction scores.

    Returns:
        float: The average satisfaction score.
    """
    if satisfaction_scores:
        average_satisfaction_score = sum(satisfaction_scores) / len(satisfaction_scores)
        logging.info(f"Average Satisfaction Score: {average_satisfaction_score:.2f} / 5.0")
        return average_satisfaction_score
    else:
        logging.info("No user messages found in the conversation history.")
        return None


if __name__ == "__main__":
    configure_logging()
    conversation_log_path = '../logs/conversation_history.log'
    conversation_lines = read_conversation_log(conversation_log_path)
    satisfaction_scores = extract_and_evaluate_sentiment(conversation_lines)
    calculate_average_satisfaction(satisfaction_scores)
