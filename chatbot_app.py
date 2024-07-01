from flask import Flask, render_template, request
import openai

app = Flask(__name__)

openai.api_key = 'sk-proj-GIgdojeDb0v81JFVk6RST3BlbkFJtAtcCLVbUhcBKz4ja8iD'

client = openai.OpenAI(api_key=openai.api_key)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/get")
def get_bot_response():
    user_text = request.args.get('msg')
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