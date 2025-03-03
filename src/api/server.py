from flask import Flask, send_from_directory, jsonify
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Get the data path from environment variables
DATA_PATH = os.getenv("DATA_PATH")
IMAGES_PATH = os.path.join(DATA_PATH, "images")

@app.route('/images', methods=['GET'])
def list_images():
    """List all images in the images directory."""
    try:
        files = os.listdir(IMAGES_PATH)
        images = [f for f in files if os.path.isfile(os.path.join(IMAGES_PATH, f))]
        return jsonify(images)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/images/<filename>', methods=['GET'])
def get_image(filename):
    """Serve an image from the images directory."""
    try:
        return send_from_directory(IMAGES_PATH, filename)
    except Exception as e:
        return jsonify({"error": str(e)}), 404