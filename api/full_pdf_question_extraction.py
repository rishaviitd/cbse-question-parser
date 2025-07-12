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

def extract_markdown_from_response(response_text: str) -> str:
    """
    Extract markdown content from Gemini response that contains a ```markdown code block.
    
    Args:
        response_text (str): Raw response text from Gemini
    
    Returns:
        str: Extracted markdown content
    """
    # Look for markdown code block patterns
    patterns = [
        r'```markdown\s*\n(.*?)\n```',  # Standard markdown block
        r'```\s*\n(.*?)\n```',         # Generic code block
        r'```markdown(.*?)```',         # Inline markdown block
    ]
    
    for pattern in patterns:
        match = re.search(pattern, response_text, re.DOTALL)
        if match:
            return match.group(1).strip()
    
    # If no code block found, look for content after a specific marker
    # Look for content after "```markdown" or similar indicators
    lines = response_text.split('\n')
    markdown_start = -1
    
    for i, line in enumerate(lines):
        if '```markdown' in line.lower():
            markdown_start = i + 1
            break
        elif line.strip() == '```' and i > 0 and any(keyword in lines[i-1].lower() for keyword in ['markdown', 'final', 'output']):
            markdown_start = i + 1
            break
    
    if markdown_start >= 0:
        # Find the end of the markdown block
        markdown_end = len(lines)
        for i in range(markdown_start, len(lines)):
            if lines[i].strip() == '```':
                markdown_end = i
                break
        
        # Extract the markdown content
        markdown_lines = lines[markdown_start:markdown_end]
        return '\n'.join(markdown_lines).strip()
    
    # If still no markdown found, return the original response
    # This handles cases where the response doesn't use code blocks
    return response_text.strip()

