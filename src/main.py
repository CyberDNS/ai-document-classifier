import time
import os
import shutil
import json
from threading import Thread
from watchdog.observers.polling import PollingObserver
from watchdog.events import FileSystemEventHandler
from dotenv import load_dotenv
from api import start_flask_server
from ocr.adobe_ocr_api import AdobeOCR
from ocr.mistral_ocr_api import MistralOCR

# Load environment variables from .env file
load_dotenv()

# Get the SMB share path and data path from environment variables
SMB_SHARE_PATH = os.getenv("SMB_MOUNTPOINT")
DATA_PATH = os.getenv("DATA_PATH")
IMAGES_PATH = os.path.join(DATA_PATH, "images")
OCR_OUTPUT_PATH = os.path.join(DATA_PATH, "ocr_output")

# Ensure the images and OCR output directories exist
os.makedirs(IMAGES_PATH, exist_ok=True)
os.makedirs(OCR_OUTPUT_PATH, exist_ok=True)

class ScanHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        if event.src_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.pdf')):
            print(f"File created: {event.src_path}")
            thread = Thread(target=self.copy_and_verify_file, args=(event.src_path,))
            thread.start()

    def copy_and_verify_file(self, src_path, timeout=30):
        """Copy the file and verify it is fully written before deleting the source file."""
        filename = os.path.basename(src_path)
        dest_path = os.path.join(IMAGES_PATH, filename)

        start_time = time.time()
        while True:
            if self.is_file_fully_written(src_path):
                print(f"File {dest_path} is fully written.")
                shutil.move(src_path, dest_path)
                print(f"Moved file to: {dest_path}")
                run_ocr(dest_path)  # Run OCR after moving the file
                break
            if time.time() - start_time > timeout:
                print(f"Timeout waiting for file {dest_path} to be fully written.")
                break
            time.sleep(1)

    def is_file_fully_written(self, src_path):
        """Check if the file is fully written by comparing its size over time."""
        initial_size = os.path.getsize(src_path)
        time.sleep(5)
        new_size = os.path.getsize(src_path)
        return initial_size == new_size

def run_ocr(file_path):
    """Run OCR on the given file."""
    if file_path.lower().endswith('.pdf'):
        # Extract image from first page of PDF
        adobe_ocr = AdobeOCR()
        output_image_path = os.path.join(IMAGES_PATH, os.path.basename(file_path) + '.jpg')
        adobe_ocr.extract_images_from_pdf(file_path, output_image_path)
        print(f"Extracted image from PDF: {output_image_path}")

        mistral_ocr = MistralOCR()
        language = mistral_ocr.detect_language(output_image_path)

        output_ocr_path = os.path.join(OCR_OUTPUT_PATH, os.path.basename(file_path))
        adobe_ocr.ocr(file_path, output_ocr_path, language)
        print(f"OCR completed for {file_path}. Output saved to {output_ocr_path}")

        classify_pdf(output_ocr_path, mistral_ocr)

    elif file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff')):
        mistral_ocr = MistralOCR()
        classification_response = mistral_ocr.classify_document(file_path)
        if classification_response:
            print(f"Classification completed for {file_path}. Classification response: {classification_response}")
            json_output_path = os.path.join(IMAGES_PATH, os.path.basename(file_path) + '.json')
            with open(json_output_path, 'w') as json_file:
                json.dump(classification_response, json_file)
            print(f"Classification result saved to {json_output_path}")
        else:
            print(f"Error during document classification for {file_path}")

def classify_pdf(file_path, mistral_ocr):
    classification_response = mistral_ocr.classify_document_from_pdf(file_path)
    if classification_response:
        print(f"Classification completed for {file_path}. Classification response: {classification_response}")
        json_output_path = os.path.join(OCR_OUTPUT_PATH, os.path.basename(file_path) + '.json')
        with open(json_output_path, 'w') as json_file:
            json.dump(classification_response, json_file)
        print(f"Classification result saved to {json_output_path}")
    else:
        print(f"Error during document classification for {file_path}")

def classify_existing_pdfs():
    """Classify all PDFs in the OCR folder that have not yet been classified."""
    mistral_ocr = MistralOCR()
    for root, _, files in os.walk(OCR_OUTPUT_PATH):
        for file in files:
            if file.lower().endswith('.pdf'):
                pdf_path = os.path.join(root, file)
                json_output_path = os.path.join(OCR_OUTPUT_PATH, os.path.basename(file) + '.json')
                if not os.path.exists(json_output_path):
                    classify_pdf(pdf_path, mistral_ocr)

def start_smb_watcher():
    """Starts the SMB share watcher."""
    print("Initializing ScanHandler...")
    classify_existing_pdfs()  # Classify existing PDFs on startup

    event_handler = ScanHandler()
    observer = PollingObserver()
    watch_path = os.path.join(SMB_SHARE_PATH, "input")
    
    # Check if the watch path exists
    if not os.path.exists(watch_path):
        print(f"Error: Watch path does not exist: {watch_path}")
        return
    
    print(f"Watching path: {watch_path}")
    observer.schedule(event_handler, watch_path, recursive=False)
    observer.start()
    print("Observer started.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping observer...")
        observer.stop()
    observer.join()
    print("Observer stopped.")

if __name__ == "__main__":
    print("Starting SMB watcher and Flask server...")
    watcher_thread = Thread(target=start_smb_watcher)
    flask_thread = Thread(target=start_flask_server)
    watcher_thread.start()
    flask_thread.start()
    watcher_thread.join()
    flask_thread.join()