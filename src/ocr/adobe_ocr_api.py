import os
import logging
from adobe.pdfservices.operation.auth.service_principal_credentials import ServicePrincipalCredentials
from adobe.pdfservices.operation.exception.exceptions import ServiceApiException, ServiceUsageException, SdkException
from adobe.pdfservices.operation.io.cloud_asset import CloudAsset
from adobe.pdfservices.operation.io.stream_asset import StreamAsset
from adobe.pdfservices.operation.pdf_services import PDFServices
from adobe.pdfservices.operation.pdf_services_media_type import PDFServicesMediaType
from adobe.pdfservices.operation.pdfjobs.jobs.ocr_pdf_job import OCRPDFJob
from adobe.pdfservices.operation.pdfjobs.params.ocr_pdf.ocr_params import OCRParams
from adobe.pdfservices.operation.pdfjobs.params.ocr_pdf.ocr_supported_locale import OCRSupportedLocale
from adobe.pdfservices.operation.pdfjobs.params.ocr_pdf.ocr_supported_type import OCRSupportedType
from adobe.pdfservices.operation.pdfjobs.result.ocr_pdf_result import OCRPDFResult
from dotenv import load_dotenv
import fitz  # PyMuPDF


logging.basicConfig(level=logging.INFO)


class AdobeOCR():
    def ocr(self, input_path: str, output_path: str, language: str):
        # Load environment variables from .env file
        load_dotenv()

        try:
            with open(input_path, 'rb') as file:
                input_stream = file.read()

            # Initial setup, create credentials instance
            credentials = ServicePrincipalCredentials(
                client_id=os.getenv('ADOBE_CLIENT_ID'),
                client_secret=os.getenv('ADOBE_CLIENT_SECRET'),
            )

            # Creates a PDF Services instance
            pdf_services = PDFServices(credentials=credentials)

            # Creates an asset(s) from source file(s) and upload
            input_asset = pdf_services.upload(input_stream=input_stream,
                                              mime_type=PDFServicesMediaType.PDF)

            ocr_pdf_params = OCRParams(
                ocr_locale=OCRSupportedLocale[language],
                ocr_type=OCRSupportedType.SEARCHABLE_IMAGE
            )

            # Creates a new job instance
            ocr_pdf_job = OCRPDFJob(input_asset=input_asset, ocr_pdf_params=ocr_pdf_params)

            # Submit the job and gets the job result
            location = pdf_services.submit(ocr_pdf_job)
            pdf_services_response = pdf_services.get_job_result(location, OCRPDFResult)

            # Get content from the resulting asset(s)
            result_asset: CloudAsset = pdf_services_response.get_result().get_asset()
            stream_asset: StreamAsset = pdf_services.get_content(result_asset)

            # Creates an output stream and copy stream asset's content to it
            with open(output_path, "wb") as file:
                file.write(stream_asset.get_input_stream())

        except (ServiceApiException, ServiceUsageException, SdkException) as e:
            logging.exception(f'Exception encountered while executing operation: {e}')

    def extract_images_from_pdf(self, input_path: str, output_path: str):

        # Open the PDF file
        pdf_document = fitz.open(input_path)

        # Get the first page
        page = pdf_document[0]

        # Extract the images from the first page
        image_list = page.get_images(full=True)

        if image_list:
            # Get the first image
            xref = image_list[0][0]
            base_image = pdf_document.extract_image(xref)
            image_bytes = base_image["image"]

            # Write the image to the output path
            with open(output_path, "wb") as image_file:
                image_file.write(image_bytes)
        else:
            logging.info("No images found on the first page.")

        # Close the PDF document
        pdf_document.close()





if __name__ == "__main__":
    adobe_ocr = AdobeOCR()
    adobe_ocr.ocr('./ocrInput.pdf', 'output/OcrPDFWithOptions.pdf')