from flask import Blueprint, render_template, request, jsonify
from chains.vocabulary_chain import vocabulary_chain
import json
import re

vocabulary_bp = Blueprint('vocabulary', __name__)

@vocabulary_bp.route('/vocabulary', methods=['GET', 'POST'])
def vocabulary():
    result = None
    if request.method == 'POST':
        word = request.form.get('word')
        if word:
            try:
                # Get response from chain
                chain_response = vocabulary_chain.invoke({"word": word})
                response_text = chain_response.content
                
                # Parse the JSON response
                result = parse_vocabulary_response(response_text, word)
                
            except Exception as e:
                result = {
                    "word": word,
                    "part_of_speech": "error",
                    "burmese": "အမှားတစ်ခုဖြစ်နေပါသည်",
                    "definition": {
                        "english": f"Error: {str(e)}",
                        "burmese": "အမှားတစ်ခုဖြစ်ပေါ်နေပါသည်"
                    },
                    "examples": [
                        {
                            "english": "Please try again with a different word.",
                            "burmese_translation": "ကျေးဇူးပြု၍ အခြားစကားလုံးဖြင့် ထပ်မံကြိုးစားကြည့်ပါ။"
                        },
                        {
                            "english": "Check your internet connection.",
                            "burmese_translation": "သင့်အင်တာနက်ချိတ်ဆက်မှုကို စစ်ဆေးကြည့်ပါ။"
                        },
                        {
                            "english": "If problem persists, contact support.",
                            "burmese_translation": "ပြဿနာဆက်ရှိနေပါက အကူအညီယူပါ။"
                        }
                    ]
                }

    return render_template('vocabulary.html', result=result)

@vocabulary_bp.route('/vocabulary/search', methods=['POST'])
def search_word():
    try:
        data = request.get_json()
        word = data.get('word', '').strip()
        
        if not word:
            return jsonify({'error': 'Please enter a word'})
        
        # Get response from chain
        chain_response = vocabulary_chain.invoke({"word": word})
        response_text = chain_response.content
        
        # Parse the response
        result = parse_vocabulary_response(response_text, word)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'error': f'Server error: {str(e)}',
            'word': word,
            'part_of_speech': 'error',
            'burmese': 'အမှားတစ်ခုဖြစ်နေပါသည်',
            'definition': {
                'english': 'An error occurred while processing your request',
                'burmese': 'တောင်းပန်ပါတယ်၊ သင့်တောင်းဆိုမှုကို ပြုလုပ်စဉ် အမှားတစ်ခုဖြစ်ပေါ်ခဲ့သည်'
            },
            'examples': [{
                'english': 'Please try again later.',
                'burmese_translation': 'ကျေးဇူးပြု၍ နောက်မှထပ်ကြိုးစားကြည့်ပါ။'
            }]
        })

def parse_vocabulary_response(response_text, original_word):
    """
    Parse the AI response and extract structured vocabulary data
    """
    try:
        # Try to extract JSON from the response
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group()
            data = json.loads(json_str)
            
            # Validate required fields
            required_fields = ['word', 'part_of_speech', 'burmese', 'definition', 'examples']
            for field in required_fields:
                if field not in data:
                    if field == 'examples':
                        data[field] = []
                    elif field == 'definition':
                        data[field] = {"english": "Definition not available", "burmese": "အဓိပ္ပာယ်ဖွင့်ဆိုချက် မရှိပါ"}
                    else:
                        data[field] = f"Missing {field}"
            
            # Process definition to ensure it has proper structure
            data['definition'] = validate_definition(data['definition'], original_word)
            
            # Process examples to ensure they have proper structure
            data['examples'] = validate_examples(data['examples'], original_word)
            
            return data
        
        else:
            # If no JSON found, create a fallback response
            return create_fallback_response(original_word, response_text)
            
    except json.JSONDecodeError:
        # If JSON parsing fails, create fallback response
        return create_fallback_response(original_word, response_text)

def validate_definition(definition, word):
    """
    Validate and ensure definition has proper structure with both English and Burmese
    """
    if isinstance(definition, dict):
        if 'english' in definition and 'burmese' in definition:
            return {
                'english': definition['english'],
                'burmese': definition['burmese']
            }
        elif 'english' in definition:
            return {
                'english': definition['english'],
                'burmese': generate_burmese_definition(definition['english'])
            }
        else:
            # Try to extract from string values
            english_def = definition.get('definition') or str(definition)
            return {
                'english': english_def,
                'burmese': generate_burmese_definition(english_def)
            }
    elif isinstance(definition, str):
        return {
            'english': definition,
            'burmese': generate_burmese_definition(definition)
        }
    else:
        return {
            'english': f"Definition of {word}",
            'burmese': f"{word} ၏ အဓိပ္ပာယ်ဖွင့်ဆိုချက်"
        }

