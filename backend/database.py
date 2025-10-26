# backend/database.py
from pymongo import MongoClient
from dotenv import load_dotenv
import os

mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
client = MongoClient(mongo_uri)
db = client['chatbotDB']
users_collection = db['chatbotDB']