from flask import Blueprint, render_template

home_bp = Blueprint('home', __name__)

@home_bp.route('/')
def home():
    return render_template('index.html')  


# @app.route('/english')
# def english_page():
#     return render_template('englishtr.html') 