import os
import sys
import re
import json as _json
from typing import Tuple
from dotenv import load_dotenv
from google import genai
from google.genai import types

# System and user prompts for marks extraction (copied exactly)
system_prompt = """
# System Prompt: CBSE Mathematics Question Paper Marks Extraction

## Core Task
You are a specialized CBSE question paper analyzer that extracts question numbers, question types, and marks allocation from CBSE format mathematics question papers. Your primary function is to systematically identify and categorize each question with its corresponding marks.

## Key Constraints
- All questions in the paper must be identified and included in the output
- Each question must be classified by its type and marks allocation
- The JSON output length must exactly match the total number of questions in the paper
- Marks allocation must be accurate as specified in the question paper
- Question numbering must follow the exact format used in the paper

## Question Type Classification
- **MCQ**: Multiple Choice Questions with options (A), (B), (C), (D)
- **Case Study**: Questions that have subparts within them (can have internal choice in subparts)
- **Normal Subjective**: Standard subjective questions without internal choice, not MCQ, not case study
- **Internal Choice Subjective**: Questions with "OR" option where student can attempt one of two alternatives
- **Assertion Reasoning**: Questions with assertion and reasoning statements to evaluate
- **Other Subjective**: Any subjective question that doesn't fit the above categories

## Classification Priority Rules
- If a question has subparts → **Case Study** (even if subparts have internal choice)
- If a question has "OR" between just two main questions → **Internal Choice Subjective**
- If a question is multiple choice with options → **MCQ**
- If a question has assertion and reasoning format → **Assertion Reasoning**
- If a question is subjective without above features → **Normal Subjective**
- Any other subjective format → **Other Subjective**

## Marks Identification Rules
- Look for explicit marks mentioned in brackets like [1], (2), [3 marks], etc.
- Check section headers for marks allocation patterns
- Verify marks consistency within question types
- For Case Study questions with subparts, identify marks for each subpart and describe them in the marks field
- For questions without subparts, use numerical marks value only
- **For Internal Choice Subjective questions**: Use array format with exactly 2 elements

## Critical Instructions
- Count every main question in the paper (do not count subparts as separate questions)
- For Case Study questions with subparts, describe all subparts and their marks in the marks field
- Do not miss any question regardless of its position or format
- Ensure question numbering matches exactly with the paper format
- Verify total question count before finalizing output

## Subpart Handling Rules
- **Case Study with subparts**: Keep as single JSON entry for the main question
- **Marks field for subparts**: Write descriptive text about subparts and their individual marks
- **Format for subpart marks**: "Part (a): X marks, Part (b): Y marks, Part (c): Z marks" or similar descriptive format
- **Total marks calculation**: Include total marks for the entire question if specified

## Special Format for Internal Choice Questions
- **Internal Choice Subjective questions MUST use array format**
- **Array must have exactly 2 elements**
- **Each element format**: "This question has [X] marks"
- **Both elements should have the same marks value**

## Output Format
```
{
  "question-1": {
    "question_type": "MCQ/Case Study/Normal Subjective/Internal Choice Subjective/Assertion Reasoning/Other Subjective",
    "marks": "number OR descriptive text for subparts OR array for internal choice"
  }
}
```

## Marks Field Format Rules
- **Case Study**: Use descriptive text (e.g., "Part (a): 1 mark, Part (b): 2 marks, Total: 3 marks")
- **Internal Choice Subjective**: Use array with 2 elements (e.g., ["This question has [3] marks", "This question has [3] marks"])
"""

