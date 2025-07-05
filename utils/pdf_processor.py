import os
import fitz
from .helpers import ensure_dir_exists, generate_output_filename


def process_pdf(uploaded_file, output_folder):
    """
    Split uploaded PDF into single-page PDFs and save them to output_folder.
    """
    # Ensure the output directory exists
    ensure_dir_exists(output_folder)

    # Read the uploaded file into memory
    file_bytes = uploaded_file.read()
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    total_pages = doc.page_count

    # Loop through each page and save as a new PDF
    for i in range(total_pages):
        new_doc = fitz.open()
        new_doc.insert_pdf(doc, from_page=i, to_page=i)
        filename = generate_output_filename(i + 1, total_pages)
        filepath = os.path.join(output_folder, filename)
        new_doc.save(filepath)
        new_doc.close()

    doc.close() 