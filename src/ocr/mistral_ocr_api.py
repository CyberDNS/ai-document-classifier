import base64
import os
import logging
from mistralai import Mistral
from dotenv import load_dotenv
from pydantic import BaseModel
from enum import Enum
import json
import fitz  # PyMuPDF

logging.basicConfig(level=logging.INFO)

# Load environment variables from .env file
load_dotenv()

# Get the data path from environment variables
DATA_PATH = os.getenv("DATA_PATH")

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


class DocumentClassification(BaseModel):
    date: str
    languages: list[str]
    category: str
    source: str
    destination: str
    containsDestinationAddress: bool
    description: str
    name: str

class LanguageEnum(str, Enum):
    DE_DE = "DE_DE"
    EN_US = "EN_US"
    FR_FR = "FR_FR"

class DocumentLanguage(BaseModel):
    firstHundredWords: str
    language: LanguageEnum
    description: str

class MistralOCR:
    def __init__(self):
        load_dotenv()

        self.api_key = os.getenv("MISTRAL_API_KEY")
        if not self.api_key:
            raise ValueError("MISTRAL_API_KEY environment variable is not set.")
        self.client = Mistral(api_key=self.api_key)

    def encode_image(self, image_path):
        """Encode the image to base64."""
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except FileNotFoundError:
            logging.error(f"Error: The file {image_path} was not found.")
            return None
        except Exception as e:
            logging.error(f"Error: {e}")
            return None

    def ocr(self, image_path):
        """Perform OCR on the given image and return the text response."""
        base64_image = self.encode_image(image_path)
        if not base64_image:
            return None

        try:
            ocr_response = self.client.ocr.process(
                model="mistral-ocr-latest",
                document={
                    "type": "image_url",
                    "image_url": f"data:image/jpeg;base64,{base64_image}"
                }
            )
            return ocr_response
        except Exception as e:
            logging.error(f"Error during OCR processing: {e}")
            return None

    def detect_language(self, image_path):
        """Detect the language of the document using the given image path."""

        base64_image = self.encode_image(image_path)
        if not base64_image:
            return None

        system_message = """You are a DMS expert.
                        Write out the first 100 words of the document and provide the detected language based on this.
                        Think twice before defining the language based on the first 100 words. It is crucial to provide the correct language.
                        After having detected the correct language, you should also provide a description of the content of the document in the detected language."""

        messages = [
            {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": system_message
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Here is the document for language classification. "
                    },
                    {
                        "type": "image_url",
                        "image_url": f"data:image/jpeg;base64,{base64_image}"
                    }
                ]
            }
        ]

        try:
            language_response = self.client.chat.parse(
                model="pixtral-12b-latest",
                messages=messages,
                response_format=DocumentLanguage
            )

            model = json.loads(language_response.choices[0].message.content)
            return model['language']
        except Exception as e:
            logging.error(f"Error during language detection: {e}")
            return "DE_DE"

    def classify_document(self, image_path):
        """Classify the document using the given image path and return the classification model."""
        base64_image = self.encode_image(image_path)
        if not base64_image:
            return None

        system_message = f"""You are a DMS expert. You have to categorize incoming office documents for the DMS. 
                        First we have to detect the language of the document because the rest of the classification depends on it.
                        The output for name and description must be in the same language that the document was written in.
                        Description is a string that describes the content of the document. It should also contain information about the sender and the recipient.
                        Also the main purpose of the document should be described.
                        Date is the date of the document. The format of the date should be YYYY-MM-DD.
                        Name is a short name for the document. It should be unique, short and describe the content of the document.
                        Please provide the language in the following form: DE_DE for german, EN_US for english and FR_FR for french. 
                        If it is another language the array should be empty. 
                        If multiple languages are detected, the main language should be on top of the array followed by the other languages. 
                        Source is the organism that sent the document. If none can be detected leave the field blank. 
                        Destination is the person that receives the document. If none can be detected leave the field blank. 
                        ContainsDestinationAddress is a boolean value that indicates if the document contains the postal address of the destination. 
                        The category should be determined based on the content and the description of the document. 
                        Only the following categories are allowed: {', '.join(config['categories'])}.
                        Source is preferable sources: {', '.join(config['sources'])}.
                        Destination is preferable destinations: {', '.join(config['destinations'])}."""

        # First classification using pixtral-12b-2409 model
        messages = [
            {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": system_message
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Here is the document for classification. "
                    },
                    {
                        "type": "image_url",
                        "image_url": f"data:image/jpeg;base64,{base64_image}"
                    }
                ]
            }
        ]

        try:
            chat_response = self.client.chat.parse(
                model="pixtral-12b-latest",
                messages=messages,
                response_format=DocumentClassification
            )
            initial_classification = json.loads(chat_response.choices[0].message.content)
        except Exception as e:
            logging.error(f"Error during initial document classification: {e}")
            return None

        # Verify and correct classification using mistral-large-latest model
        verification_messages = [
            {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": system_message
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "If the classification is correct, return the same classification. " +
                        "If it is incorrect, provide the correct classification. " +
                        json.dumps(initial_classification)
                    }
                ]
            }
        ]

        try:
            verification_response = self.client.chat.parse(
                model="mistral-large-latest",
                messages=verification_messages,
                response_format=DocumentClassification
            )
            final_classification = json.loads(verification_response.choices[0].message.content)
            return final_classification
        except Exception as e:
            logging.error(f"Error during classification verification: {e}")
            return initial_classification

    def classify_document_from_pdf(self, pdf_path):
        """Classify the document using the given PDF path and return the classification model."""
        try:
            # Open the PDF file
            pdf_document = fitz.open(pdf_path)
            # Extract text from the first page
            first_page = pdf_document.load_page(0)
            first_page_text = first_page.get_text("text")
        except Exception as e:
            logging.error(f"Error reading PDF file {pdf_path}: {e}")
            return None

        if not first_page_text:
            logging.error(f"No text found on the first page of the PDF {pdf_path}")
            return None

        system_message = f"""You are a DMS expert. You have to categorize incoming office documents for the DMS. 
                        First we have to detect the language of the document because the rest of the classification depends on it.
                        The output for name and description must be in the same language that the document was written in.
                        Description is a string that describes the content of the document. It should also contain information about the sender and the recipient.
                        Also the main purpose of the document should be described.
                        Date is the date of the document. The format of the date should be YYYY-MM-DD.
                        Name is a short name for the document. It should be unique, short and describe the content of the document.
                        Please provide the language in the following form: DE_DE for german, EN_US for english and FR_FR for french. 
                        If it is another language the array should be empty. 
                        If multiple languages are detected, the main language should be on top of the array followed by the other languages. 
                        Source is the organism that sent the document. If none can be detected leave the field blank. 
                        Destination is the person that receives the document. If none can be detected leave the field blank. 
                        ContainsDestinationAddress is a boolean value that indicates if the document contains the postal address of the destination. 
                        The category should be determined based on the content and the description of the document. 
                        Only the following categories are allowed: {', '.join(config['categories'])}.
                        Source is preferable sources: {', '.join(config['sources'])}.
                        Destination is preferable destinations: {', '.join(config['destinations'])}."""

        # First classification using pixtral-12b-2409 model
        messages = [
            {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": system_message
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Here is the document for classification. "
                    },
                    {
                        "type": "text",
                        "text": first_page_text
                    }
                ]
            }
        ]

        try:
            chat_response = self.client.chat.parse(
                model="mistral-small-latest",
                messages=messages,
                response_format=DocumentClassification
            )
            initial_classification = json.loads(chat_response.choices[0].message.content)
        except Exception as e:
            logging.error(f"Error during initial document classification: {e}")
            return None

        # Verify and correct classification using mistral-large-latest model
        verification_messages = [
            {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": system_message
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "If the classification is correct, return the same classification. " +
                        "If it is incorrect, provide the correct classification. " +
                        json.dumps(initial_classification)
                    }
                ]
            }
        ]

        try:
            verification_response = self.client.chat.parse(
                model="mistral-large-latest",
                messages=verification_messages,
                response_format=DocumentClassification
            )
            final_classification = json.loads(verification_response.choices[0].message.content)
            return final_classification
        except Exception as e:
            logging.error(f"Error during classification verification: {e}")
            return initial_classification