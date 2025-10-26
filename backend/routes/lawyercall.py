

from flask import Blueprint, request, jsonify
import edge_tts
import asyncio
import os
import uuid
import glob
import re
from datetime import datetime, timedelta
import traceback
from utils.model import llm  


lawyer_call_bp = Blueprint('lawyer_call', __name__, url_prefix='/lawyer-call') 


VOICE_OPTIONS = {
    'default': 'en-US-ChristopherNeural',
    'male2': 'en-US-EricNeural',
    'male3': 'en-US-GuyNeural'
}

SPEED_OPTIONS = {
    "slow": "-30%",
    "normal": "+0%",
    "fast": "+30%"
}


STANDALONE_LAWYER_PROMPT = """
[STRICT INSTRUCTION: YOU MUST RESPOND IN ENGLISH ONLY. NEVER USE MYANMAR/BURMESE LANGUAGE OR SCRIPT.]

You are U Khin Zaw, a professional Myanmar lawyer specializing in Myanmar laws.

STRICT RULES:
1. LANGUAGE: RESPOND IN ENGLISH ONLY - ABSOLUTELY NO MYANMAR CHARACTERS
2. CONTENT: Base advice ONLY on Myanmar laws (civil, criminal, family, labor)
3. LENGTH: Keep responses concise (2-3 sentences) by default, but expand only if needed to explain something clearly.
4. TONE: Formal and professional
5. SCOPE: Do not discuss foreign or international laws
6. LIMITATION: For complex cases, recommend consulting licensed Myanmar attorney

If you cannot follow these rules, respond with: "I recommend consulting a licensed Myanmar attorney for proper legal advice."

User's legal question: {user_input}, response with english,dont tell me this,

U Khin Zaw (English response):
"""


def strict_english_enforcer(text: str) -> str:
    """STRICTER filter - BLOCK ANY Myanmar text completely"""
    if not text or not text.strip():
        return "Please describe your legal issue in English."
    
    # Detect Myanmar Unicode range (1000-109F)
    myanmar_pattern = re.compile(r'[\u1000-\u109F]')
    if myanmar_pattern.search(text):
        print(f" BLOCKED: Myanmar script detected")
        return "I provide legal advice in English only. Please consult a licensed Myanmar attorney."
    
    # Block any non-ASCII characters that might be other languages
    non_english_pattern = re.compile(r'[^\x00-\x7F]')
    non_english_chars = non_english_pattern.findall(text)
    if non_english_chars:
        print(f" BLOCKED: Non-English characters detected: {non_english_chars}")
        return "I provide legal advice in English only. Please consult a licensed Myanmar attorney."
    
    return text.strip()


def get_standalone_lawyer_response(user_input: str) -> str:
    """COMPLETELY STANDALONE - NO CHAIN, NO LANGCHAIN DEPENDENCY"""
    try:
        # Create prompt directly - NO CHAIN
        prompt = STANDALONE_LAWYER_PROMPT.format(user_input=user_input)
        
        print(f"🔒 STANDALONE - Sending prompt to LLM...")
        
        # Call LLM directly - NO CHAIN
        result = llm.invoke(prompt)
        response = result.content if hasattr(result, "content") else str(result)
        
        print(f"🧾 STANDALONE - LLM Raw Output: {response}")
        
       
        response = strict_english_enforcer(response)
        
        
        if len(response.split()) < 3:
            response = "Based on Myanmar law, I recommend consulting a licensed attorney for proper legal advice regarding your specific situation."
        
        print(f" STANDALONE - Final Response: {response}")
        return response

    except Exception as e:
        print(f" STANDALONE - get_standalone_lawyer_response error: {e}")
        traceback.print_exc()
        return "I apologize for the technical issue. Please consult a licensed Myanmar attorney for legal advice."


def get_audio_dir():
    base_dir = os.path.dirname(__file__)
    audio_dir = os.path.join(base_dir, '../../frontend/static/audio/lawyer')
    os.makedirs(audio_dir, exist_ok=True)
    return os.path.abspath(audio_dir)

def delete_old_audio_files(hours=12):
    try:
        audio_dir = get_audio_dir()
        cutoff = datetime.now() - timedelta(hours=hours)
        for f in glob.glob(os.path.join(audio_dir, '*.mp3')):
            if datetime.fromtimestamp(os.path.getmtime(f)) < cutoff:
                os.remove(f)
                print(f" Deleted old: {os.path.basename(f)}")
        return True
    except Exception as e:
        print(f" delete_old_audio_files error: {e}")
        return False

