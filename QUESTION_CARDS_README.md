# Question Card Generator - Simplified Workflow

## Overview

This tool processes CBSE Mathematics question papers and extracts questions, diagrams, and marks mapping without PDF splitting. The workflow focuses on full PDF processing and provides detailed output after each step.

## Workflow Steps

The system now has **4 main steps** (removed PDF splitting):

1. **Step 1: Diagram Extraction**

   - Extracts diagrams and figures from the PDF
   - Saves images to `logs/diagrams/images/`
   - Creates metadata file with figure information
   - Generates a preview image combining all figures

2. **Step 2: Diagram Mapping**

   - Maps extracted diagrams to their corresponding questions
   - Uses AI to analyze PDF content and figure positions
   - Saves mapping to `logs/diagram_mappings/`

3. **Step 3: Marks Extraction**

   - Extracts marks allocation for each question
   - Identifies question types (MCQ, Case Study, etc.)
   - Saves marks mapping to `logs/marks_mappings/`

4. **Step 4: Full PDF Question Extraction** ⭐ **Main Step**
   - Processes the entire PDF to extract all questions
   - Maintains question numbering and formatting
   - Saves extracted questions to `logs/full_pdf_questions/`

## Quick Start

### Option 1: Streamlit Web Interface (Recommended)

```bash
# Install dependencies
pip install -r requirements.txt

# Run the web interface
streamlit run app.py
```

Features:

- Upload PDF files through web interface
- Choose between "End-to-End Processing" or "Individual Steps"
- View detailed results after each step
- Download generated files
- Progress tracking with visual indicators

### Option 2: Command Line Testing

```bash
# Edit the test script to provide your PDF path
# Update line 84 in test_question_cards.py:
# test_pdf_path = "your_pdf_file.pdf"

# Run the test script
python test_question_cards.py
```

## Output Structure

```
logs/
├── diagrams/
│   ├── images/
│   │   ├── figure-1.png
│   │   ├── figure-2.png
│   │   └── ...
│   ├── previews/
│   │   └── preview_20241201_120000.png
│   └── meta_data.json
├── diagram_mappings/
│   └── paper_name.json
├── marks_mappings/
│   └── paper_name.json
└── full_pdf_questions/
    ├── paper_name.md
    └── paper_name_raw_response.txt
```

## Step-by-Step Output Examples

### Step 1: Diagram Extraction Output

```
✅ Step 1: Diagram Extraction
📊 Total figures extracted: 8
📁 Images saved to: logs/diagrams/images
📄 Metadata file: logs/diagrams/meta_data.json
```

### Step 2: Diagram Mapping Output

```
✅ Step 2: Diagram Mapping
📄 Mapping file: logs/diagram_mappings/paper_name.json
🔍 Mapping content:
{
  "figure-1": {
    "question_identifier": "12",
    "choice_location": "null"
  },
  "figure-2": {
    "question_identifier": "15",
    "choice_location": "first"
  }
}
```

### Step 3: Marks Extraction Output

```
✅ Step 3: Marks Extraction
📄 Marks file: logs/marks_mappings/paper_name.json
🔍 Marks content:
{
  "question-1": {
    "question_type": "MCQ",
    "marks": 1
  },
  "question-15": {
    "question_type": "Internal Choice Subjective",
    "marks": ["This question has [3] marks", "This question has [3] marks"]
  }
}
```

### Step 4: Full PDF Question Extraction Output

```
✅ Step 4: Full PDF Question Extraction
📄 Questions file: logs/full_pdf_questions/paper_name.md
📄 Raw response file: logs/full_pdf_questions/paper_name_raw_response.txt
📖 Extracted questions preview:
1. The LCM of smallest two digit composite number and smallest composite number is:
(A) 12
(B) 4
(C) 20
(D) 44
[####]

2. Solve the equation: $x^2 + 5x + 6 = 0$
[####]
...
```

## Error Handling

The system continues processing even if individual steps fail:

- **Step 1 fails**: Continues to Step 2-4, but no diagrams available
- **Step 2 fails**: Continues to Step 3-4, but no diagram mapping
- **Step 3 fails**: Continues to Step 4, but no marks mapping
- **Step 4 fails**: Reports error but still shows results from other steps

## Key Features

- ✅ **No PDF splitting** - processes entire PDF at once
- ✅ **Detailed output display** - shows results after each step
- ✅ **Individual step testing** - debug specific steps
- ✅ **Progress tracking** - real-time status updates
- ✅ **File download** - easy access to generated files
- ✅ **Error resilience** - continues processing on step failures

## Configuration

### Environment Variables

```bash
# Required
GEMINI_API_KEY=your_gemini_api_key_here
```

### Dependencies

```bash
# Install all dependencies
pip install -r requirements.txt

# Key dependencies:
# - streamlit (web interface)
# - google-genai (AI processing)
# - PyPDF2, pdf2image (PDF processing)
# - torch, torchvision (diagram extraction)
# - pillow (image processing)
```

## Troubleshooting

### Common Issues

1. **"No diagrams found"**: Normal for text-only PDFs
2. **"Diagram mapping failed"**: Occurs when no diagrams are available
3. **"Marks extraction failed"**: Check if PDF contains clear marks indicators
4. **"Question extraction failed"**: Verify PDF is readable and contains questions

### Debug Mode

Use individual step testing to isolate issues:

```bash
# Test specific steps
python test_question_cards.py

# Or use Streamlit interface
streamlit run app.py
# Choose "Individual Steps" mode
```

## Output File Formats

- **Questions**: Markdown format with special tags (`[####]`, `[%OR%]`)
- **Mappings**: JSON format with structured data
- **Diagrams**: PNG images with metadata
- **Raw responses**: Plain text for debugging

This simplified workflow eliminates the complexity of PDF splitting while providing comprehensive output visibility for debugging and verification.
