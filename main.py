"""
Pokémon Hangman Game - Flask Application

This module initializes the Flask app and registers the routes.
"""

from flask import Flask
import os
# Import the blueprint
from routes import hangman_bp

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Register the blueprint
# If you plan to run under a prefix like /hangman, you can specify it here:
# app.register_blueprint(hangman_bp, url_prefix='/hangman')
# However, let's keep it at the root for now, Nginx/Gunicorn will handle the prefix.
app.register_blueprint(hangman_bp)

# Keep this for running locally during development
if __name__ == "__main__":
    # Note: debug=True should be False in production
    app.run(debug=True)