def generate_burmese_definition(english_definition):
    """
    Generate a Burmese translation for English definition
    This is a fallback - the AI should provide this in the response
    """
    # Simple mapping for common definition patterns
    mappings = {
        "noun": "နာမ်",
        "verb": "�ြိယာ", 
        "adjective": "နာမဝိသေသန",
        "adverb": "ကြိယာဝိသေသန",
        "used to": "အသုံးပြုသည်",
        "something": "တစ်စုံတစ်ရာ",
        "someone": "တစ်စုံတစ်ယောက်",
        "action": "လုပ်ဆောင်ချက်",
        "state": "အခြေအနေ",
        "quality": "အရည်အသွေး",
        "feeling": "ခံစားချက်",
        "object": "အရာဝတ္ထု",
        "person": "လူ",
        "place": "နေရာ",
        "thing": "အရာ",
        "time": "အချိန်",
        "way": "နည်းလမ်း"
    }
    
    # Simple word replacement (this is just a fallback)
    burmese_definition = english_definition
    for eng, bur in mappings.items():
        burmese_definition = burmese_definition.replace(eng, bur)
    
    return f"{burmese_definition} ဟု အဓိပ္ပာယ်ရသည်"

def validate_examples(examples, word):
    """
    Validate and ensure examples have proper structure with Burmese translations
    """
    validated_examples = []
    
    if isinstance(examples, list):
        for example in examples:
            if isinstance(example, dict) and 'english' in example and 'burmese_translation' in example:
                # Already in correct format
                validated_examples.append({
                    'english': example['english'],
                    'burmese_translation': example['burmese_translation']
                })
            elif isinstance(example, str):
                # If it's a string, use it as English and create placeholder Burmese
                validated_examples.append({
                    'english': example,
                    'burmese_translation': f"ဤဝါကျကို {word} စကားလုံးဖြင့် ဖွဲ့စည်းထားပါသည်"
                })
            elif isinstance(example, dict):
                # Try to extract from different possible key names
                english = example.get('english') or example.get('sentence') or example.get('example') or str(example)
                burmese = example.get('burmese_translation') or example.get('burmese') or example.get('translation') or f"{word} စကားလုံးပါဝင်သော ဝါကျ"
                
                validated_examples.append({
                    'english': english,
                    'burmese_translation': burmese
                })
    
    # Ensure we have at least 3 examples
    while len(validated_examples) < 3:
        validated_examples.append({
            'english': f"Example sentence {len(validated_examples) + 1} with {word}",
            'burmese_translation': f"{word} စကားလုံးပါဝင်သော ဥပမာဝါကျ {len(validated_examples) + 1}"
        })
    
    return validated_examples[:3]

def create_fallback_response(word, response_text):
    """
    Create a fallback response when parsing fails
    """
    # Try to extract information from unstructured text
    burmese = extract_burmese(response_text)
    part_of_speech = extract_part_of_speech(response_text)
    definition_text = extract_definition(response_text)
    
    # Process definition
    definition = validate_definition(definition_text, word)
    
    # Extract examples
    examples = extract_examples(response_text)
    validated_examples = validate_examples(examples, word)
    
    return {
        "word": word,
        "part_of_speech": part_of_speech,
        "burmese": burmese,
        "definition": definition,
        "examples": validated_examples
    }

def extract_burmese(text):
    """Extract Burmese translation from text"""
    patterns = [
        r'"burmese"\s*:\s*"([^"]+)"',
        r'burmese[:\s]+([^\n]+)',
        r'မြန်မာ[:\s]+([^\n]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    
    return "ဘာသာပြန်မရှိပါ"

def extract_part_of_speech(text):
    """Extract part of speech from text"""
    patterns = [
        r'"part_of_speech"\s*:\s*"([^"]+)"',
        r'part of speech[:\s]+(\w+)',
        r'(\b(noun|verb|adjective|adverb|preposition|conjunction|interjection)\b)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip().lower()
    
    return "unknown"

def extract_definition(text):
    """Extract definition from text"""
    patterns = [
        r'"definition"\s*:\s*"([^"]+)"',
        r'"english"\s*:\s*"([^"]+)"',
        r'definition[:\s]+([^\n]+)',
        r'means?[:\s]+([^\n.]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    
    return "Definition not available"

def extract_examples(text):
    """Extract example sentences from text"""
    examples = []
    
    # Look for JSON examples array first
    json_pattern = r'"examples"\s*:\s*\[(.*?)\]'
    json_match = re.search(json_pattern, text, re.DOTALL)
    if json_match:
        examples_content = json_match.group(1)
        # Extract individual example objects
        example_pattern = r'\{(.*?)\}'
        example_matches = re.findall(example_pattern, examples_content, re.DOTALL)
        for match in example_matches:
            # Try to extract English sentence from example object
            english_pattern = r'"english"\s*:\s*"([^"]+)"'
            english_match = re.search(english_pattern, match)
            if english_match:
                examples.append(english_match.group(1))
    
    # If no JSON examples found, look for numbered examples
    if not examples:
        patterns = [
            r'\d+\.\s*([^\n]+)',
            r'[•\-]\s*([^\n]+)',
            r'Example[:\s]+([^\n.]+)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, str):
                    clean_line = match.strip().strip('"')
                    if clean_line and len(clean_line) > 10:
                        examples.append(clean_line)
    
    return examples