import pytesseract
import fitz  # PyMuPDF
from PIL import Image
import os
import io
import smbclient
import cv2
import numpy as np
import subprocess
import urllib.request
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

# Path to textcleaner script
textcleaner_path = "./textcleaner"

# Download textcleaner if it does not exist
if not os.path.exists(textcleaner_path):
    url = "http://www.fmwconcepts.com/imagemagick/downloadcounter.php?scriptname=textcleaner&dirname=textcleaner"
    urllib.request.urlretrieve(url, textcleaner_path)
    os.chmod(textcleaner_path, 0o755)

# Register SMB connection
smbclient.register_session(server_ip, username=username, password=password)

# Create a new PDF
pdf_document = fitz.open()

# Ensure the B&W image folder exists
bw_image_folder_path = f"\\\\{server_ip}\\{share_name}\\{bw_image_folder}"
if not smbclient.path.exists(bw_image_folder_path):
    smbclient.mkdir(bw_image_folder_path)

# Process each image
directory_path = f"\\\\{server_ip}\\{share_name}\\{image_folder}"
for file_info in smbclient.listdir(directory_path):
    if file_info.lower().endswith((".jpg")):
        img_path = f"\\\\{server_ip}\\{share_name}\\{image_folder}\\{file_info}"

        # Open image from SMB share
        with smbclient.open_file(img_path, mode='rb') as file:
            img_data = file.read()
            img = Image.open(io.BytesIO(img_data))

            # Save the image to a temporary file
            temp_img_path = f"/tmp/{file_info}"
            img.save(temp_img_path)

            # Run textcleaner on the temporary file
            cleaned_img_path = f"/tmp/cleaned_{file_info}"

            # Run textcleaner on the temporary file with the following options: -g -e stretch -f 25 -o 10 -u -s 1 -T -p 10
            subprocess.run([textcleaner_path, "-g", "-e", "stretch", "-o", "7", "-t", "20", temp_img_path, cleaned_img_path])

            # Load the cleaned image
            cleaned_img = Image.open(cleaned_img_path)

            # Convert back to PIL image
            bw_img = Image.fromarray(np.array(cleaned_img))

            # Save the B&W image to the bw_images folder for debugging
            bw_img_path = f"\\\\{server_ip}\\{share_name}\\{bw_image_folder}\\bw_{file_info}"
            with smbclient.open_file(bw_img_path, mode='wb') as bw_file:
                bw_img_byte_arr = io.BytesIO()
                bw_img.save(bw_img_byte_arr, format='JPEG')
                bw_file.write(bw_img_byte_arr.getvalue())

            # Generate searchable PDF from the B&W image with Tesseract configuration
            custom_config = r'--oem 1 --psm 3'
            pdf_bytes = pytesseract.image_to_pdf_or_hocr(bw_img, lang='fra+deu+eng', config=custom_config, extension='pdf')

            # Add original image as a new page
            img_pdf = fitz.open("pdf", pdf_bytes)
            pdf_document.insert_pdf(img_pdf)

            # Add the original image to the PDF
            page = pdf_document[-1]
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='JPEG')
            img_bytes = img_byte_arr.getvalue()
            page.insert_image(page.rect, stream=img_bytes)

# Save the searchable PDF to SMB share
output_path = f"\\\\{server_ip}\\{share_name}\\{output_pdf}"
with smbclient.open_file(output_path, mode='wb') as output_file:
    output_file.write(pdf_document.write())

pdf_document.close()

print(f"Searchable PDF saved as {output_pdf}")
print(f"B&W images saved in folder: {bw_image_folder}")