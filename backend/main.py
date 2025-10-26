from flask import Flask, render_template, request, jsonify, send_from_directory
from dotenv import load_dotenv
import os

from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import LLMChain

# Load environment variables
load_dotenv()
google_api_key = os.getenv("GOOGLE_API_KEY")

# Setup Flask app
app = Flask(__name__, static_folder='../fondend', static_url_path='', template_folder='../fondend/templates')

# Setup Gemini model
llm = ChatGoogleGenerativeAI(
   model="models/gemini-2.5-flash",
   google_api_key=google_api_key,
   temperature=0.05
)

# --------------------------
# English Teacher AI Setup
# --------------------------
english_prompt = PromptTemplate.from_template("""
You are an English teacher AI named Aye Mya Sabal. You only understand and respond in English.
You do not know math, programming, or other subjects.
You answer the user's questions about English and also ask questions to help them practice English.
User said: "{text}", respond in English with a maximum of 20 words.
Your response:
""")
english_chain = LLMChain(llm=llm, prompt=english_prompt, verbose=True)

# --------------------------
# Doctor AI Setup
# --------------------------
doctor_prompt = PromptTemplate.from_template("""
You are a professional doctor AI named Dr. Health. You only understand and respond in English.
You provide helpful, concise medical advice based on user questions.
User said: "{text}", respond in English with a maximum of 30 words.
Your response:
""")
doctor_chain = LLMChain(llm=llm, prompt=doctor_prompt, verbose=True)

# --------------------------
# Lawyer AI Setup
# --------------------------
lawyer_prompt = PromptTemplate.from_template("""
You are a professional lawyer AI named Legal Aid. You only understand and respond in English.
You provide helpful, concise legal advice based on user questions.
User said: "{text}", respond in English with a maximum of 30 words.
Your response:
""")
lawyer_chain = LLMChain(llm=llm, prompt=lawyer_prompt, verbose=True)

# --------------------------
# Translator AI Setup
# --------------------------
translator_prompt = PromptTemplate.from_template("""
You are a professional translator. Detect whether the input "{text}" is in English or Myanmar (Burmese), and translate it into the other language.

- If the input is in English, translate it into natural, fluent Myanmar (Burmese).
- If the input is in Myanmar (Burmese), translate it into natural, fluent English.
- Only provide the translated output. Do not include the original or any explanations.
""")
translator_chain = LLMChain(llm=llm, prompt=translator_prompt, verbose=True)

# --------------------------
# Routes
# --------------------------

@app.route('/')
# def home():
#     return render_template('index.html')

@app.route('/english')
def english_page():
    return render_template('englishTr.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_text = data.get("message", "").strip() if data else ""
    if not user_text:
        return jsonify({"reply": "Please send a message."})

    result = english_chain.invoke({"text": user_text})
    return jsonify({"reply": result.get("text", "AI has no response.")})



@app.route('/doctor')
def doctor_page():
    return render_template('doctor.html')

@app.route('/doctorchat', methods=['POST'])
def doctor_chat():
    data = request.get_json()
    user_text = data.get("message", "").strip() if data else ""
    if not user_text:
        return jsonify({"reply": "Please send a message."})

    result = doctor_chain.invoke({"text": user_text})
    return jsonify({"reply": result.get("text", "Doctor AI has no response.")})



@app.route('/lawer') 
def lawyer_page():
    return render_template('lawer.html')  

@app.route('/lawerchat', methods=['POST'])
def lawyer_chat():
    data = request.get_json()
    user_text = data.get("message", "").strip() if data else ""
    if not user_text:
        return jsonify({"reply": "Please send a message."})

    result = lawyer_chain.invoke({"text": user_text})
    return jsonify({"reply": result.get("text", "Lawer AI has no response.")})





@app.route('/translate', methods=['GET', 'POST'])
def translate():
    translated_text = ""
    if request.method == 'POST':
        text = request.form.get('text')
        if text:
            result = translator_chain.invoke({"text": text})
            translated_text = result['text']
    return render_template('translate.html', translate=translated_text)

# Route to show image
@app.route('/image/<path:filename>')
def serve_image(filename):
    return send_from_directory('../fondend/image', filename)

# --------------------------
# Start the server
# --------------------------
if __name__ == '__main__':
    app.run(debug=True)
