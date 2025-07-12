import os
import sys
from typing import Tuple
from dotenv import load_dotenv
from google import genai
from google.genai import types
from api.prompt.prompt_figure_map.prompt import system_prompt, user_prompt

# Load environment variables
load_dotenv()

# Ensure Gemini API key is set
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("Environment variable GEMINI_API_KEY must be set")

# Initialize Gemini client
client = genai.Client(api_key=GEMINI_API_KEY)

def generate_diagram_mapping(pdf_path: str, image_path: str) -> Tuple[str, str]:
    """
    Sends a PDF and a diagram image to Gemini LLM to generate a mapping JSON.
    Returns a tuple of (path to the saved mapping file, full raw LLM response text).
    """
    # Upload files to Gemini
    pdf_file = client.files.upload(file=pdf_path)
    img_file = client.files.upload(file=image_path)

    # Safety settings
    safety_settings = [
        {
            "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
            "threshold": "BLOCK_MEDIUM_AND_ABOVE",
        }
    ]

    # Generation configuration
    config = types.GenerateContentConfig(
        temperature=0,
        max_output_tokens=60000,
        response_mime_type="text/plain",
        safety_settings=safety_settings,
        thinking_config=types.ThinkingConfig(thinking_budget=512)
    )

    try:
        # Send to Gemini model
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite-preview-06-17",
            contents=[pdf_file, img_file, system_prompt, user_prompt],
            config=config,
        )

        # Clean up uploaded files
        client.files.delete(name=pdf_file.name)
        client.files.delete(name=img_file.name)

        # Capture full raw response text
        raw_text = response.text.strip() if hasattr(response, 'text') else ''
        if not raw_text:
            raise ValueError("No mapping content generated")
        # Find JSON object in the raw text
        import re, json as _json
        match = re.search(r"\{[\s\S]*\}", raw_text)
        if not match:
            raise ValueError("No JSON object found in mapping response")
        json_str = match.group(0)
        try:
            mapping_json = _json.loads(json_str)
        except _json.JSONDecodeError as jde:
            raise ValueError(f"Failed to decode JSON: {jde}")

        # Save clean mapping JSON
        output_dir = os.path.join(os.path.dirname(__file__), '..', 'logs', 'diagram_mappings')
        os.makedirs(output_dir, exist_ok=True)
        base_pdf = os.path.splitext(os.path.basename(pdf_path))[0]
        base_img = os.path.splitext(os.path.basename(image_path))[0]
        output_filename = f"{base_pdf}__{base_img}.json"
        output_path = os.path.join(output_dir, output_filename)
        with open(output_path, 'w', encoding='utf-8') as f:
            _json.dump(mapping_json, f, indent=2)

        # Return both the file path and the raw response text
        return output_path, raw_text

    except Exception as e:
        # Attempt cleanup on error
        try:
            client.files.delete(name=pdf_file.name)
        except:
            pass
        try:
            client.files.delete(name=img_file.name)
        except:
            pass
        raise RuntimeError(f"Diagram mapping generation failed: {str(e)}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python gemini_diagram_mapping.py <pdf_path> <image_path>")
        sys.exit(1)
    pdf_path = sys.argv[1]
    image_path = sys.argv[2]
    mapping_path, raw = generate_diagram_mapping(pdf_path, image_path)
    print(f"Mapping saved to: {mapping_path}")
    print("--- RAW RESPONSE ---")
    print(raw) 