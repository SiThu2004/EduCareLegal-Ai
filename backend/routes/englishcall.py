from flask import Blueprint, request, jsonify
import edge_tts
import asyncio
import os
import uuid
import glob
from datetime import datetime, timedelta
from functools import lru_cache

english_call_bp = Blueprint('english_call', __name__, url_prefix='/english')


VOICE_OPTIONS = {
    'default': 'en-US-JennyNeural',
    'female2': 'en-US-AriaNeural',
    'female3': 'en-US-AnaNeural',
    'female4': 'en-US-AshleyNeural',
    'female5': 'en-US-MichelleNeural',
    'female6': 'en-US-SaraNeural',
}

# Speed options
SPEED_OPTIONS = {
    'slow': '-30%',
    'normal': '+0%',
    'fast': '+30%'
}

def get_audio_dir():
    """Get the audio directory path"""
    return os.path.join(os.path.dirname(__file__), '../../frontend/static/audio/english') #change

def delete_old_audio_files(hours=0):
    """Delete audio files older than specified hours"""
    try:
        audio_dir = get_audio_dir()
        os.makedirs(audio_dir, exist_ok=True)
        
        now = datetime.now()
        cutoff = now - timedelta(hours=hours)
        
        for filepath in glob.glob(os.path.join(audio_dir, '*.mp3')):
            try:
                file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                if file_time < cutoff:
                    os.remove(filepath)
                    print(f"Deleted old audio file: {filepath}")
            except Exception as e:
                print(f"Error deleting file {filepath}: {e}")
        return True
    except Exception as e:
        print(f"Error in audio deletion: {e}")
        return False

@lru_cache(maxsize=1)
def get_english_chain():
    """Cache the AI chain to avoid reinitialization"""
    from chains.english_chain import english_chain
    return english_chain

async def generate_speech(text: str, voice_type: str = 'default', speed: str = 'normal') -> str:
    """Generate speech audio file with selected voice and speed"""
    try:            
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Invalid text input")
            
        audio_dir = get_audio_dir()
        os.makedirs(audio_dir, exist_ok=True)
        
        # Clean up old files before creating new one
        delete_old_audio_files(hours=0)
        
        filename = f"english_{uuid.uuid4().hex}.mp3"
        filepath = os.path.join(audio_dir, filename)
        
        voice = VOICE_OPTIONS.get(voice_type, VOICE_OPTIONS['default'])
        rate = SPEED_OPTIONS.get(speed, SPEED_OPTIONS['normal'])
        
        # Add timeout for TTS generation
        try:
            communicate = edge_tts.Communicate(text, voice, rate=rate)
            await asyncio.wait_for(communicate.save(filepath), timeout=15)  # 15s timeout
            return f"/static/audio/english/{filename}"#change
        except asyncio.TimeoutError:
            print("TTS generation timed out")
            return None
            
    except Exception as e:
        print(f"Error in speech generation: {e}")
        return None

@english_call_bp.route('/clean-audio', methods=['POST'])
def clean_audio():
    """Endpoint to clean up audio files"""
    try:
        delete_old_audio_files(hours=0)  
        return jsonify({"status": "success", "message": "Audio files cleaned"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@english_call_bp.route('/call', methods=['POST'])
async def voice_chat():
    """Handle voice chat with voice and speed options"""
    data = request.get_json()
    message = data.get('message', '').strip()
    voice_type = data.get('voice', 'default')
    speed = data.get('speed', 'normal')
    
    if not message:
        return jsonify({"text": "Please say something.", "audio": None})
    
    try:
        
        chain = get_english_chain()
        
        # Add timeout for AI response
        try:
            response = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None,  
                    lambda: chain.invoke({"text": message})
                ),
                timeout=5  
            )
            response_text = str(response.content) if hasattr(response, 'content') else str(response)
        except asyncio.TimeoutError:
            response_text = "I need more time to think about that. Could you ask me something else?"
        
        
        audio_url = None
        if not response_text.startswith("I need more time"):
            audio_url = await generate_speech(response_text, voice_type, speed)
        
        return jsonify({
            "text": response_text,
            "audio": audio_url
        })
        
    except Exception as e:
        print(f"Error in voice chat endpoint: {e}")
        return jsonify({
            "text": "Sorry, I'm having technical difficulties. Please try again.", 
            "audio": None
        }), 500


