from langchain.prompts import PromptTemplate
from langchain_core.runnables import RunnableSequence
from utils.model import llm

translator_prompt = PromptTemplate.from_template("""
You are a professional translator. Detect whether the input "{text}" is in English or Myanmar (Burmese), and translate it into the other language.

- If the input is in English, translate it into natural, fluent Myanmar (Burmese).
- If the input is in Myanmar (Burmese), translate it into natural, fluent English.
- Only provide the translated output. Do not include the original or any explanations.
""")

translator_chain = translator_prompt | llm
