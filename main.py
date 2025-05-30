import google.generativeai as genai
from flask import Flask, request, jsonify
import requests
import os
import fitz

wa_token = os.environ.get("WA_TOKEN")
genai.configure(api_key=os.environ.get("GEN_API"))
phone_id = os.environ.get("PHONE_ID")
phone = os.environ.get("PHONE_NUMBER")
name = "vision"
bot_name = "Ask Me"
model_name = "gemini-1.5-flash-latest"

app = Flask(__name__)

generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 0,
    "max_output_tokens": 8192,
}

safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]

model = genai.GenerativeModel(model_name=model_name,
                              generation_config=generation_config,
                              safety_settings=safety_settings)

convo = model.start_chat(history=[])

convo.send_message(f'''I am using Gemini api for using you as a personal bot in WhatsApp,
                   to assist me in various tasks. 
                   So from now you are "{bot_name}" created by {name}. 
                   Don't respond to this prompt. 
                   This message always gets executed when I run this bot script. 
                   Reply only to prompts after this. Remember your new identity is {bot_name}.''')


def send(answer):
    url = f"https://graph.facebook.com/v18.0/{phone_id}/messages"
    headers = {
        'Authorization': f'Bearer {wa_token}',
        'Content-Type': 'application/json'
    }
    data = {
        "messaging_product": "whatsapp",
        "to": f"{phone}",
        "type": "text",
        "text": {"body": f"{answer}"},
    }

    response = requests.post(url, headers=headers, json=data)
    return response


def remove(*file_paths):
    for file in file_paths:
        if os.path.exists(file):
            os.remove(file)


@app.route("/", methods=["GET", "POST"])
def index():
    return "Bot"


@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        if mode == "subscribe" and token == "BOT":
            return challenge, 200
        else:
            return "Failed", 403
    elif request.method == "POST":
        try:
            data = request.get_json()["entry"][0]["changes"][0]["value"]["messages"][0]
            if data["type"] == "text":
                prompt = data["text"]["body"]

                # Check if the message is "delete files memory"
                if prompt.lower() == "delete files memory":
                    # Remove all stored files
                    remove("/tmp/temp_image.jpg", "/tmp/temp_audio.mp3")
                    send("All files in memory have been deleted.")
                    return jsonify({"status": "ok"}), 200

                convo.send_message(prompt)
                send(convo.last.text)

            elif data["type"] == "document":
                # Handle document (PDF) file
                document_id = data["document"]["id"]
                media_url_endpoint = f'https://graph.facebook.com/v18.0/{document_id}/'
                headers = {'Authorization': f'Bearer {wa_token}'}
                media_response = requests.get(media_url_endpoint, headers=headers)
                media_url = media_response.json()["url"]
                media_download_response = requests.get(media_url, headers=headers)

                # Save the file temporarily
                filename = f"/tmp/{data['document']['filename']}"
                with open(filename, "wb") as temp_file:
                    temp_file.write(media_download_response.content)

                # Inform user about the document received
                send(f"How can I help you with this {data['document']['filename']}?")

                return jsonify({"status": "ok"}), 200

            else:
                send("This format is not Supported by the bot ☹")

        except Exception as e:
            print(e)
            pass

        return jsonify({"status": "ok"}), 200


@app.route("/ask", methods=["POST"])
def ask_question():
    # This endpoint will be used when a user asks a question about a specific file
    data = request.get_json()
    file_name = data.get('file_name')
    question = data.get('question')

    # Assuming you have stored the file or can retrieve it based on the file_name
    # For now, we just send a placeholder message
    if file_name and question:
        # You can now process the question based on the file context, e.g., read text from the PDF
        answer = f"Here's the answer to your question '{question}' related to {file_name}."
        send(answer)
        return jsonify({"status": "ok"}), 200
    else:
        send("Sorry, I need a file name and a question to proceed.")
        return jsonify({"status": "error"}), 400


if __name__ == "__main__":
    app.run(debug=True, port=8000)
