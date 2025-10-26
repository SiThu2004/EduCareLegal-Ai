from langchain.prompts import PromptTemplate
from langchain_core.runnables import RunnableSequence
from utils.model import llm

vocabulary_prompt = PromptTemplate.from_template("""
You are a professional English to Burmese dictionary. For the English word "{word}", provide a comprehensive vocabulary entry in JSON format.

Return ONLY valid JSON with this exact structure:
{{
    "word": "{word}",
    "part_of_speech": "noun/verb/adjective/adverb/etc",
    "burmese": "Burmese translation",
    "definition": {{
        "english": "English definition",
        "burmese": "Burmese translation of the definition"
    }},
    "examples": [
        {{
            "english": "Example sentence 1 in English",
            "burmese_translation": "Burmese translation of example sentence 1"
        }},
        {{
            "english": "Example sentence 2 in English", 
            "burmese_translation": "Burmese translation of example sentence 2"
        }},
        {{
            "english": "Example sentence 3 in English",
            "burmese_translation": "Burmese translation of example sentence 3"
        }}
    ]
}}

Requirements:
1. part_of_speech must be one of: noun, verb, adjective, adverb, preposition, conjunction, interjection
2. burmese must be the accurate Burmese translation of the word
3. definition.english must be clear and concise English definition
4. definition.burmese must be accurate Burmese translation of the definition
5. examples must contain 3 different natural sentences showing different usage contexts
6. Each example must have both English sentence and accurate Burmese translation
7. Use natural, conversational Burmese translations for both definitions and examples
8. Ensure all Burmese text is properly encoded

Example response for word "hello":
{{
    "word": "hello",
    "part_of_speech": "interjection",
    "burmese": "မင်္ဂလာပါ",
    "definition": {{
        "english": "A greeting used when meeting someone or starting a conversation",
        "burmese": "တစ်စုံတစ်ယောက်ကို တွေ့ရှိချိန် သို့မဟုတ် စကားစပြောချိန်တွင် အသုံးပြုသော နှုတ်ဆက်စကား"
    }},
    "examples": [
        {{
            "english": "Hello, how are you today?",
            "burmese_translation": "မင်္ဂလာပါ၊ ဒီနေ့ နေကောင်းရဲ့လား?"
        }},
        {{
            "english": "She said hello to everyone in the room.",
            "burmese_translation": "သူမက အခန်းထဲက လူတိုင်းကို မင်္ဂလာပါလို့ ပြောတယ်။"
        }},
        {{
            "english": "Hello! It's good to see you again.",
            "burmese_translation": "မင်္ဂလာပါ! သင့်ကိုပြန်တွေ့ရတာ ဝမ်းသာပါတယ်။"
        }}
    ]
}}


Now process the word: "{word}"
""")

vocabulary_chain = vocabulary_prompt | llm