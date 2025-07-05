import os
import re
import hashlib
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

# Environment variable for your Gemini API key
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("Environment variable GEMINI_API_KEY must be set")

def generate_markdown_from_pdf(pdf_path: str) -> str:
    """
    Sends a one-page PDF to Gemini LLM to generate Markdown content.
    
    Args:
        pdf_path (str): Path to the PDF file to be processed
    
    Returns:
        str: Path to the generated Markdown file
    """
    # Initialize Gemini client
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    # Upload file to Gemini
    pdf_file = client.files.upload(file=pdf_path)
    
    # Prepare prompts
    system_prompt = """You are a Markdown converter for PDF pages containing **CBSE Mathematics exam questions**. Reproduce the PDF's content exactly in Markdown format except diagrams
**Apply every rule below—no exceptions:**
• Preserve all text, characters, and line breaks  
• Use Markdown syntax for headings, lists, tables, etc.  
• Render mathematical expressions with LaTeX:  
    – Inline math: `$…$`  
    – Display math: `$$…$$`  
• Separate major sections with a blank line  
• The PDF contains only these question types:  
    – MCQs  
    - Assertion Reasoning
    – Subjective questions with internal choices ("OR")  
    – Case-study questions with an introductory paragraph and sub-parts (sub-parts may also include internal choices ("OR"))"""

    user_prompt = (
        "Convert this PDF page to clean, precise Markdown."
        "Preserve exact content, formatting, and structure."
        "Use standard Markdown syntax for all elements."
        "First check at the start of the page if there is a main question identifier, if there is no main question identifier, then start with [%missing_question_identifier%]",
        "Main Question identifier should be outputted in the format [%<quetion_identifier>%] only",
        "Children of the main question identifier should never be tagged with [%%]"
        "Produce output ready for direct rendering in a React UI.",
        "Only print the questions themselves—leave out everything else, no instructions no section headings ,no page numbers, no mark allocations no subject name or other metadata"
        "Do not ouptut assertion reasoning question instructions because that always the same across all question papers"
    )
    
    # Set up safety settings
    safety_settings = [
        {
            "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
            "threshold": "BLOCK_MEDIUM_AND_ABOVE",
        }
    ]
    
    # Configure generation with explicit thinking tokens
    config = types.GenerateContentConfig(
        temperature=0.3,
        max_output_tokens=10000,
        response_mime_type="text/plain",
        safety_settings=safety_settings,
        thinking_config=types.ThinkingConfig(
            thinking_budget=2000  # Explicitly set thinking tokens to 512
        )
    )
    
    try:
        # Generate response
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[pdf_file, system_prompt, user_prompt],
            config=config,
        )
        
        # Clean up uploaded file
        client.files.delete(name=pdf_file.name)
        
        # Extract plain text markdown
        markdown_text = response.text.strip() if hasattr(response, 'text') else ''
        
        if not markdown_text:
            raise ValueError("No markdown content generated")
        
        # Determine output path in gemini_questions directory
        base_dir = os.path.join(os.path.dirname(__file__), '..', 'logs', 'gemini_questions')
        os.makedirs(base_dir, exist_ok=True)
        
        # Use the exact original filename with .md extension
        output_filename = os.path.basename(pdf_path).replace('.pdf', '.md')
        output_path = os.path.join(base_dir, output_filename)
        
        # Save markdown to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown_text)
        
        return output_path
    
    except Exception as e:
        # Ensure file is deleted even if an error occurs
        try:
            client.files.delete(name=pdf_file.name)
        except:
            pass
        
        raise RuntimeError(f"Markdown generation failed: {str(e)}")

if __name__ == "__main__":
    # Quick test: replace 'page_001.pdf' with your actual PDF path
    result = generate_markdown_from_pdf("page_001.pdf")
    print(f"Markdown saved to: {result}")