def extract_questions_from_pdf(pdf_path: str) -> tuple[str, str]:
    """
    Sends a PDF to Gemini LLM to extract questions only from CBSE Mathematics exam papers.
    
    Args:
        pdf_path (str): Path to the PDF file to be processed
    
    Returns:
        tuple[str, str]: Tuple containing:
            - Path to the generated Markdown file with extracted questions
            - Path to the raw response file from Gemini
    """
    # Initialize Gemini client
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    # Upload file to Gemini
    pdf_file = client.files.upload(file=pdf_path)
    
    # System prompt for question extraction
    system_prompt = """
# CBSE Mathematics Question Extraction Assistant

## Core Identity
You are a specialized question extraction assistant that converts CBSE Mathematics exam papers to clean Markdown format with 100% verbatim accuracy for questions only, excluding all instructional content and diagrams.

## Input Specification
- **Source**: CBSE Mathematics exam paper (any length, any number of questions)
- **Question Types**:
  - Multiple Choice Questions (MCQs) with options A, B, C, D
  - Assertion-Reason questions with statements A and R
  - Very Short Answer (VSA) questions with internal choices
  - Short Answer (SA) questions with internal choices
  - Long Answer (LA) questions with internal choices
  - Case-study questions with sub-parts and internal choices

## Primary Objective
Extract ONLY the questions from the exam paper, converting them to clean Markdown format while maintaining exact textual fidelity and proper question separation.

## Content Classification Rules

### MUST INCLUDE (Questions):
- All question text with question numbers (as they appear in the source)
- All answer options for MCQs (A), (B), (C), (D)
- All mathematical expressions and symbols
- All case study paragraphs and their sub-questions
- All internal choice alternatives marked with "OR"
- All sub-parts: (i), (ii), (iii), (a), (b), (c)
- All question fragments that contain subject matter content

### MUST EXCLUDE (Instructions/Metadata):
- General instructions ("Read the following instructions carefully")
- Any Table and it's content -EXCLUDE
- ALL diagram content, diagram labels, diagram annotations, figures, images, or visual elements
- Section headers ("SECTION A", "SECTION B", etc.)
- Section descriptions ("This section has X questions carrying Y marks each")
- Marking schemes and mark allocations ("[X marks]", "X×Y=Z")
- Page numbers and "P.T.O." indicators
- Assertion-Reason boilerplate instructions (when no actual A and R statements present)
- Drawing instructions unless part of the question itself
- Calculator usage instructions
- Subject names or exam metadata

## Formatting Rules

### Mathematical Expressions
- Inline math: `$expression$`
- Display math: `$$expression$$`
- Preserve all mathematical notation exactly as shown

### Structure and Tagging
- Preserve original question numbering exactly as shown in the source
- Replace internal choice indicators: "OR" becomes [%OR%]
- Add [####] immediately after each complete question ends
- Separate questions with blank lines
- Do NOT add any additional tags or formatting to question numbers

### Question Separation Logic
A question is considered "complete" when:
- All parts of an MCQ (question + options A,B,C,D) are included
- All sub-parts of a multi-part question are included
- Both alternatives of an OR question are included
- All sub-questions of a case study are included

## Diagram Handling
- **COMPLETELY IGNORE** all visual elements even if the question explicitly mentions to refer including:
  - Geometric figures and shapes
  - Graphs and charts
  - Diagrams and illustrations
  - Image annotations and labels
  - Figure captions
  - Any text that describes or references diagrams ("In the given figure...")

## Output Format Template
```markdown
1. [Complete question text]
(A) [option]
(B) [option]
(C) [option]
(D) [option]
[####]

2. [Complete question text]
[####]

15. (a) [Question part a]
[%OR%]
(b) [Question part b]
[####]

25. [Case study scenario description]
Based on the above given information, answer the following questions:
(i) [Sub-question i]
(ii) [Sub-question ii]
(iii) (a) [Sub-question iii part a]
[%OR%]
(iii) (b) [Sub-question iii part b]
[####]
```

## Quality Standards
- **Verbatim Accuracy**: Every character of question content must match the source exactly
- **Complete Extraction**: All questions must be extracted with no omissions
- **Clean Formatting**: Use proper Markdown syntax throughout
- **Consistent Tagging**: Apply [%OR%] and [####] tags uniformly
- **No Hallucinations**: Do not add, modify, or invent any content

## Verification Checklist
Before submitting, confirm:
- [ ] All questions extracted in sequential order as they appear in the source
- [ ] Each question ends with [####]
- [ ] Question numbers preserved exactly as shown (no additional tagging)
- [ ] All mathematical expressions properly formatted
- [ ] Internal choice "OR" replaced with [%OR%]
- [ ] Any table present in the question paper was excluded
- [ ] No instructional text included
- [ ] No diagram content or references included
- [ ] All case study scenarios and sub-questions included
- [ ] No marks/scoring information included
- [ ] Output is in clean Markdown format

## Critical Success Factors
1. **100% Question Coverage**: Every question must be extracted
2. **Zero Instruction Contamination**: No instructional text should appear in output
3. **Diagram Immunity**: Completely ignore all visual elements
4. **Exact Textual Fidelity**: Preserve every character of question content
5. **Proper Separation**: Each question clearly demarcated with [####]

Focus on precision, completeness, and clean Markdown output while maintaining absolute fidelity to the original question content.
"""

    # User prompt for question extraction
    user_prompt = """
# Chain of Thought Question Extraction Prompt

**TASK:** Extract ONLY the questions from a mathematics exam paper with precise formatting using systematic chain-of-thought reasoning.

**SYSTEMATIC PROCESSING APPROACH:**

## **Step 1: Initial Document Analysis**
First, analyze the overall structure: "I can see [X] total pages with [Y] distinct questions numbered from [start] to [end]. The document contains [Z] sections with [A] question types including MCQs, assertion-reason, case studies, and multi-part questions."

## **Step 2: Question Inventory and Mapping**
For comprehensive question identification: "I will now scan the entire document to create a complete question inventory:
- Questions 1-[X]: [Location/Section]
- Questions [Y]-[Z]: [Location/Section]
- Total question count: [Number]
- Question types identified: [MCQ/Long Answer/Case Study/etc.]"

## **Step 3: Element-by-Element Classification**
For each and every element from top to bottom, explicitly state: "This is [question text/instruction/header/page number] and should be [included/excluded] because [specific reason based on inclusion/exclusion criteria]."

**Inclusion Criteria Check:**
- "This element contains a question number [X] - INCLUDE"
- "This element contains question text following a number - INCLUDE"
- "This element contains answer options (A), (B), (C), (D) - INCLUDE"
- "This element contains sub-parts (i), (ii), (a), (b) - INCLUDE"
- "This element contains OR alternatives within a question - INCLUDE and TAG"
- "This element contains case study scenario for questions - INCLUDE"
- "This element contains assertion-reason statements - INCLUDE"

**Exclusion Criteria Check:**
- "This element is general instructions - EXCLUDE"
- "This element contains data tables within questions - EXCLUDE"
- "This element is section header (SECTION A/B/C) - EXCLUDE"
- "This element is marking scheme reference - EXCLUDE"
- "This element is page number/P.T.O. - EXCLUDE"
- "This element is marks allocation (2 marks, etc.) - EXCLUDE"

## **Step 4: Question-by-Question Deep Analysis**
For each identified question, perform detailed analysis:

**Question [Number] Analysis:**
"I am now processing Question [X]:
- Question identifier: [Exact format as shown]
- Question type: [MCQ/Long Answer/Case Study/Multi-part]
- Question text begins: '[First few words]'
- Question text ends: '[Last few words]'
- Contains options: [Yes/No] - If yes, options are: (A), (B), (C), (D)
- Contains sub-parts: [Yes/No] - If yes, sub-parts are: [list]
- Contains OR alternatives: [Yes/No] - If yes, mark for [%OR%] tagging
- Special mathematical notation: [List any complex symbols/equations]
- Reasoning for inclusion: [Why this entire block constitutes one complete question]"

## **Step 5: Content Boundary Determination**
For each question, clearly define boundaries: "Question [X] starts at '[exact text]' and ends at '[exact text]' before Question [X+1] begins. Everything between these boundaries belongs to Question [X], including [list specific elements like options, sub-parts, tables]."

## **Step 6: Mathematical Expression and Symbol Preservation**
For each mathematical element: "This expression '[content]' requires [specific formatting] because [reasoning]. Special characters identified: [list]. Greek letters present: [list]. Equations present: [list]. All symbols will be preserved exactly as shown."

## **Step 7: OR Alternative Identification and Tagging**
"Scanning for internal choice alternatives:
- Found 'OR' in Question [X] between '[option 1]' and '[option 2]' - Will replace with [%OR%]
- Found 'or' in Question [Y] between '[option 1]' and '[option 2]' - Will replace with [%or%]
- Total OR alternatives identified: [count]"

## **Step 8: Multi-part Question Structure Analysis**
For complex questions: "Question [X] has multiple parts:
- Main question: '[text]'
- Sub-part (a): '[text]'
- Sub-part (b): '[text]'
- Sub-part (i): '[text]'
- All parts belong to Question [X] and will be included together before [####] marker."

## **Step 9: Case Study Question Processing**
For case studies: "Case study identified for Questions [X]-[Y]:
- Scenario description: '[summary]'
- Questions based on scenario: [list]
- Will include complete scenario followed by all related questions before [####] marker."

## **Step 10: Quality Assurance Pre-Extraction**
Before extraction, verify: "I have identified [X] questions total. Each question has been analyzed for:
- ✓ Complete question text
- ✓ All options where applicable
- ✓ All sub-parts where applicable
- ✓ All OR alternatives tagged
- ✓ All mathematical symbols preserved
- ✓ All tables/data excluded
- ✓ Proper boundaries established
- ✓ No instructional content mixed in"

## **Step 11: Sequential Extraction with Verification**
"I will now extract each question in sequence, verifying accuracy:

**Extracting Question 1:**
- Question number: [as shown]
- Question text: '[complete text]'
- Options: [if applicable]
- Sub-parts: [if applicable]
- Verification: [confirms this is complete question 1]

**Extracting Question 2:**
- Question number: [as shown]
- Question text: '[complete text]'
- Options: [if applicable]
- Sub-parts: [if applicable]
- Verification: [confirms this is complete question 2]

[Continue for all questions...]"

## **Step 12: Final Verification Checklist**
Before outputting final result: "Final verification completed:
- [ ] All questions numbered sequentially from 1 to [final number]
- [ ] Each question ends with [####]
- [ ] No instructional text included
- [ ] All mathematical symbols preserved exactly
- [ ] OR alternatives tagged with [%OR%] where present
- [ ] Any table present in the question paper was excluded and not outputted
- [ ] Case study scenarios included with their questions
- [ ] No marks/scoring information included
- [ ] Question count matches initial inventory: [X] questions
- [ ] All sub-parts kept with their parent questions
- [ ] All answer options preserved exactly as shown"

## **Step 13: Final Output Generation**
"After completing the systematic analysis above, I will now provide the final extracted questions in the specified format. The output will contain ONLY the questions with their exact numbering, complete content, and proper [####] markers."

**REASONING DISPLAY REQUIREMENT:**
Present your complete step-by-step analysis and reasoning in regular text first, showing all the decision-making process, classifications, and verifications from Steps 1-12. Then, at the very end, provide only the final extracted questions in a markdown code block.

**OUTPUT FORMAT:**
```
1. [Complete question text]
(A) [option]
(B) [option]
(C) [option]
(D) [option]
[####]

2. [Complete question text]
[####]

21. (a) [Question part a]
[%OR%]
(b) [Question part b]
[####]
```

**FINAL PRESENTATION FORMAT:**
After your complete analysis, provide the final extracted questions using this exact format:

```markdown
[Place only the final extracted questions here - no steps, no reasoning, just the extracted questions with proper numbering and [####] markers]
```

**ACCURACY REQUIREMENT:** This systematic approach ensures 100% accuracy with no omissions, no additions, and no modifications to the original content. Every step must be completed before proceeding to the next, ensuring comprehensive analysis and perfect extraction. The markdown code block should contain ONLY the extracted questions, not the analysis steps.
"""
    
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
        # thinking_config=types.ThinkingConfig(
        #     thinking_budget=1000
        # )
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
        raw_response = response.text.strip() if hasattr(response, 'text') else ''
        
        if not raw_response:
            raise ValueError("No response content generated")
        
        # Extract markdown content from code block (clean version for questions file)
        markdown_text = extract_markdown_from_response(raw_response)
        
        # Determine output path in full_pdf_questions directory
        base_dir = os.path.join(os.path.dirname(__file__), '..', 'logs', 'full_pdf_questions')
        os.makedirs(base_dir, exist_ok=True)
        
        # Use the exact original filename with .md extension
        base_filename = os.path.basename(pdf_path).replace('.pdf', '')
        output_filename = f"{base_filename}.md"
        raw_output_filename = f"{base_filename}_raw_response.txt"
        
        output_path = os.path.join(base_dir, output_filename)
        raw_output_path = os.path.join(base_dir, raw_output_filename)
        
        # Save extracted markdown to file (clean version without code blocks)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown_text)
        
        # Save raw response to file (original response with code blocks preserved)
        with open(raw_output_path, 'w', encoding='utf-8') as f:
            f.write(raw_response)
        
        return output_path, raw_output_path
    
    except Exception as e:
        # Ensure file is deleted even if an error occurs
        try:
            client.files.delete(name=pdf_file.name)
        except:
            pass
        
        raise RuntimeError(f"Question extraction failed: {str(e)}")

if __name__ == "__main__":
    # Quick test: replace 'test_paper.pdf' with your actual PDF path
    questions_path, raw_path = extract_questions_from_pdf("test_paper.pdf")
    print(f"Questions extracted and saved to: {questions_path}")
    print(f"Raw response saved to: {raw_path}") 