from flask import Blueprint, request, jsonify
import edge_tts
import asyncio
import os
import uuid
import glob
from datetime import datetime, timedelta
import traceback
from langchain.prompts import PromptTemplate
from utils.model import llm

doctor_call_bp = Blueprint('doctor_call', __name__, url_prefix='/doctor')

# Voice options - Fixed with correct voice names
VOICE_OPTIONS = {
    'default': 'en-US-ChristopherNeural',      # Male voice 1
    'male2': 'en-US-EricNeural',               # Male voice 2  
    'male3': 'en-US-GuyNeural'                 # Male voice 3
}

SPEED_OPTIONS = {
    "slow": "-30%",
    "normal": "+0%", 
    "fast": "+30%"
}

# Doctor Chain - Integrated into same file
doctor_prompt = PromptTemplate.from_template("""
You are "Dr.Kyaw", a highly experienced and compassionate medical doctor (not an AI). You are male.
You can fluently understand and speak English.

When replying:
-If the user's message is only a greeting, thanks, goodbye, or otherwise contains no health symptoms or medical questions, reply with a short friendly greeting (1 sentence) and do NOT suggest diagnoses or medicines.                                             
- Use a caring, confident tone like a real doctor talking to a patient.
- Keep your reply **clear, accurate, and under 60 words**.
- Ask short follow-up questions if needed.
- When possible, **prescribe common over-the-counter medicine** or safe home remedies.
- Give practical advice on **what to eat and what to avoid**, if relevant.
- If the problem is serious, calmly suggest seeing a real doctor or going to a clinic.

Format:
1. Identify the likely cause briefly.
2. Suggest treatment or medicine.
3. Mention what to eat or avoid (if necessary).
4. End with gentle encouragement.

Always reply naturally and human-like — never robotic.

User said: "{text}",always replay with english,
Dr. Health:
""")

# Create doctor chain
doctor_chain = doctor_prompt | llm

def get_doctor_response(user_input: str) -> str:
    """Get response from doctor chain"""
    try:
        result = doctor_chain.invoke({"text": user_input})
        return result.content if hasattr(result, "content") else str(result)
    except Exception as e:
        print(f" Doctor chain error: {e}")
        return "I apologize, but I'm having trouble processing your request. Please try again."

def get_audio_dir():
    """Get audio directory path"""
    base_dir = os.path.dirname(__file__)
    audio_dir = os.path.join(base_dir, '../../frontend/static/audio/doctor')
    return os.path.abspath(audio_dir)

def delete_old_audio_files(hours=12):
    """Delete old audio files"""
    try:
        audio_dir = get_audio_dir()
        if not os.path.exists(audio_dir):
            return True
            
        cutoff = datetime.now() - timedelta(hours=hours)
        for filepath in glob.glob(os.path.join(audio_dir, '*.mp3')):
            try:
                if datetime.fromtimestamp(os.path.getmtime(filepath)) < cutoff:
                    os.remove(filepath)
                    print(f" Deleted old file: {os.path.basename(filepath)}")
            except Exception as e:
                print(f" Error deleting file: {e}")
        return True
    except Exception as e:
        print(f" Error in delete_old_audio_files: {e}")
        return False

