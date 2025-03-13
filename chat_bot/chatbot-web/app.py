import os
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from anthropic import Anthropic
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get API key securely
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    raise ValueError("Anthropic API key not found! Set ANTHROPIC_API_KEY in .env or environment variables.")

# Initialize the Anthropic client
client = Anthropic(api_key=ANTHROPIC_API_KEY)

app = Flask(__name__)
CORS(app)  # Enable CORS

#trial
conversation = []  # Store the chat history

@app.route("/")
def home():
    """Render the chatbot UI."""
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    """Handle user messages and return chatbot responses."""
    global conversation
    
    if not request.is_json:
        return jsonify({"reply": "Invalid request format"}), 400
        
    user_input = request.json.get("message", "").strip()

    if not user_input:
        return jsonify({"reply": "Please enter a valid message."}), 400

    conversation.append({"role": "user", "content": user_input})

    try:
        stream = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1000,
            messages=conversation,
            stream=True
        )

        assistant_response = ""
        for chunk in stream:
            if chunk.type == "content_block_delta":
                assistant_response += chunk.delta.text

        if not assistant_response:
            return jsonify({"reply": "No response from assistant"}), 500

        conversation.append({"role": "assistant", "content": assistant_response})
        return jsonify({"reply": assistant_response})

    except Exception as e:
        print(f"Error: {str(e)}")  # For debugging
        return jsonify({"reply": "An error occurred while processing your request"}), 500

if __name__ == "__main__":
    app.run(debug=True)
