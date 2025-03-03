import easyocr
import fitz  # PyMuPDF
from PIL import Image, ImageEnhance, ImageFilter
import os
import io
import smbclient
import cv2
import numpy as np
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# SMB connection details
server_name = os.getenv("SERVER_NAME")
server_ip = os.getenv("SERVER_IP")
share_name = os.getenv("SHARE_NAME")
username = os.getenv("USERNAME")
password = os.getenv("PASSWORD")

# Folder containing JPG images on SMB share
image_folder = "input"
bw_image_folder = "bw_images"
output_pdf = "searchable_output.pdf"

# Register SMB connection
smbclient.register_session(server_ip, username=username, password=password)

# Create a new PDF
pdf_document = fitz.open()

# Ensure the B&W image folder exists
bw_image_folder_path = f"\\\\{server_ip}\\{share_name}\\{bw_image_folder}"
if not smbclient.path.exists(bw_image_folder_path):
    smbclient.mkdir(bw_image_folder_path)

# Initialize EasyOCR reader
reader = easyocr.Reader(['fr', 'en', 'de'], gpu=False)  # Add languages as needed

# Process each image
directory_path = f"\\\\{server_ip}\\{share_name}\\{image_folder}"
for file_info in smbclient.listdir(directory_path):
    if file_info.lower().endswith((".jpg")):
        img_path = f"\\\\{server_ip}\\{share_name}\\{image_folder}\\{file_info}"

        # Open image from SMB share
        with smbclient.open_file(img_path, mode='rb') as file:
            img_data = file.read()
            img = Image.open(io.BytesIO(img_data))

            # Resize the image into an image with 1500px maximum long edge
            # max_size = 1500
            # width, height = img.size
            # if width > height:
            #     new_width = min(width, max_size)
            #     new_height = int(height * new_width / width)
            # else:
            #     new_height = min(height, max_size)
            #     new_width = int(width * new_height / height)
            # img = img.resize((new_width, new_height))

            # Convert image to numpy array
            img_np = np.array(img)

            # Perform OCR using EasyOCR
            result = reader.readtext(img_np, batch_size=3)

            # Create a new PDF page
            page = pdf_document.new_page(width=img.width, height=img.height)

            # Add the original image to the PDF
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='JPEG')
            img_bytes = img_byte_arr.getvalue()
            page.insert_image(page.rect, stream=img_bytes)

            # Add OCR text to the PDF
            for (bbox, text, prob) in result:
                (top_left, top_right, bottom_right, bottom_left) = bbox
                x_min = min(top_left[0], bottom_left[0])
                y_min = min(top_left[1], top_right[1])
                x_max = max(bottom_right[0], top_right[0])
                y_max = max(bottom_right[1], bottom_left[1])
    
                # Calculate the font size based on the height of the bounding box
                bbox_height = y_max - y_min
                fontsize = float(bbox_height * 0.6)  # Adjust the multiplier as needed

                # Insert the text box with transparent text
                page.insert_text((x_min, y_max), text, fontsize=fontsize, stroke_opacity=0, fill_opacity=0)

# Save the searchable PDF to SMB share
output_path = f"\\\\{server_ip}\\{share_name}\\{output_pdf}"
with smbclient.open_file(output_path, mode='wb') as output_file:
    output_file.write(pdf_document.write())

pdf_document.close()

print(f"Searchable PDF saved as {output_pdf}")
print(f"B&W images saved in folder: {bw_image_folder}")