from flask import Flask, render_template, request
from werkzeug.middleware.proxy_fix import ProxyFix
from app.routes import hangman_bp

def create_app():
    print("Flask app initialized.")
    app = Flask(__name__)
    
    # Apply ProxyFix middleware for reverse proxy support
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
    
    # Register the blueprint with the app
    app.register_blueprint(hangman_bp)
    
    print(app.url_map)
    # Add this handler to log request details
    @app.before_request
    def log_request_info():
        print("-" * 20)
        print(f"Headers: {request.headers}")
        print(f"Path seen by Flask: {request.path}")
        print(f"Script Root: {request.script_root}")
        print(f"URL: {request.url}")
        print("-" * 20)

    print("Flask app configured.")
    return app