def run_async_in_thread(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

async def generate_speech(text: str, voice_type="default", speed="normal") -> str:
    try:
        if not text.strip():
            return None

        delete_old_audio_files()
        audio_dir = get_audio_dir()
        filename = f"lawyer_{uuid.uuid4().hex}.mp3"
        filepath = os.path.join(audio_dir, filename)

        voice = VOICE_OPTIONS.get(voice_type, VOICE_OPTIONS["default"])
        rate = SPEED_OPTIONS.get(speed, SPEED_OPTIONS["normal"])

        print(f" Generating voice ({voice_type}, {speed})...")
        communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate)
        await asyncio.wait_for(communicate.save(filepath), timeout=30)

        if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
            return f"/static/audio/lawyer/{filename}"
        else:
            print(" Empty TTS file created")
            return None

    except asyncio.TimeoutError:
        print("❌ TTS Timeout after 30s")
        return None
    except Exception as e:
        print(f" TTS Error: {e}")
        traceback.print_exc()
        return None


@lawyer_call_bp.route('/call', methods=['POST'])
def voice_consultation():
    try:
        data = request.get_json() or {}
        message = data.get("message", "").strip()
        voice = data.get("voice", "default")
        speed = data.get("speed", "normal")

        print(f" STANDALONE LAWYER CALL — message: {message}")

        if not message:
            return jsonify({
                "text": "Please describe your legal issue in English.",
                "audio": None,
                "status": "error"
            })

        # USE STANDALONE FUNCTION - NO CHAIN
        response_text = get_standalone_lawyer_response(message)
        audio_url = run_async_in_thread(generate_speech(response_text, voice, speed))

        return jsonify({
            "text": response_text,
            "audio": audio_url,
            "status": "success",
            "voice_used": voice,
            "speed_used": speed
        })

    except Exception as e:
        print(f" voice_consultation error: {e}")
        traceback.print_exc()
        return jsonify({
            "text": "Technical error occurred. Please try again.",
            "status": "error",
            "error": str(e)
        }), 500

# ==============================
# Test Endpoints - STANDALONE
# ==============================
@lawyer_call_bp.route('/test-standalone', methods=['POST'])
def test_standalone():
    """Test the completely standalone system"""
    try:
        data = request.get_json() or {}
        msg = data.get("message", "What are my rights as a tenant in Myanmar?").strip()
        
        print(" Testing COMPLETELY STANDALONE system...")
        response = get_standalone_lawyer_response(msg)
        
        # Check for Myanmar characters
        myanmar_detected = bool(re.search(r'[\u1000-\u109F]', response))
        
        return jsonify({
            "user_input": msg,
            "response": response,
            "myanmar_detected": myanmar_detected,
            "length": len(response),
            "word_count": len(response.split()),
            "system": "STANDALONE"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@lawyer_call_bp.route('/clean-audio', methods=['POST'])
def clean_audio():
    try:
        audio_dir = get_audio_dir()
        deleted = 0
        for f in os.listdir(audio_dir):
            if f.endswith(".mp3"):
                os.remove(os.path.join(audio_dir, f))
                deleted += 1
        return jsonify({"status": "success", "message": f"Deleted {deleted} files"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@lawyer_call_bp.route('/test-voices', methods=['GET'])
def test_voices():
    test_text = "Hello, this is U Khin Zaw testing the standalone lawyer voice system."
    results = {}
    for name, code in VOICE_OPTIONS.items():
        try:
            audio_url = run_async_in_thread(generate_speech(test_text, name, "normal"))
            results[name] = {
                "voice_code": code,
                "audio_url": audio_url,
                "status": "success" if audio_url else "failed"
            }
        except Exception as e:
            results[name] = {"error": str(e), "status": "error"}
    return jsonify(results)


@lawyer_call_bp.route('/debug-info', methods=['GET'])
def debug_info():
    """Debug endpoint to check system status"""
    return jsonify({
        "system": "STANDALONE_LAWYERCALL",
        "status": "active", 
        "llm_connected": llm is not None,
        "voices_available": list(VOICE_OPTIONS.keys()),
        "speeds_available": list(SPEED_OPTIONS.keys()),
        "dependency": "NONE - COMPLETELY STANDALONE"
    })