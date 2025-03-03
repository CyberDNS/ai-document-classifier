from .server import app

def start_flask_server():
    """Starts the Flask server."""
    app.run(host='0.0.0.0', port=5298)