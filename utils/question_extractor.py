import os
from api.gemini import generate_markdown_from_pdf
from typing import List, Dict

def process_pdf_pages(folder_path: str) -> List[Dict[str, str]]:
    """
    Process PDF pages in a folder and generate markdown for each page.
    
    Args:
        folder_path (str): Path to the folder containing PDF files
    
    Returns:
        List[Dict[str, str]]: List of dictionaries with page filename and markdown content
    """
    results = []
    for filename in os.listdir(folder_path):
        if filename.endswith('.pdf'):
            file_path = os.path.join(folder_path, filename)
            # Generate markdown for the page
            markdown_content = generate_markdown_from_pdf(file_path)
            results.append({"page": filename, "result": markdown_content})
    return results

def extract_questions_from_folder(folder_path: str) -> List[Dict[str, str]]:
    """
    Extract markdown content from all PDF files in a given folder.
    
    Args:
        folder_path (str): Path to the folder containing PDF files
    
    Returns:
        List[Dict[str, str]]: List of dictionaries with page filename and markdown content
    """
    return process_pdf_pages(folder_path)

def extract_questions_from_pdf(file_path: str) -> str:
    """
    Extract questions from a PDF using Gemini markdown generation.
    
    Args:
        file_path (str): Path to the PDF file
    
    Returns:
        str: Markdown content of the PDF
    """
    markdown_content: str = generate_markdown_from_pdf(file_path)
    return markdown_content 