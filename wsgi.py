from main import app

if __name__ == "__main__":
    # This part is mainly for convenience if you ever run `python wsgi.py` directly,
    # though typically Gunicorn will import the 'app' object directly.
    # Use the same host/port/debug settings as your development run if needed.
    app.run()