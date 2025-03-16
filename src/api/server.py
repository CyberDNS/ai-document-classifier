from flask import Flask, send_from_directory, jsonify, request, send_file, Response
from flask_cors import CORS
import os
import shutil
import json
from dotenv import load_dotenv
import time

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__, static_folder='../frontend', static_url_path='/')
CORS(app)  # Enable CORS

# Get the data path from environment variables
DATA_PATH = os.getenv("DATA_PATH")
IMAGES_PATH = os.path.join(DATA_PATH, "images")
OCR_OUTPUT_PATH = os.path.join(DATA_PATH, "ocr_output")
OUTPUT_PATH = os.path.join(os.getenv("SMB_MOUNTPOINT"), "output")  # Use SMB share path

# Ensure the output directory exists
os.makedirs(OUTPUT_PATH, exist_ok=True)

# Load configuration file with error handling
config_filepath = os.path.join(DATA_PATH, "config.json")
default_config = {
    "categories": [],
    "sources": [],
    "destinations": []
}

def reload_config(config_filepath, default_config):
    try:
        with open(config_filepath) as config_file:
            config = json.load(config_file)
    except (FileNotFoundError, json.JSONDecodeError):
        config = default_config
    return config

config = reload_config(config_filepath, default_config)

@app.route('/')
def serve_frontend():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_static_files(path):
    return send_from_directory(app.static_folder, path)

@app.route('/config.json')
def serve_config():
    api_url = os.getenv('VUE_APP_API_URL', 'http://localhost:5298')
    config_data = {
        "VUE_APP_API_URL": api_url
    }
    return jsonify(config_data)

@app.route('/images', methods=['GET'])
def list_images():
    """List all images in the images directory."""
    try:
        files = os.listdir(IMAGES_PATH)
        images = sorted([f for f in files if os.path.isfile(os.path.join(IMAGES_PATH, f)) and f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp'))])
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

@app.route('/images/<filename>/metadata', methods=['GET'])
def get_metadata(filename):
    """Serve a metadata JSON file from the OCR output directory."""
    try:
        metadata_filename = f"{filename}.json"
        return send_from_directory(IMAGES_PATH, metadata_filename)
    except Exception as e:
        return jsonify({"error": str(e)}), 404

@app.route('/documents', methods=['GET'])
def list_documents():
    """List all pdf documents in the ocr_output directory."""
    try:
        files = os.listdir(OCR_OUTPUT_PATH)
        docs = sorted([f for f in files if os.path.isfile(os.path.join(OCR_OUTPUT_PATH, f)) and f.lower().endswith(('.pdf'))])
        return jsonify(docs)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/documents/<filename>', methods=['GET'])
def get_document(filename):
    """Serve an pdf document from the ocr_output directory."""
    try:
        return send_from_directory(OCR_OUTPUT_PATH, filename)
    except Exception as e:
        return jsonify({"error": str(e)}), 404

@app.route('/documents/<filename>/metadata', methods=['GET'])
def get_documents_metadata(filename):
    """Serve a metadata JSON file from the OCR output directory."""
    try:
        metadata_filename = f"{filename}.json"
        return send_from_directory(OCR_OUTPUT_PATH, metadata_filename)
    except Exception as e:
        return jsonify({"error": str(e)}), 404

@app.route('/documents/save', methods=['POST'])
def save_document():
    """Save the renamed file and metadata to the SMB share output directory."""
    try:
        data = request.json
        original_filename = data['originalFilename']
        renamed_filename = data['renamedFilename']
        metadata = data['metadata']
        category = metadata.get('category', 'uncategorized')

        # Create the category subfolder if it doesn't exist
        category_path = os.path.join(OUTPUT_PATH, category)
        os.makedirs(category_path, exist_ok=True)

        # Move the file to the SMB share output directory with the new name
        original_file_path = os.path.join(OCR_OUTPUT_PATH, original_filename)
        renamed_file_path = os.path.join(category_path, renamed_filename)
        shutil.move(original_file_path, renamed_file_path)
        os.remove(f"{original_file_path}.json")

        # Save the metadata to the SMB share output directory
        metadata_filename = f"{renamed_filename}.json"
        metadata_file_path = os.path.join(category_path, metadata_filename)
        with open(metadata_file_path, 'w') as metadata_file:
            json.dump(metadata, metadata_file)

        return jsonify({"message": "File and metadata saved successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/config/categories', methods=['GET'])
def get_categories():
    config = reload_config(config_filepath, default_config)
    return jsonify(config['categories'])

@app.route('/config/categories', methods=['POST'])
def add_category():
    try:
        new_category = request.json.get('category')
        config = reload_config(config_filepath, default_config)
        if new_category not in config['categories']:
            config['categories'].append(new_category)
            with open(config_filepath, 'w') as config_file:
                json.dump(config, config_file)
        return jsonify({"message": "Category added successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/config/sources', methods=['GET'])
def get_sources():
    config = reload_config(config_filepath, default_config)
    return jsonify(config['sources'])

@app.route('/config/sources', methods=['POST'])
def add_source():
    try:
        new_source = request.json.get('source')
        config = reload_config(config_filepath, default_config)
        if new_source not in config['sources']:
            config['sources'].append(new_source)
            with open(config_filepath, 'w') as config_file:
                json.dump(config, config_file)
        return jsonify({"message": "Source added successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/config/destinations', methods=['GET'])
def get_destinations():
    config = reload_config(config_filepath, default_config)
    return jsonify(config['destinations'])

@app.route('/config/destinations', methods=['POST'])
def add_destination():
    try:
        new_destination = request.json.get('destination')
        config = reload_config(config_filepath, default_config)
        if new_destination not in config['destinations']:
            config['destinations'].append(new_destination)
            with open(config_filepath, 'w') as config_file:
                json.dump(config, config_file)
        return jsonify({"message": "Destination added successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/sse/documents', methods=['GET'])
def sse_documents():
    def generate():
        previous_docs = set()
        while True:
            try:
                files = os.listdir(OCR_OUTPUT_PATH)
                current_docs = set(f for f in files if os.path.isfile(os.path.join(OCR_OUTPUT_PATH, f)) and f.lower().endswith('.pdf.json'))
                if current_docs != previous_docs:
                    docs = sorted(current_docs)
                    data = json.dumps({"totalDocuments": len(docs)})
                    yield f"data: {data}\n\n"
                    previous_docs = current_docs
                time.sleep(5)  # Adjust the interval as needed
            except Exception as e:
                yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"
                time.sleep(5)

    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5298)