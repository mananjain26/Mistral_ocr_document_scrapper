import streamlit as st
from mistralai import Mistral
import os
from dotenv import load_dotenv
import tempfile
import time
from markdown_pdf import MarkdownPdf
from io import BytesIO
import markdown2
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit

# def convert_md_to_pdf(md_content):
#     import markdown2
#     import pdfkit
#     import tempfile

#     # Convert Markdown to HTML
#     html_content = markdown2.markdown(md_content)

#     # Save HTML to a temporary file
#     with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as temp_html:
#         temp_html.write(html_content.encode("utf-8"))
#         temp_html_path = temp_html.name

#     # Define wkhtmltopdf options
#     options = {
#         'enable-local-file-access': None  # Avoid protocol errors
#     }

#     # Convert HTML to PDF
#     pdf_path = temp_html_path.replace(".html", ".pdf")
#     pdfkit.from_file(temp_html_path, pdf_path, options=options)

#     return pdf_path

import markdown2
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit
import tempfile

def convert_md_to_pdf(md_content):
    # Convert Markdown to plain text
    html_content = markdown2.markdown(md_content)
    plain_text = html_content.replace('<p>', '').replace('</p>', '\n').replace('<br>', '\n').replace('<br />', '\n')

    # Create a temporary PDF file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
        temp_pdf_path = temp_pdf.name

    # Create PDF using ReportLab
    c = canvas.Canvas(temp_pdf_path, pagesize=LETTER)
    width, height = LETTER
    text_object = c.beginText(40, height - 40)
    text_object.setFont("Helvetica", 11)

    lines = simpleSplit(plain_text, 'Helvetica', 11, width - 80)
    for line in lines:
        if text_object.getY() < 40:  # Check for page overflow
            c.drawText(text_object)
            c.showPage()
            text_object = c.beginText(40, height - 40)
            text_object.setFont("Helvetica", 11)
        text_object.textLine(line)

    c.drawText(text_object)
    c.save()

    return temp_pdf_path



# Load environment variables (ensure MISTRAL_API_KEY is in your .env file)
load_dotenv()

# Get your API key
api_key = os.environ.get("MISTRAL_API_KEY")

# Initialize Mistral client
if api_key:
    client = Mistral(api_key=api_key)
else:
    st.error("MISTRAL_API_KEY not found in environment variables. Please set it in a .env file.")
    st.stop() # Stop the app if API key is missing

st.set_page_config(page_title="Mistral OCR PDF App", layout="centered")
st.title("📄 Mistral OCR for PDF Files")
st.markdown("Upload a PDF document, and I'll use Mistral's OCR to extract the text!")

# File uploader widget
uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

if uploaded_file is not None:
    st.write("File uploaded successfully!")
    st.write(f"File name: {uploaded_file.name}")
    st.write(f"File size: {uploaded_file.size / (1024 * 1024):.2f} MB")

    total_start_time = time.time() # Start total timer

    # Display a spinner while processing
    with st.spinner("Processing PDF with Mistral OCR... This might take a moment."):
        try:
            # Create a temporary file to save the uploaded content
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                temp_file_path = tmp_file.name

            # --- Step 1: Upload the PDF to Mistral's file storage ---
            step_start_time = time.time()
            st.info("Uploading PDF to Mistral file storage...")
            with open(temp_file_path, "rb") as f:
                uploaded_pdf_response = client.files.upload(
                    file={
                        "file_name": uploaded_file.name,
                        "content": f,
                    },
                    purpose="ocr"
                )
            step_end_time = time.time()
            st.success(f"File uploaded to Mistral: ID {uploaded_pdf_response.id} (Took {step_end_time - step_start_time:.2f} seconds)")
            st.markdown(f"**Uploaded File Details:**")
            st.json(uploaded_pdf_response.model_dump_json())

            # --- Step 2: Get a signed URL for the uploaded file ---
            step_start_time = time.time()
            st.info("Getting a signed URL for the uploaded file...")
            signed_url_response = client.files.get_signed_url(file_id=uploaded_pdf_response.id)
            step_end_time = time.time()
            st.success(f"Signed URL retrieved! (Took {step_end_time - step_start_time:.2f} seconds)")

            # --- Step 3: Process the document using the signed URL ---
            step_start_time = time.time()
            st.info("Initiating OCR process with the signed URL...")
            ocr_response = client.ocr.process(
                model="mistral-ocr-latest",
                document={
                    "type": "document_url",
                    "document_url": signed_url_response.url,
                },
                include_image_base64=False
            )
            step_end_time = time.time()
            st.success(f"OCR process completed! (Took {step_end_time - step_start_time:.2f} seconds)")

            # Display the OCR results
            st.subheader("OCR Results:")
            if ocr_response and ocr_response:
                st.text_area("Extracted Text:", ocr_response , height=400)
            else:
                st.warning("No text was extracted from the document.")

            # Optional: Display full response for debugging
            with st.expander("View Full OCR Response"):
                st.json(ocr_response.model_dump_json())
            
            
                # --- Generate PDF using markdown-pdf ---
            st.info("Generating PDF from markdown content using markdown-pdf...")
            
                # Combine markdown from all pages
            combined_markdown = "\n\n---\n\n".join([page.markdown for page in ocr_response.pages])

            # Convert the combined markdown to PDF
            pdf_path = convert_md_to_pdf(combined_markdown)

            # Load PDF into buffer for download
            with open(pdf_path, "rb") as pdf_file:
                pdf_buffer = BytesIO(pdf_file.read())

            # Streamlit download button
            st.download_button(
                label="Download Extracted Markdown as PDF",
                data=pdf_buffer.getvalue(),
                file_name="extracted_text.pdf",
                mime="application/pdf"
            )
            # Display success message       
            st.success("PDF generated from markdown and ready for download!")

        except Exception as e:
            st.error(f"An error occurred during OCR processing: {e}")
            st.exception(e) # Show full traceback for debugging

        finally:
            # Clean up the temporary file
            if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            # Optional: Delete the file from Mistral's storage if it's no longer needed
            # client.files.delete(file_id=uploaded_pdf_response.id) # Uncomment if you want to delete immediately

    total_end_time = time.time()
    st.info(f"**Total processing time: {total_end_time - total_start_time:.2f} seconds**")

else:
    st.info("Please upload a PDF file to begin OCR.")

st.sidebar.header("About This App")
st.sidebar.info(
    "This Streamlit application demonstrates how to perform OCR on PDF files "
    "using the Mistral AI API. It uploads the PDF to Mistral's file storage, "
    "retrieves a signed URL, and then uses that URL for the OCR process."
)
st.sidebar.markdown("[Mistral AI Website](https://mistral.ai/)")