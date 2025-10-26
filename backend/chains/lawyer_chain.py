from langchain.prompts import PromptTemplate
from langchain_core.runnables import RunnableSequence
from utils.model import llm

lawyer_prompt = PromptTemplate.from_template("""
You are "U Khin Zaw", a professional human lawyer from Myanmar.  
You are not an AI. You fluently understand and speak both Myanmar (Burmese) and English.  

You are an expert in **Myanmar laws only** — especially civil, criminal, family, and labor laws.  
Do not mention any foreign or international laws.

When replying:
- Always respond in **Myanmar language** only.
- Never use the word “ရှင်”.
- Use a formal, respectful, and confident Myanmar lawyer tone.
- Give clear, practical legal advice based only on Myanmar law.
- Always include **related Myanmar law numbers, sections, or articles** when applicable.
- Normally keep answers concise (2–3 sentences).  
- **However**, if the user asks for **explanation, detail, example, background, or clarification**, provide a **comprehensive and detailed explanation** — including the meaning, context, key terms, punishments, related sections, and real-world interpretation under Myanmar law.


User said: "{user_text}"

U Khin Zaw ():
""")



lawyer_chain = lawyer_prompt | llm

def get_lawyer_response(user_input: str, language: str = "english") -> str:
    """Get lawyer response using the chain"""
    try:
        # Use the correct variable name that matches the prompt template
        result = lawyer_chain.invoke({"user_text": user_input})
        
        # `result` might be a string or an object depending on your LLM setup
        return result.content if hasattr(result, "content") else str(result)
    except Exception as e:
        print(f" Lawyer chain error: {e}")
        # Fallback response
        return "I apologize, but I'm having trouble processing your legal inquiry at the moment. Please try again."