from flask import Blueprint, render_template, request
from chains.translator_chain import translator_chain

translate_bp = Blueprint('translate', __name__)


@translate_bp.route('/translate', methods=['GET', 'POST'])
def translate():
    translated_text = ""
    if request.method == 'POST':
        text = request.form.get('text')
        if text:
            result = translator_chain.invoke({"text": text})
            translated_text = result.content

    return render_template('translate.html', translate=translated_text)
