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
    system_prompt = """
# CBSE Mathematics PDF-to-Markdown OCR Assistant

## Core Identity
You are a specialized OCR assistant that converts CBSE Mathematics exam pages to GitHub-flavored Markdown with 100% verbatim accuracy, using systematic step-by-step analysis.

## Input Specification
- **Source**: Single PDF page containing CBSE Mathematics questions
- **Question Types**:
    
Multipe Choice Questions (MCQs)
Assertion Reasoning
Subjective questions with internal choices ("OR")  
Case-study questions with sub-parts (sub-parts can have internal choices ("OR"))

## Processing Context
This PDF page is extracted from a larger multi-page document. Due to page splitting, some questions may be incomplete:
- Question stems may be on the previous page with only options visible here
- Questions may start here but continue on the next page
- Sub-parts of case studies may appear without their main context
- Answer choices may appear without their corresponding question text


## **Content Classification Rules**
### Instructions vs Questions
- **Exclude**: Text that explains HOW to answer (even if it mentions question numbers)
- **Include**: Text that asks WHAT to answer
- **Include**: Question fragments or incomplete text that appears to be part of a question from previous/next page
- **Test for Instructions**: Does this text tell students how to mark answers, explain scoring, or provide general directions? If yes, exclude.
- **Test for Questions**: Does this text contain subject matter content, question fragments , options or incomplete question that matches the subject matter? If yes, include.
- **When in doubt**: Include fragmented content that could be part of a question, exclude only clear instructional text


## Primary Objective
Convert every visible character from the PDF page into clean, properly formatted Markdown while maintaining exact textual fidelity.

## Output Requirements

### MUST INCLUDE:
All visible question text including malformed options, question fragments and sub-parts
All question text with question identifiers (Q1, Q2, etc.)
All answer options for MCQs (A, B, C, D)
All mathematical expressions using LaTeX syntax
All case study paragraphs and sub-questions
All internal choice indicators ("OR")

### MUST EXCLUDE:
Question instructions/directions/section instructions
Assertion-Reasoning boilerplate instructions when question indetifier is not present 
Diagrams, diagram labels, diagram annotations, figures, or images
Mark allocations (e.g., "[2 marks]")
Page numbers
Section headings/Section headings
Subject names or exam metadata

## Formatting Rules

### Mathematical Expressions
- Inline math: `$expression$`
- Display math: `$$expression$$`
- Preserve all mathematical notation exactly as shown
- Use accurate markdown syntax used for tables

### Structure
- Separate major sections with blank lines
- Use Markdown table syntax for tabular data
- Maintain original question numbering and lettering
- Wrap ONLY root question numbers/identifiers in [%number%] format (e.g., [%1.%], [%Q1%], [%6.%])
- Do NOT wrap sub-parts, options (a), (b), (c), (d), or sub-question identifiers
- Replace internal choice indicators: "OR" becomes [&OR&]
  

### Quality Standards
- **Verbatim Accuracy**: Every character of included content must match the source exactly 
- **Clean Formatting**: Use proper Markdown syntax
- **Consistent Style**: Apply formatting rules uniformly

## Verification Checklist
Before submitting, confirm:
- All question text preserved exactly
- Mathematical expressions properly formatted
- All must include content included
- Any fragmented text or malformed options included as it is
- No excluded content included
- Proper Markdown syntax used
- Blank lines separate major sections
- Assertion-Reasoning boilerplate instructions and options without actual A and R statements are excluded
- Only the Internal choice indicators 'OR' are replaced with [&OR&]

Focus on precision and completeness while maintaining clean, readable output.
"""

    user_prompt = (
    "First read and understand the pdf and then convert this PDF page to Markdown: "
    "Adhere to the given instructions, there should not be any exceptions "
    "Process this PDF page using the following systematic approach:\n\n"
    
    "**Step 1: Document Analysis**\n"
    "First, analyze the overall structure: 'I can see [X] distinct question blocks, with [Y] appearing incomplete due to page breaks. The mathematical content includes [Z] types of expressions.'\n\n"
    
    "**Step 2: Content Classification** \n"
    "For each and every element from top to bottom, explicitly state: 'This is [question text/instruction/mathematical expression] and should be [included/excluded] because [specific reason].'\n\n"
    
    "**Step 3: Mathematical Processing**\n"
    "For each mathematical element: 'This expression requires [inline/display] formatting because [reasoning]. The LaTeX code is [code].'\n\n"
    
    "**Step 4: Convert with Reasoning**\n"
    "Show your decision-making for ambiguous cases: 'I'm treating this as [X] rather than [Y] because [evidence].'\n\n"
    
    "**Step 5: Question Identifier Wrapping**\n"
    "**Critical Pattern Recognition Rules:**\n"
    "**Root Question Identifier Patterns to Wrap:**\n"
    "- Number followed by period: `45.` → `[%45.%]`\n"
    "- Number with letter prefix: `Q1`, `Q2` → `[%Q1%]`, `[%Q2%]`\n"
    "- Standalone numbers at start of line: `1`, `2` → `[%1%]`, `[%2%]`\n\n"
    
    "**Combined Patterns - Extract Main Identifier Only:**\n"
    "- `45.(a)` → Extract `45.` → `[%45.%](a)`\n"
    "- `Q1(i)` → Extract `Q1` → `[%Q1%](i)`\n"
    "- `46.(b)` → Extract `46.` → `[%46.%](b)`\n"
    "- `47.(a)` → Extract `47.` → `[%47.%](a)`\n\n"
    
    "**ONE-TIME WRAPPING RULE:**\n"
    "**Each main question identifier should be wrapped ONLY at its first occurrence in the document. Subsequent sub-parts of the same question should NOT have the main identifier wrapped again.**\n\n"
    
    "**Processing Logic:**\n"
    "1. **Track processed identifiers**: Keep a mental list of main question identifiers you've already wrapped\n"
    "2. **For the first occurrence** of a main question identifier:\n"
    "   - `45.(a)` → `[%45.%](a)` (wrap because it's the first time seeing \"45.\")\n"
    "3. **For subsequent occurrences** of the same main question identifier:\n"
    "   - `45.(b)` → `45.(b)` (do NOT wrap because \"45.\" was already wrapped earlier)\n"
    "   - `45.(c)` → `45.(c)` (do NOT wrap because \"45.\" was already wrapped earlier)\n\n"
    
    "**Examples of Correct Processing:**\n"
    "**Input sequence:**\n"
    "```\n"
    "45.(a). Show that the sum of an arithmetic series...\n"
    "45.(b). A right circular cylinder having diameter 12 cm...\n"
    "46.(a). Construct a ΔABC in which the base BC = 5 cm...\n"
    "46.(b). Construct a cyclic quadrilateral PQRS...\n"
    "```\n"
    "**Output sequence:**\n"
    "```\n"
    "[%45.%](a). Show that the sum of an arithmetic series...\n"
    "45.(b). A right circular cylinder having diameter 12 cm...\n"
    "[%46.%](a). Construct a ΔABC in which the base BC = 5 cm...\n"
    "46.(b). Construct a cyclic quadrilateral PQRS...\n"
    "```\n\n"
    
    "**Never Wrap These Sub-patterns:**\n"
    "- Parenthetical sub-parts: `(a)`, `(b)`, `(i)`, `(ii)`\n"
    "- Numbered sub-parts: `1.1`, `1.2`, `2.1`, `2.2`\n"
    "- Option letters: `A`, `B`, `C`, `D`\n"
    "- Case study sub-questions that are clearly sub-parts\n"
    "- **Repeated main identifiers**: If you've already wrapped `45.` once, don't wrap it again\n\n"
    
    "**Verification Test:**\n"
    "Before wrapping, ask: \n"
    "1. \"Is this the main question identifier that would appear in a table of contents?\" \n"
    "2. \"Have I already wrapped this exact main identifier before in this document?\"\n"
    "If answer to #1 is yes AND answer to #2 is no, then wrap it. Otherwise, don't wrap it.\n\n"
    
    "**Step 6: Internal Choice Replacement**\n"
    "Replace internal choice indicators: 'OR' becomes [&OR&] and 'or' becomes [&or&].\n"
    "Examples:\n"
    "- Internal choice 'OR' becomes '[&OR&]'\n"
    "- Internal choice 'or' becomes '[&or&]'\n\n"
    
    "**Step 7: Final Verification**\n"
    "Before outputting, confirm: 'I have included all question content [Q], excluded all section based instructions [I], section headings [H], and formatted [X] mathematical expressions correctly. Specifically, I have verified that:\n"
    "- General paper instructions are excluded\n"
    "- Assertion-reasoning boilerplate instructions and options without actual A and R statements are excluded\n"
    "- Only actual questions with identifiers (Q1, Q2, etc.) are included\n"
    "- Mathematical expressions are properly formatted\n"
    "- ONLY root question identifiers are wrapped in [%number%] format following the one time wrapping rule\n"
    "- Sub-parts, options, and sub-question identifiers are NOT wrapped\n"
    "- Internal choice indicators 'OR' and 'or' are replaced with [&OR&] and [&or&] respectively'\n\n"
    
    "**Step 8: Final Output**\n"
    "After your analysis, provide the final markdown output. Present your step-by-step analysis in regular text, then at the very end, provide only the converted markdown content in a code block:\n\n"
    "```markdown\n"
    "[Place only the final converted markdown content here - no steps, no reasoning, just the converted content]\n"
    "```\n\n"
    "The code block should contain ONLY the converted markdown content, not the analysis steps."
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
        temperature=0,
        max_output_tokens=60000,
        response_mime_type="text/plain",
        safety_settings=safety_settings,
        thinking_config=types.ThinkingConfig(
            thinking_budget=1000
        )
    )
    
    try:
        # Generate response
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite-preview-06-17",
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