def run_async_in_thread(coro):
    """Run async function in thread"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    except Exception as e:
        print(f" Async error: {e}")
        return None
    finally:
        loop.close()

async def generate_speech(text: str, voice_type: str = "default", speed: str = "normal") -> str:
    """Generate speech audio"""
    try:
        if not text or not text.strip():
            print(" Empty text for TTS")
            return None
            
        audio_dir = get_audio_dir()
        os.makedirs(audio_dir, exist_ok=True)
        
        # Clean old files
        delete_old_audio_files(hours=12)

        filename = f"doctor_{uuid.uuid4().hex}.mp3"
        filepath = os.path.join(audio_dir, filename)

        # Get voice
        voice = VOICE_OPTIONS.get(voice_type)
        if not voice:
            print(f" Voice type '{voice_type}' not found, using default")
            voice = VOICE_OPTIONS["default"]
        
        # Get speed rate
        rate = SPEED_OPTIONS.get(speed, SPEED_OPTIONS["normal"])

        print(f" TTS Generating - Voice Type: {voice_type}, Voice: {voice}, Speed: {rate}")
        print(f" TTS Text: {text[:100]}...")

        # Generate speech
        communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate)
        await asyncio.wait_for(communicate.save(filepath), timeout=30)

        # Check if file was created
        if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
            audio_url = f"/static/audio/doctor/{filename}"
            print(f" TTS Success: {audio_url}")
            return audio_url
        else:
            print(" TTS Failed: File not created or empty")
            return None
            
    except asyncio.TimeoutError:
        print(" TTS Timeout")
        return None
    except Exception as e:
        print(f" TTS Error: {e}")
        traceback.print_exc()
        return None

@doctor_call_bp.route('/call', methods=['POST'])
def voice_consultation():
    """Main voice call endpoint"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"text": "No data received", "audio": None, "status": "error"}), 400
            
        message = data.get("message", "").strip()
        voice_type = data.get("voice", "default")
        speed = data.get("speed", "normal")

        print(f" CALL Request - Voice: {voice_type}, Speed: {speed}")
        print(f" Message: {message}")

        if not message:
            return jsonify({"text": "Please provide a message", "audio": None, "status": "error"})

        # Get AI response from integrated doctor chain
        response_text = get_doctor_response(message)
        
        if not response_text.strip():
            # Fallback responses based on voice type
            if voice_type == "myanmar":
                response_text = "ကျေးဇူးပြု၍ သင့်ရောဂါလက္ခဏာများကိုဖော်ပြပါ။"
            else:
                response_text = "I am here to help. Please describe your symptoms."

        print(f" AI Response: {response_text}")

        # Generate audio with selected voice and speed
        audio_url = run_async_in_thread(generate_speech(response_text, voice_type=voice_type, speed=speed))

        print(f" CALL Response - Audio URL: {audio_url}")

        return jsonify({
            "text": response_text,
            "audio": audio_url,
            "status": "success",
            "voice_used": voice_type,
            "speed_used": speed
        })

    except Exception as e:
        print(f" CALL Endpoint error: {e}")
        traceback.print_exc()
        return jsonify({
            "text": "Technical error occurred. Please try again.",
            "audio": None,
            "status": "error",
            "error": str(e)
        }), 500

# Test endpoint to check available voices
@doctor_call_bp.route('/test-voices', methods=['GET'])
def test_voices():
    """Test endpoint to check if voices work"""
    test_text = "Hello, this is a test of different voices."
    results = {}
    
    for voice_name, voice_code in VOICE_OPTIONS.items():
        try:
            audio_url = run_async_in_thread(generate_speech(test_text, voice_type=voice_name, speed="normal"))
            results[voice_name] = {
                "voice_code": voice_code,
                "audio_url": audio_url,
                "status": "success" if audio_url else "failed"
            }
            print(f" Tested {voice_name}: {voice_code} - {'Success' if audio_url else 'Failed'}")
        except Exception as e:
            results[voice_name] = {
                "voice_code": voice_code,
                "error": str(e),
                "status": "error"
            }
            print(f" Error testing {voice_name}: {e}")
    
    return jsonify(results)

# Clean audio endpoint
@doctor_call_bp.route('/clean-audio', methods=['POST'])
def clean_audio():
    """Clean all audio files"""
    try:
        audio_dir = get_audio_dir()
        if os.path.exists(audio_dir):
            for file in os.listdir(audio_dir):
                if file.endswith('.mp3'):
                    os.remove(os.path.join(audio_dir, file))
        return jsonify({"status": "success", "message": "Audio files cleaned"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

# Test doctor chain endpoint
@doctor_call_bp.route('/test-chain', methods=['POST'])
def test_doctor_chain():
    """Test the doctor chain directly"""
    try:
        data = request.get_json()
        message = data.get("message", "").strip()
        
        if not message:
            return jsonify({"error": "No message provided"}), 400
            
        response_text = get_doctor_response(message)
        
        return jsonify({
            "status": "success",
            "user_message": message,
            "doctor_response": response_text
        })
        
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500