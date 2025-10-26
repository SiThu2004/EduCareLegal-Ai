from dotenv import load_dotenv
import os
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()
google_api_key = os.getenv("GOOGLE_API_KEY")

llm = ChatGoogleGenerativeAI(
    model="models/gemini-2.5-flash-lite", 
    google_api_key=google_api_key,
    temperature=0.2,
     convert_system_message_to_human=True
)


# from google import generativeai as genai
# genai.configure(api_key=google_api_key)

# models = genai.list_models()
# for m in models:
#     print(m.name)