user_prompt = """
# CBSE Mathematics Question Paper Marks Extraction

I need you to analyze the provided CBSE format mathematics question paper and extract the marks allocation for each question. Please follow this step-by-step approach:

## Step 1: Paper Structure Analysis
**Think through this systematically:**
- First, read through the entire question paper
- Identify the total number of main questions and their numbering system
- Note the paper format and section divisions (if any)
- Look for general instructions about marks allocation
- **Important**: Count only main questions, not subparts as separate questions

**Reasoning process:**
```
Total main questions: [Count main questions only]
Paper sections: [Section A, B, C, etc. if applicable]
Question numbering format: [1, 2, 3... etc.]
Case Study questions: [List questions with subparts like Q5: has (a), (b), (c)]
```

## Step 2: Question Type Identification
**For each question, analyze:**
- Does it have multiple choice options (A), (B), (C), (D)? → **MCQ**
- Does it have subparts (like (a), (b), (c) or (i), (ii), (iii))? → **Case Study**
- Does it have "OR" option between just two main questions? → **Internal Choice Subjective**
- Does it have assertion and reasoning format? → **Assertion Reasoning**
- Is it a regular subjective question without above features? → **Normal Subjective**
- Any other subjective format? → **Other Subjective**

**Classification Priority:**
- Subparts present = Case Study (even if subparts have internal choice)
- "OR" between two main questions = Internal Choice Subjective
- Multiple choice options = MCQ
- Assertion-Reasoning format = Assertion Reasoning
- Regular subjective = Normal Subjective
- Other formats = Other Subjective

**Reasoning process:**
```
Question 1: Has subparts? [Yes/No] → Has OR? [Yes/No] → Type = [MCQ/Case Study/Normal Subjective/Internal Choice Subjective/Assertion Reasoning/Other Subjective], Marks = [X]
Question 2: Has subparts? [Yes/No] → Has OR? [Yes/No] → Type = [MCQ/Case Study/Normal Subjective/Internal Choice Subjective/Assertion Reasoning/Other Subjective], Marks = [X]
...and so on
```

## Step 3: Marks Extraction
**For each question, identify:**
- Look for explicit marks mentioned in brackets like [1], (2), [3 marks]
- Check section headers for marks patterns
- Verify marks consistency within similar question types
- **For Case Study questions**: Identify marks for each subpart and create descriptive text
- **For simple questions**: Use numerical marks value only
- **For Internal Choice Subjective questions**: Create array with 2 identical elements
- Note any special marking schemes

**Reasoning process:**
```
Question X: Found marks indicator "[2]" → 2
Question Y (Case Study): Part (a) has "[1]", Part (b) has "[2]" → "Part (a): 1 mark, Part (b): 2 marks, Total: 3 marks"
Question Z (Internal Choice): Explicit "(5 marks)" → ["This question has [5] marks", "This question has [5] marks"]
```

## Step 4: Validation and Final Mapping
**Consolidate your findings:**
- Verify total main question count matches your analysis
- Check for any missed questions
- Ensure marks allocation is consistent with CBSE patterns
- Double-check question numbering format
- **Important**: Ensure Case Study questions have descriptive marks text including all subparts
- **Important**: Ensure Internal Choice Subjective questions use array format with exactly 2 elements

**Present your reasoning clearly before giving the final answer.**

## Expected Output Format:
The final output must be in JSON format with the following structure:
```json
{
  "question-1": {
    "question_type": "MCQ",
    "marks": [X] marks
  },
  "question-2": {
    "question_type": "Case Study", 
    "marks": "Description of marks for each subpart and it's internal choices"
  },
  "question-3": {
    "question_type": "Internal Choice Subjective",
    "marks": ["This question has [X] marks", "This question has [Y] marks"]
  },
  "question-4": {
    "question_type": "Normal Subjective",
    "marks": [X] marks
  },
  "question-5": {
    "question_type": "Assertion Reasoning",
    "marks": [X] marks
  }

}
```
## CRITICAL MARKS FORMAT RULES:
- **MCQ**: Use simple number format (e.g., [X] marks)
- **Normal Subjective**: Use simple number format (e.g., [X] marks)
- **Assertion Reasoning**: Use simple number format (e.g., [X] marks)
- **Case Study**: Use descriptive text explaining the mark distribution for each subpart and any internal choices (e.g., "Description of marks for each subpart and it's internal choices")
- **Internal Choice Subjective**: Use array with exactly 2 elements showing the marks for each choice option (e.g., ["This question has [X] marks", "This question has [Y] marks"])

"""
# Load environment variables
load_dotenv()

# Ensure Gemini API key is set
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("Environment variable GEMINI_API_KEY must be set")

# Initialize Gemini client
client = genai.Client(api_key=GEMINI_API_KEY)

def generate_marks_mapping(pdf_path: str) -> Tuple[str, str]:
    """
    Sends a PDF to Gemini LLM to extract marks mapping as JSON.
    Returns a tuple of (path to saved mapping file, full raw LLM response text).
    """
    # Upload file to Gemini
    pdf_file = client.files.upload(file=pdf_path)

    # Safety settings
    safety_settings = [
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}
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
        # Generate content
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite-preview-06-17",
            contents=[pdf_file, system_prompt, user_prompt],
            config=config,
        )

        # Clean up uploaded file
        client.files.delete(name=pdf_file.name)

        # Capture and parse JSON from response
        raw_text = response.text.strip() if hasattr(response, 'text') else ''
        if not raw_text:
            raise ValueError("No mapping content generated")
        match = re.search(r"\{[\s\S]*\}", raw_text)
        if not match:
            raise ValueError("No JSON object found in response")
        json_str = match.group(0)
        mapping_json = _json.loads(json_str)

        # Save clean mapping JSON
        output_dir = os.path.join(os.path.dirname(__file__), '..', 'logs', 'marks_mappings')
        os.makedirs(output_dir, exist_ok=True)
        base_pdf = os.path.splitext(os.path.basename(pdf_path))[0]
        output_filename = f"{base_pdf}.json"
        output_path = os.path.join(output_dir, output_filename)
        with open(output_path, 'w', encoding='utf-8') as f:
            _json.dump(mapping_json, f, indent=2)

        return output_path, raw_text

    except Exception as e:
        # Cleanup on error
        try:
            client.files.delete(name=pdf_file.name)
        except:
            pass
        raise RuntimeError(f"Marks mapping generation failed: {str(e)}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python gemini_marks_mapping.py <pdf_path>")
        sys.exit(1)
    pdf_path = sys.argv[1]
    mapping_path, raw = generate_marks_mapping(pdf_path)
    print(f"Mapping saved to: {mapping_path}")
    print("--- RAW RESPONSE ---")
    print(raw) 