import os
import json
import fitz  # PyMuPDF to extract text from PDFs
import shutil
from pydantic import BaseModel
from openai import OpenAI
from flask import Flask, render_template, request, redirect, url_for
import re
import datetime

# Flask setup
app = Flask(__name__)

# Define the structure of the expected response using Pydantic
class DocumentClassificationResponse(BaseModel):
    date: str
    source: str
    destination: str
    description: str
    classification: str

# Function to extract text from a PDF
def extract_text_from_pdf(pdf_file):
    doc = fitz.open(pdf_file)
    text = ""
    for page in doc:
        text += page.get_text()
    return text

# Load config from a JSON file
def load_config(input_folder):
    config_path = os.path.join(input_folder, "config.json")
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found at {config_path}")
    
    with open(config_path, "r") as config_file:
        config = json.load(config_file)
    
    return config

# Load additional destinations and description suggestions from file
def load_additional_data(input_folder):
    additional_data_path = os.path.join(input_folder, "additional_data.json")
    
    if not os.path.exists(additional_data_path):
        return {"additional_sources": [], "description_suggestions": []}
    
    with open(additional_data_path, "r") as additional_data_file:
        return json.load(additional_data_file)

# Save additional destinations and description suggestions to file
def save_additional_data(input_folder, additional_sources, description_suggestions):
    additional_data_path = os.path.join(input_folder, "additional_data.json")
    additional_data = {
        "additional_sources": additional_sources,
        "description_suggestions": description_suggestions
    }
    with open(additional_data_path, "w") as additional_data_file:
        json.dump(additional_data, additional_data_file, indent=4)

# Initialize OpenAI client with the API key from config
def initialize_openai_client(api_key):
    return OpenAI(api_key=api_key)

# Function to classify the document using OpenAI API
def classify_document(client, text, sources, destinations, classifications, description_suggestions):

    # convert the lists to strings for the prompt
    sources = ", ".join(sources)
    destinations = ", ".join(destinations)
    classifications = ", ".join(classifications)
    description_suggestions = ", ".join(description_suggestions)
    

    system_prompt = f"""
    Act as a document management agent that is responsible for classifying documents at home. 
    Names of a person should always be put in this order, the first name then the last name.
    Possible destinations are: "{destinations}".
    Possible classifications are: "{classifications}".
    If the content of the document matches the following description suggestions please use the same format: {description_suggestions}.
    Sources is normally a company or other entity that is the origin of the document. Examples are {sources}.
    Sources should never be a name from this list: {destinations}. It is better to leave the source blank than to use a name from the destination list.

    Here is an example of an output:
    {{
     "date": "20240523",
     "source": "Dr. Jerry Brandt",
     "destination": "David Ney",
     "description": "Ordonnance médicale pour kinésithérapie",
     "classification": "Gesundheit"
    }}
    """

    user_prompt = f"""
    DOCUMENT: {text[:2500]}
    """
    
    # Initial message sequence (the context starts here)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    # Use the new ChatCompletion API
    response = client.beta.chat.completions.parse(
        # model="gpt-4o-mini",
        model="gpt-4o-2024-08-06", 
        messages=messages,
        response_format=DocumentClassificationResponse,
    )
    
    parsed_result = response.choices[0].message.parsed

    # If the source was correct, return the original result
    return parsed_result

# Store classification results temporarily for review
classification_results = []

@app.route('/')
def index():
    return render_template('index.html', classifications=classification_results)

@app.route('/classify', methods=['POST'])
def classify_documents():
    input_folder = "/app/input"
    
    # Load the configuration from the config.json file
    config = load_config(input_folder)
    additional_data = load_additional_data(input_folder)

    api_key = config.get("api_key")
    sources = config.get("sources", []) + additional_data.get("additional_sources", [])
    destinations = config.get("destinations", [])
    classifications = config.get("classifications", [])
    description_suggestions = additional_data.get("description_suggestions", [])
    
    # Initialize the OpenAI client with the API key
    client = initialize_openai_client(api_key)

    classification_results.clear()  # Clear previous results

    for filename in os.listdir(input_folder):
        if filename.endswith(".pdf"):
            filepath = os.path.join(input_folder, filename)
            pdf_text = extract_text_from_pdf(filepath)

            # Get classification result
            parsed_response = classify_document(client, pdf_text, sources, destinations, classifications, description_suggestions)
            
            # Store the result temporarily for review
            classification_results.append({
                'filename': filename,
                'date': parsed_response.date,
                'source': parsed_response.source,
                'destination': parsed_response.destination,
                'description': parsed_response.description,
                'classification': parsed_response.classification
            })

    return redirect(url_for('index'))

@app.route('/confirm', methods=['POST'])
def confirm_classification():
    input_folder = "/app/input"
    output_folder = "/app/output"
    
    additional_data = load_additional_data(input_folder)

    additional_sources = additional_data.get("additional_sources", [])
    description_suggestions = additional_data.get("description_suggestions", [])

    for result in classification_results:
        filename = result['filename']
        # Get the modified values from the form
        date = request.form.get(f"date_{filename}")
        source = request.form.get(f"source_{filename}")
        destination = request.form.get(f"destination_{filename}")
        description = request.form.get(f"description_{filename}")
        classification = request.form.get(f"classification_{filename}")
        

        # Add new destination if it's not already in the config
        if request.form.get(f"add_source_{result['filename']}") and source not in additional_sources:
            additional_sources.append(destination)
        
        # Add description suggestion if checkbox is selected
        if request.form.get(f"add_description_{result['filename']}") and description not in description_suggestions:
            description_suggestions.append(description)

        # Replace invalid characters from the filename
        new_filename = f"{date}-{source}-{destination}-{description}.pdf"
        new_filename = re.sub(r'[\/\\:*?"<>| ]', '_', new_filename)

        dest_folder = os.path.join(output_folder, classification)
        os.makedirs(dest_folder, exist_ok=True)
        
        # Copy the file to the final destination
        shutil.copy(os.path.join("/app/input", filename), os.path.join(dest_folder, new_filename))

        # move the input files to the processed folder and subfolder with timestamp
        processed_folder = os.path.join(input_folder, "processed")
        os.makedirs(processed_folder, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        processed_subfolder = os.path.join(processed_folder, timestamp)
        os.makedirs(processed_subfolder, exist_ok=True)
        shutil.move(os.path.join(input_folder, filename), os.path.join(processed_subfolder, filename))

    # Save the additional destinations and description suggestions
    save_additional_data(input_folder, additional_sources, description_suggestions)
        
    # Clear the classification results after processing
    classification_results.clear()

    return redirect(url_for('index'))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)