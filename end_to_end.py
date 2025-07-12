import os
import sys
import re
import json
import torch
import torchvision
import tempfile
import streamlit as st
from typing import List, Tuple, Dict, Any
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import fitz
from pdf2image import convert_from_bytes
import hashlib
from dotenv import load_dotenv
from google import genai
from google.genai import types
from huggingface_hub import snapshot_download
from doclayout_yolo import YOLOv10
import cv2
import io
import base64
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Rectangle
from collections import defaultdict

# Load environment variables
load_dotenv()

# Environment variable for Gemini API key
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("Environment variable GEMINI_API_KEY must be set")

# Dependency checks
def check_dependencies():
    """Check if all required dependencies are available"""
    missing_deps = []
    
    try:
        import torch
        import torchvision
    except ImportError:
        missing_deps.append("PyTorch")
    
    try:
        from google import genai
    except ImportError:
        missing_deps.append("Google Genai")
    
    try:
        from doclayout_yolo import YOLOv10
    except ImportError:
        missing_deps.append("DocLayout YOLO")
    
    try:
        import fitz  # PyMuPDF
    except ImportError:
        missing_deps.append("PyMuPDF")
    
    try:
        from pdf2image import convert_from_bytes
    except ImportError:
        missing_deps.append("pdf2image")
    
    if missing_deps:
        error_msg = f"Missing required dependencies: {', '.join(missing_deps)}"
        raise ImportError(error_msg)
    
    return True

# Check dependencies on import
try:
    check_dependencies()
    DEPENDENCIES_OK = True
except ImportError as e:
    print(f"Dependency check failed: {e}")
    DEPENDENCIES_OK = False

# Initialize Gemini client
try:
    client = genai.Client(api_key=GEMINI_API_KEY)
    GEMINI_CLIENT_OK = True
except Exception as e:
    print(f"Failed to initialize Gemini client: {e}")
    GEMINI_CLIENT_OK = False

# Import the full PDF question extraction function
from api.full_pdf_question_extraction import extract_questions_from_pdf

# Import question card generation utilities
try:
    from utils.question_card_generator import generate_question_cards
    QUESTION_CARDS_AVAILABLE = True
except ImportError:
    QUESTION_CARDS_AVAILABLE = False

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def ensure_dir_exists(directory):
    """Create directory if it doesn't exist"""
    if not os.path.exists(directory):
        os.makedirs(directory)

def generate_output_filename(page_num, total_pages):
    """Generate formatted filename for page"""
    padding = len(str(total_pages))
    return f"page_{page_num:0{padding}d}.pdf"

# =============================================================================
# DIAGRAM EXTRACTION FUNCTIONS
# =============================================================================

def _load_model():
    """Load the DocLayout YOLO model"""
    try:
        # Check if CUDA is available
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        if device == 'cuda':
            print("Using CUDA GPU for model inference")
        else:
            print("Using CPU for model inference")
            
        model_dir = snapshot_download(
            'juliozhao/DocLayout-YOLO-DocStructBench',
            local_dir=os.path.abspath(os.path.join(os.path.dirname(__file__), 'models', 'DocLayout-YOLO-DocStructBench'))
        )
        model_path = os.path.join(model_dir, 'doclayout_yolo_docstructbench_imgsz1024.pt')
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found at {model_path}")
            
        model = YOLOv10(model_path)
        return model, device
    except Exception as e:
        print(f"Error loading model: {str(e)}")
        if st is not None:
            st.error(f"Error loading model: {str(e)}")
        return None, None

# Global model initialization
_model, _device = _load_model()

# Mapping of class IDs to names
ID_TO_NAMES = {
    0: 'title',
    1: 'plain text',
    2: 'abandon',
    3: 'figure',
    4: 'figure_caption',
    5: 'table',
    6: 'table_caption',
    7: 'table_footnote',
    8: 'isolate_formula',
    9: 'formula_caption'
}

def visualize_bbox(image, boxes, classes, scores, id_to_names):
    """Visualize bounding boxes on image"""
    try:
        # Convert PIL image to numpy array
        if isinstance(image, Image.Image):
            image = np.array(image)
        
        # Create figure and axis
        fig, ax = plt.subplots(1, figsize=(12, 8))
        ax.imshow(image)
        
        # Draw bounding boxes
        for box, cls, score in zip(boxes, classes, scores):
            x1, y1, x2, y2 = box
            width = x2 - x1
            height = y2 - y1
            
            # Create rectangle
            rect = Rectangle((x1, y1), width, height, 
                           linewidth=2, edgecolor='red', facecolor='none')
            ax.add_patch(rect)
            
            # Add label
            label = f"{id_to_names.get(int(cls), 'unknown')} {score:.2f}"
            ax.text(x1, y1-5, label, fontsize=8, color='red', 
                   bbox=dict(boxstyle="round,pad=0.3", facecolor="yellow", alpha=0.7))
        
        ax.axis('off')
        
        # Convert matplotlib figure to PIL Image
        fig.canvas.draw()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', dpi=150)
        buf.seek(0)
        result_image = Image.open(buf)
        plt.close(fig)
        
        return np.array(result_image)
        
    except Exception as e:
        st.error(f"Error in visualization: {str(e)}")
        return image

def extract_diagrams_from_pdf(file_path: str, conf_threshold: float = 0.25, iou_threshold: float = 0.45) -> Tuple[List, List[List]]:
    """Extract diagram images with detected bounding boxes from a PDF file"""
    try:
        results = []
        figure_snippets = []
        
        if _model is None:
            st.error("Model not loaded. Cannot extract diagrams.")
            return [], []
        
        with open(file_path, 'rb') as f:
            pages = convert_from_bytes(f.read(), dpi=300)
            
        for page in pages:
            try:
                det_res = _model.predict(
                    page,
                    imgsz=1024,
                    conf=conf_threshold,
                    device=_device,
                )[0]
                
                boxes = det_res.__dict__['boxes'].xyxy
                classes = det_res.__dict__['boxes'].cls
                scores = det_res.__dict__['boxes'].conf

                # Apply non-maximum suppression
                indices = torchvision.ops.nms(
                    boxes=torch.Tensor(boxes),
                    scores=torch.Tensor(scores),
                    iou_threshold=iou_threshold
                )
                
                b, s, c = boxes[indices], scores[indices], classes[indices]
                
                # Ensure correct shape
                if b.ndim == 1:
                    b = np.expand_dims(b, 0)
                    s = np.expand_dims(s, 0)
                    c = np.expand_dims(c, 0)

                vis = visualize_bbox(page, b, c, s, ID_TO_NAMES)
                results.append(vis)
                
                # Extract figure snippets
                fig_indices = [i for i, cls in enumerate(c) if int(cls) == 3]
                fig_boxes = [b[i] for i in fig_indices]
                n = len(fig_boxes)
                
                if n > 0:
                    # Group overlapping boxes
                    parents = list(range(n))
                    def find(i):
                        if parents[i] != i:
                            parents[i] = find(parents[i])
                        return parents[i]
                    
                    def union(i, j):
                        pi, pj = find(i), find(j)
                        if pi != pj:
                            parents[pj] = pi
                    
                    for i1 in range(n):
                        y1_i, y2_i = fig_boxes[i1][1], fig_boxes[i1][3]
                        for j1 in range(i1 + 1, n):
                            y1_j, y2_j = fig_boxes[j1][1], fig_boxes[j1][3]
                            if y1_i < y2_j and y1_j < y2_i:
                                union(i1, j1)
                    
                    groups = defaultdict(list)
                    for idx in range(n):
                        root = find(idx)
                        groups[root].append(idx)
                    
                    merged = []
                    for grp in groups.values():
                        xs1 = [fig_boxes[i][0] for i in grp]
                        ys1 = [fig_boxes[i][1] for i in grp]
                        xs2 = [fig_boxes[i][2] for i in grp]
                        ys2 = [fig_boxes[i][3] for i in grp]
                        x1_ = min(xs1); y1_ = min(ys1)
                        x2_ = max(xs2); y2_ = max(ys2)
                        crop = page.crop((int(x1_), int(y1_), int(x2_), int(y2_)))
                        merged.append((y1_, crop))
                    
                    merged.sort(key=lambda x: x[0])
                    page_figs = [crop for _, crop in merged]
                else:
                    page_figs = []
                
                figure_snippets.append(page_figs)
                
            except Exception as e:
                st.error(f"Error processing page: {str(e)}")
                figure_snippets.append([])
                
        return results, figure_snippets
        
    except Exception as e:
        st.error(f"Error in extract_diagrams_from_pdf: {str(e)}")
        return [], []

def log_diagram_snippets(figure_snippets):
    """
    Save extracted figure snippets to disk and write metadata JSON.
    Uses the existing high-quality implementation from logs/logger.py
    """
    try:
        from datetime import datetime
        
        # Create directories
        DIAGRAM_LOG_DIR = os.path.join('logs', 'diagrams')
        images_dir = os.path.join(DIAGRAM_LOG_DIR, 'images')
        ensure_dir_exists(images_dir)
        
        # Build metadata
        meta = {"figures": []}
        fig_counter = 1
        for page_idx, figs in enumerate(figure_snippets):
            for fig_img in figs:
                file_name = f"figure-{fig_counter}.png"
                save_path = os.path.join(images_dir, file_name)
                fig_img.save(save_path)
                meta["figures"].append({
                    "figure_id": fig_counter,
                    "page": page_idx + 1,
                    "path": save_path
                })
                fig_counter += 1
        
        # Write metadata JSON
        ensure_dir_exists(DIAGRAM_LOG_DIR)
        meta_path = os.path.join(DIAGRAM_LOG_DIR, 'meta_data.json')
        with open(meta_path, 'w') as mf:
            json.dump(meta, mf, indent=2)
        
        # Compose and save UI preview image using existing high-quality implementation
        try:
            # Generate higher resolution preview (wide thumbnails) for crisp output
            preview_img = compose_diagram_preview(figure_snippets, thumb_width=800)
            preview_dir = os.path.join(DIAGRAM_LOG_DIR, 'previews')
            ensure_dir_exists(preview_dir)
            preview_filename = f"preview_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            preview_path = os.path.join(preview_dir, preview_filename)
            preview_img.save(preview_path, dpi=(300, 300))
            
            # Update metadata with preview path
            meta['preview'] = preview_path
            with open(meta_path, 'w') as mf:
                json.dump(meta, mf, indent=2)
        except Exception as e:
            meta['preview_error'] = str(e)
            with open(meta_path, 'w') as mf:
                json.dump(meta, mf, indent=2)
        
        return images_dir, meta_path
        
    except Exception as e:
        st.error(f"Error logging diagram snippets: {str(e)}")
        return None, None

def compose_diagram_preview(
    figure_snippets: List[List[Image.Image]],
    dpi: int = 300,
    thumb_width: int = 200,
    font_path: str = None
) -> Image.Image:
    """
    Build a single PIL image that mirrors the Streamlit UI layout:
      - "Here are figures present:" heading
      - For each page:
          - Subheader "Page X"
          - For each figure:
              - Label "Figure Y"
              - Thumbnail image resized to thumb_width
    Uses the existing high-quality implementation from utils/image_composer.py
    """
    # Load fonts: H1 (48px bold), H2 (36px bold), H3 (24px regular)
    if font_path:
        try:
            heading_font = ImageFont.truetype(font_path, size=48)
            subheader_font = ImageFont.truetype(font_path, size=36)
            label_font = ImageFont.truetype(font_path, size=24)
        except Exception:
            heading_font = ImageFont.load_default()
            subheader_font = ImageFont.load_default()
            label_font = ImageFont.load_default()
    else:
        # Try common system fonts for bold and regular
        font_bold_candidates = [
            "DejaVuSans-Bold.ttf",
            "/Library/Fonts/Arial Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        ]
        font_reg_candidates = [
            "DejaVuSans.ttf",
            "/Library/Fonts/Arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        ]
        heading_font = subheader_font = None
        for fb in font_bold_candidates:
            try:
                heading_font = ImageFont.truetype(fb, size=48)
                subheader_font = ImageFont.truetype(fb, size=36)
                break
            except Exception:
                continue
        label_font = None
        for fr in font_reg_candidates:
            try:
                label_font = ImageFont.truetype(fr, size=24)
                break
            except Exception:
                continue
        # Fallback to default bitmap font if any loading failed
        if heading_font is None or subheader_font is None or label_font is None:
            heading_font = ImageFont.load_default()
            subheader_font = ImageFont.load_default()
            label_font = ImageFont.load_default()

    # Layout parameters
    left_margin = 20
    # Increase top margin and vertical padding for better spacing
    top_margin = 30
    v_padding = 20
    heading_text = "Here are figures present:"

    # First pass: calculate canvas size
    # Dummy draw to measure text using textbbox
    dummy_img = Image.new("RGB", (10, 10))
    draw_dummy = ImageDraw.Draw(dummy_img)
    bbox = draw_dummy.textbbox((0, 0), heading_text, font=heading_font)
    h_heading = bbox[3] - bbox[1]
    total_height = top_margin
    total_height += h_heading + v_padding

    fig_counter = 1
    for page_idx, figs in enumerate(figure_snippets):
        if figs:
            page_text = f"Page {page_idx + 1}"
            bbox = draw_dummy.textbbox((0, 0), page_text, font=subheader_font)
            h_page = bbox[3] - bbox[1]
            total_height += h_page + v_padding
            for fig_img in figs:
                fig_label = f"Figure {fig_counter}"
                bbox = draw_dummy.textbbox((0, 0), fig_label, font=label_font)
                h_label = bbox[3] - bbox[1]
                total_height += h_label + v_padding
                # thumbnail height
                orig_w, orig_h = fig_img.size
                scale = thumb_width / orig_w
                thumb_h = int(orig_h * scale)
                total_height += thumb_h + v_padding
                fig_counter += 1
    total_height += top_margin

    # Canvas width and creation
    canvas_width = thumb_width + left_margin * 2
    canvas = Image.new("RGB", (canvas_width, total_height), "white")
    draw = ImageDraw.Draw(canvas)

    # Second pass: render content
    y = top_margin
    # Heading
    draw.text((left_margin, y), heading_text, fill="black", font=heading_font)
    y += h_heading + v_padding

    fig_counter = 1
    for page_idx, figs in enumerate(figure_snippets):
        if figs:
            page_text = f"Page {page_idx + 1}"
            draw.text((left_margin, y), page_text, fill="black", font=subheader_font)
            bbox = draw.textbbox((0, 0), page_text, font=subheader_font)
            h_page = bbox[3] - bbox[1]
            y += h_page + v_padding
            for fig_img in figs:
                fig_label = f"Figure {fig_counter}"
                draw.text((left_margin, y), fig_label, fill="black", font=label_font)
                bbox = draw.textbbox((0, 0), fig_label, font=label_font)
                h_label = bbox[3] - bbox[1]
                y += h_label + v_padding
                # Resize and paste thumbnail
                orig_w, orig_h = fig_img.size
                scale = thumb_width / orig_w
                thumb_h = int(orig_h * scale)
                thumb = fig_img.resize((thumb_width, thumb_h), resample=Image.Resampling.LANCZOS)
                canvas.paste(thumb, (left_margin, y))
                y += thumb_h + v_padding
                fig_counter += 1

    return canvas

# =============================================================================
# PDF PROCESSING FUNCTIONS
# =============================================================================

def process_pdf(uploaded_file, output_folder):
    """Split uploaded PDF into single-page PDFs"""
    try:
        ensure_dir_exists(output_folder)
        
        # Read the uploaded file into memory
        file_bytes = uploaded_file.read()
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        total_pages = doc.page_count
        
        page_paths = []
        
        # Loop through each page and save as a new PDF
        for i in range(total_pages):
            new_doc = fitz.open()
            new_doc.insert_pdf(doc, from_page=i, to_page=i)
            filename = generate_output_filename(i + 1, total_pages)
            filepath = os.path.join(output_folder, filename)
            new_doc.save(filepath)
            new_doc.close()
            page_paths.append(filepath)
        
        doc.close()
        return page_paths
        
    except Exception as e:
        st.error(f"Error processing PDF: {str(e)}")
        return []

# =============================================================================
# GEMINI API FUNCTIONS
# =============================================================================

def generate_diagram_mapping(pdf_path: str, image_path: str) -> Tuple[str, str]:
    """Generate diagram mapping using Gemini"""
    try:
        # System and user prompts (exact from original files)
        system_prompt = """
You are a specialized diagram analysis assistant that maps extracted diagrams to their corresponding questions in CBSE Mathematics exam papers with 100% accuracy.

## Core Identity
You analyze image files containing extracted diagrams and PDF documents to create precise mappings between figure numbers and their corresponding question identifiers, including proper internal choice classification.

## Input Specification
- **Image file**: Contains extracted diagrams with figure numbers and page numbers
- **PDF document**: CBSE Mathematics exam paper from which diagrams were extracted

## Primary Objective
Systematically analyze both files to create accurate mappings between figure numbers and their corresponding question identifiers, focusing ONLY on questions with actual printed visual content.

## Critical Content Rules

### MUST INCLUDE (Visual Content Only):
- Questions with actual printed diagrams, figures, charts, or images
- Visual elements that can be seen and described
- Geometric shapes, graphs, illustrations that are physically present

### MUST EXCLUDE (Textual Descriptions):
- Questions with only textual descriptions like "A triangle ABC has sides 3, 4, 5..."
- Questions stating "In a circle with center O..." without actual visual circle
- Questions mentioning "Consider a function f(x)..." without actual graph
- Questions saying "In the given figure..." when no actual figure is present
- Any question that only describes mathematical objects without showing them

## Internal Choice Classification Rules
- **Case study questions**: Always `choice_location = "null"` (regardless of OR separators in subparts)
- **Regular questions with OR**: Classify as `first/second/both` based on diagram location
- **Regular questions without OR**: `choice_location = "null"`

## Output Format
```json
{
  "figure-1": {
    "question_identifier": "question_number",
    "choice_location": "first/second/null"
  },
  "figure-2": {
    "question_identifier": "question_number",
    "choice_location": "first/second/null"
  }
}
```

## Quality Standards
- **100% Visual Content Focus**: Only map to questions with actual printed diagrams
- **Complete Figure Coverage**: Every figure in the image must be mapped
- **Precise Choice Classification**: Accurate determination of internal choice locations
- **Verbatim Question Identification**: Match questions exactly as they appear in the PDF



"""

        user_prompt = """
Please analyze the provided image file containing extracted diagrams and the PDF document they came from. Follow this systematic approach:

## Step 1: Figure Image Analysis
**Parse the provided image file:**
- Identify and count all figures present in the image
- For each figure, extract:
  - Figure number/identifier (as labeled in the image)
  - Page number (as indicated in the image)
  - Generate a detailed description of each figure's visual content

**Output format for Step 1:**
```
Total figures in image: [number]
Figure-1: Page X - [Detailed visual description including diagram type, elements, labels, etc.]
Figure-2: Page Y - [Detailed visual description including diagram type, elements, labels, etc.]
...continue for all figures
```

## Step 2: PDF Document Question Analysis
**Analyze the PDF document comprehensively:**
- Count the total number of questions in the PDF
- Identify which questions contain **actual visual diagrams/figures/images** (not just textual descriptions)
- **IMPORTANT**: Only count questions with printed diagrams, figures, charts, or visual elements
- **EXCLUDE**: Questions that only contain textual descriptions of diagrams without actual visual content
- Count the total number of questions that have actual diagrams

**Output format for Step 2:**
```
Total questions in PDF: [number]
Questions with actual diagrams: [number]
Question numbers containing actual diagrams: [list of question numbers]
```

## Step 3: Question-wise Diagram Description
**For each question that contains actual visual diagrams:**
- Identify the question number
- Determine if it's a case study type question
- **CRITICAL**: Only analyze questions with actual printed diagrams/figures/images
- **IGNORE**: Questions that only have textual descriptions like "A triangle ABC has sides...", "In a circle with center O...", "Consider a function f(x)..." without actual visual diagrams
- Locate the actual visual diagram(s) within that question
- Generate a detailed description of the visual diagram as it appears in the question
- Note the diagram's position within the question (beginning, middle, end, or in internal choice)

**Output format for Step 3:**
```
Question X: 
- Question type: [case study/regular]
- Has actual visual diagram: [Yes - if printed diagram present]
- Diagram location: [position in question]
- Diagram description: [detailed description of the actual visual content]
- Internal choice status: [first/second/both/null]

Question Y:
- Question type: [case study/regular]
- Has actual visual diagram: [Yes - if printed diagram present]
- Diagram location: [position in question] 
- Diagram description: [detailed description of the actual visual content]
- Internal choice status: [first/second/both/null]

...continue for all questions with actual visual diagrams
```

## Step 4: Cross-Reference and Mapping
**Match figures from image to questions:**
- Compare the figure descriptions from Step 1 with question diagram descriptions from Step 3
- Match based on:
  - Visual content similarity
  - Page number correlation
  - Figure number references
  - Context alignment

**Output format for Step 4:**
```
Mapping Analysis:
Figure-1 (Page X): Matches diagram in Question Y because [detailed reasoning]
Figure-2 (Page Z): Matches diagram in Question W because [detailed reasoning]
...continue for all figures
```

## Step 5: Internal Choice Classification
**For each mapped figure:**
- First, determine if the question is a case study type question
- If it's a case study question: Classification = null (regardless of OR separators in subparts)
- If it's a regular question:
  - Determine if the question has an "OR" separator creating internal choices
  - Identify where the diagram appears relative to the "OR"
  - Classify as: first/second/both/null

**Output format for Step 5:**
```
Internal Choice Analysis:
Question Y: Case study type → Classification: null
Question W: Regular question + Has OR separator → Figure-1 appears in [first/second/both] part
Question Z: Regular question + No OR separator → Classification: null
...continue for all questions
```

## Step 6: Final Output
**Present only the final mapping in JSON format:**

```json
{
  "figure-1": {
    "question_identifier": "question_number",
    "choice_location": "first/second/null"
  },
  "figure-2": {
    "question_identifier": "question_number",
    "choice_location": "first/second/null"
  }
}
```

## Critical Instructions:
- Show your complete reasoning process for each step
- **CRITICAL**: Only consider questions with actual printed diagrams/figures/images, NOT textual descriptions
- **IGNORE**: Questions like "A triangle ABC with sides 3, 4, 5..." or "In the given circle..." that only have text descriptions without visual diagrams
- **FOCUS**: Only on questions that have actual visual content (diagrams, figures, charts, images)
- Ensure every figure from the image is mapped to a question with actual visual content
- Provide detailed visual descriptions for accurate matching
- **IMPORTANT**: For case study type questions, always set choice_location to "null" regardless of any OR separators in subparts
- For regular questions with OR separators, classify as first/second/both based on diagram location
- For regular questions without OR separators, set choice_location to "null"
- Cross-verify all mappings before finalizing
- The final mappings must include ALL figures present in the provided image
- Maintain 100% accuracy in question identification and choice classification

Please follow this systematic approach and provide the comprehensive analysis with the final JSON output.
"""
        
        # Upload files to Gemini
        pdf_file = client.files.upload(file=pdf_path)
        img_file = client.files.upload(file=image_path)

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
            thinking_config=types.ThinkingConfig(thinking_budget=5000)
        )

        # Generate content
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[pdf_file, img_file, system_prompt, user_prompt],
            config=config,
        )

        # Clean up uploaded files
        client.files.delete(name=pdf_file.name)
        client.files.delete(name=img_file.name)

        # Parse response
        raw_text = response.text.strip() if hasattr(response, 'text') else ''
        if not raw_text:
            raise ValueError("No mapping content generated")
        
        # Extract JSON
        match = re.search(r"\{[\s\S]*\}", raw_text)
        if not match:
            raise ValueError("No JSON object found in mapping response")
        
        json_str = match.group(0)
        mapping_json = json.loads(json_str)

        # Save mapping
        output_dir = os.path.join('logs', 'diagram_mappings')
        ensure_dir_exists(output_dir)
        base_pdf = os.path.splitext(os.path.basename(pdf_path))[0]
        base_img = os.path.splitext(os.path.basename(image_path))[0]
        output_filename = f"{base_pdf}__{base_img}.json"
        output_path = os.path.join(output_dir, output_filename)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(mapping_json, f, indent=2)

        return output_path, raw_text

    except Exception as e:
        # Cleanup on error
        try:
            client.files.delete(name=pdf_file.name)
            client.files.delete(name=img_file.name)
        except:
            pass
        raise RuntimeError(f"Diagram mapping generation failed: {str(e)}")

def generate_marks_mapping(pdf_path: str) -> Tuple[str, str]:
    """Generate marks mapping using Gemini"""
    try:
        # System and user prompts (exact from original files)
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

## Classification Priority Rules
- If a question has subparts → **Case Study** (even if subparts have internal choice)
- If a question has "OR" between just two main questions → **Internal Choice Subjective**
- If a question is multiple choice with options → **MCQ**
- If a question has assertion and reasoning format → **Assertion Reasoning**
- If a question is subjective without above features → **Normal Subjective**

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

**Classification Priority:**
- Subparts present = Case Study (even if subparts have internal choice)
- "OR" between two main questions = Internal Choice Subjective
- Multiple choice options = MCQ
- Assertion-Reasoning format = Assertion Reasoning
- Regular subjective = Normal Subjective

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

        # Generate content
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite-preview-06-17",
            contents=[pdf_file, system_prompt, user_prompt],
            config=config,
        )

        # Clean up uploaded file
        client.files.delete(name=pdf_file.name)

        # Parse response
        raw_text = response.text.strip() if hasattr(response, 'text') else ''
        if not raw_text:
            raise ValueError("No mapping content generated")
        
        # Extract JSON
        match = re.search(r"\{[\s\S]*\}", raw_text)
        if not match:
            raise ValueError("No JSON object found in response")
        
        json_str = match.group(0)
        mapping_json = json.loads(json_str)

        # Save mapping
        output_dir = os.path.join('logs', 'marks_mappings')
        ensure_dir_exists(output_dir)
        base_pdf = os.path.splitext(os.path.basename(pdf_path))[0]
        output_filename = f"{base_pdf}.json"
        output_path = os.path.join(output_dir, output_filename)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(mapping_json, f, indent=2)

        return output_path, raw_text

    except Exception as e:
        # Cleanup on error
        try:
            client.files.delete(name=pdf_file.name)
        except:
            pass
        raise RuntimeError(f"Marks mapping generation failed: {str(e)}")

def generate_markdown_from_pdf(pdf_path: str) -> str:
    """Generate markdown from PDF using Gemini"""
    try:
        # System and user prompts (exact from original files)
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

        # Generate content
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite-preview-06-17",
            contents=[pdf_file, system_prompt, user_prompt],
            config=config,
        )

        # Clean up uploaded file
        client.files.delete(name=pdf_file.name)

        # Parse response
        markdown_text = response.text.strip() if hasattr(response, 'text') else ''
        if not markdown_text:
            raise ValueError("No markdown content generated")

        # Save markdown
        output_dir = os.path.join('logs', 'gemini_questions')
        ensure_dir_exists(output_dir)
        output_filename = os.path.basename(pdf_path).replace('.pdf', '.md')
        output_path = os.path.join(output_dir, output_filename)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown_text)

        return output_path

    except Exception as e:
        # Cleanup on error
        try:
            client.files.delete(name=pdf_file.name)
        except:
            pass
        raise RuntimeError(f"Markdown generation failed: {str(e)}")

# =============================================================================
# MAIN END-TO-END PROCESSING FUNCTION
# =============================================================================

def run_end_to_end_processing(uploaded_file, step_callback=None):
    """
    Run the complete end-to-end processing pipeline
    
    Args:
        uploaded_file: Streamlit uploaded file object
        step_callback: Optional callback function to report progress
    
    Returns:
        Dict containing all results and file paths
    """
    results = {
        'success': False,
        'errors': [],
        'step_results': {},
        'final_outputs': {}
    }
    
    temp_files = []  # Keep track of temporary files for cleanup
    
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            temp_pdf_path = tmp_file.name
            temp_files.append(temp_pdf_path)
        
        if step_callback:
            step_callback("Step 0: File uploaded successfully", "success")
        
        # =====================================================================
        # STEP 1: DIAGRAM EXTRACTION
        # =====================================================================
        try:
            if step_callback:
                step_callback("Step 1: Starting diagram extraction...", "info")
            
            parsed_images, figure_snippets = extract_diagrams_from_pdf(temp_pdf_path)
            images_dir, meta_path = log_diagram_snippets(figure_snippets)
            
            results['step_results']['step1'] = {
                'success': True,
                'parsed_images': parsed_images,
                'figure_snippets': figure_snippets,
                'images_dir': images_dir,
                'meta_path': meta_path,
                'total_figures': sum(len(figs) for figs in figure_snippets)
            }
            
            if step_callback:
                step_callback(f"Step 1: Extracted {results['step_results']['step1']['total_figures']} diagrams", "success")
                
        except Exception as e:
            error_msg = f"Step 1 failed: {str(e)}"
            results['errors'].append(error_msg)
            results['step_results']['step1'] = {
                'success': False,
                'error': str(e)
            }
            if step_callback:
                step_callback(error_msg, "error")
            # Continue to next step even if this fails
        
        # =====================================================================
        # STEP 2: DIAGRAM MAPPING
        # =====================================================================
        try:
            if step_callback:
                step_callback("Step 2: Starting diagram mapping...", "info")
            
            # Use the composed preview image if available
            step1_results = results['step_results'].get('step1', {})
            if step1_results.get('meta_path') and os.path.exists(step1_results['meta_path']):
                with open(step1_results['meta_path'], 'r') as f:
                    meta = json.load(f)
                preview_path = meta.get('preview')
                
                if preview_path and os.path.exists(preview_path):
                    mapping_path, raw_text = generate_diagram_mapping(temp_pdf_path, preview_path)
                    
                    results['step_results']['step2'] = {
                        'success': True,
                        'mapping_path': mapping_path,
                        'raw_text': raw_text,
                        'preview_used': preview_path
                    }
                    
                    if step_callback:
                        step_callback("Step 2: Diagram mapping completed", "success")
                else:
                    results['step_results']['step2'] = {
                        'success': False,
                        'error': "No diagram preview available"
                    }
                    if step_callback:
                        step_callback("Step 2: No diagram preview available, skipping mapping", "warning")
            else:
                results['step_results']['step2'] = {
                    'success': False,
                    'error': "No diagrams found"
                }
                if step_callback:
                    step_callback("Step 2: No diagrams found, skipping mapping", "warning")
                    
        except Exception as e:
            error_msg = f"Step 2 failed: {str(e)}"
            results['errors'].append(error_msg)
            results['step_results']['step2'] = {
                'success': False,
                'error': str(e)
            }
            if step_callback:
                step_callback(error_msg, "error")
            # Continue to next step even if this fails
        
        # =====================================================================
        # STEP 3: MARKS EXTRACTION
        # =====================================================================
        try:
            if step_callback:
                step_callback("Step 3: Starting marks extraction...", "info")
            
            marks_path, raw_text = generate_marks_mapping(temp_pdf_path)
            
            results['step_results']['step3'] = {
                'success': True,
                'marks_path': marks_path,
                'raw_text': raw_text
            }
            
            if step_callback:
                step_callback("Step 3: Marks extraction completed", "success")
                
        except Exception as e:
            error_msg = f"Step 3 failed: {str(e)}"
            results['errors'].append(error_msg)
            results['step_results']['step3'] = {
                'success': False,
                'error': str(e)
            }
            if step_callback:
                step_callback(error_msg, "error")
            # Continue to next step even if this fails
        
        # =====================================================================
        # STEP 4: FULL PDF QUESTION EXTRACTION (MAIN STEP)
        # =====================================================================
        try:
            if step_callback:
                step_callback("Step 4: Starting full PDF question extraction...", "info")
            
            questions_path, raw_response_path = extract_questions_from_pdf(temp_pdf_path)
            
            results['step_results']['step4'] = {
                'success': True,
                'questions_path': questions_path,
                'raw_response_path': raw_response_path
            }
            
            if step_callback:
                step_callback("Step 4: Full PDF question extraction completed", "success")
                
        except Exception as e:
            error_msg = f"Step 4 failed: {str(e)}"
            results['errors'].append(error_msg)
            results['step_results']['step4'] = {
                'success': False,
                'error': str(e)
            }
            if step_callback:
                step_callback(error_msg, "error")
            # Continue to finalization even if this fails
        
        # =====================================================================
        # STEP 5: QUESTION CARD GENERATION
        # =====================================================================
        if QUESTION_CARDS_AVAILABLE:
            try:
                if step_callback:
                    step_callback("Step 5: Starting question card generation...", "info")
                
                # Get the PDF filename without extension
                pdf_filename = os.path.splitext(os.path.basename(uploaded_file.name))[0]
                
                # Generate question cards
                generate_question_cards(pdf_filename)
                
                results['step_results']['step5'] = {
                    'success': True,
                    'pdf_filename': pdf_filename,
                    'cards_generated': True
                }
                
                if step_callback:
                    step_callback("Step 5: Question cards generated successfully!", "success")
                    
            except Exception as e:
                error_msg = f"Step 5 failed: {str(e)}"
                results['errors'].append(error_msg)
                results['step_results']['step5'] = {
                    'success': False,
                    'error': str(e)
                }
                if step_callback:
                    step_callback(error_msg, "error")
                # Continue to finalization even if this fails
        else:
            results['step_results']['step5'] = {
                'success': False,
                'error': "Question card generation not available (missing dependencies)"
            }
            if step_callback:
                step_callback("Step 5: Question card generation not available", "warning")
        
        # =====================================================================
        # FINALIZATION
        # =====================================================================
        results['success'] = True
        results['final_outputs'] = {
            'total_diagrams': results['step_results'].get('step1', {}).get('total_figures', 0),
            'diagram_mapping': results['step_results'].get('step2', {}).get('mapping_path'),
            'marks_mapping': results['step_results'].get('step3', {}).get('marks_path'),
            'full_pdf_questions': results['step_results'].get('step4', {}).get('questions_path'),
            'full_pdf_raw_response': results['step_results'].get('step4', {}).get('raw_response_path'),
            'question_cards': results['step_results'].get('step5', {}).get('cards_generated', False)
        }
        
        if step_callback:
            step_callback("🎉 End-to-end processing completed successfully!", "success")
        
    except Exception as e:
        error_msg = f"Fatal error in end-to-end processing: {str(e)}"
        results['errors'].append(error_msg)
        if step_callback:
            step_callback(error_msg, "error")
    
    finally:
        # Cleanup temporary files
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except:
                pass
    
    return results

# =============================================================================
# INDIVIDUAL STEP FUNCTIONS FOR DEBUGGING
# =============================================================================

def run_step_1(uploaded_file):
    """Run only step 1 - diagram extraction"""
    try:
        # Check dependencies first
        if not DEPENDENCIES_OK:
            return {
                'success': False,
                'error': "Missing required dependencies. Please install missing packages."
            }
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            temp_pdf_path = tmp_file.name
        
        parsed_images, figure_snippets = extract_diagrams_from_pdf(temp_pdf_path)
        images_dir, meta_path = log_diagram_snippets(figure_snippets)
        
        # Cleanup
        os.unlink(temp_pdf_path)
        
        return {
            'success': True,
            'parsed_images': parsed_images,
            'figure_snippets': figure_snippets,
            'images_dir': images_dir,
            'meta_path': meta_path,
            'total_figures': sum(len(figs) for figs in figure_snippets)
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def run_step_2(uploaded_file, preview_image_path=None):
    """Run only step 2 - diagram mapping"""
    try:
        # Check dependencies first
        if not DEPENDENCIES_OK:
            return {
                'success': False,
                'error': "Missing required dependencies. Please install missing packages."
            }
        
        if not GEMINI_CLIENT_OK:
            return {
                'success': False,
                'error': "Gemini client not initialized. Check your API key."
            }
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            temp_pdf_path = tmp_file.name
        
        if not preview_image_path:
            # First run step 1 to get diagrams
            step1_result = run_step_1(uploaded_file)
            if not step1_result['success']:
                return step1_result
            
            # Get preview path
            with open(step1_result['meta_path'], 'r') as f:
                meta = json.load(f)
            preview_image_path = meta.get('preview')
        
        if not preview_image_path or not os.path.exists(preview_image_path):
            return {
                'success': False,
                'error': 'No preview image available for mapping'
            }
        
        mapping_path, raw_text = generate_diagram_mapping(temp_pdf_path, preview_image_path)
        
        # Cleanup
        os.unlink(temp_pdf_path)
        
        return {
            'success': True,
            'mapping_path': mapping_path,
            'raw_text': raw_text,
            'preview_used': preview_image_path
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def run_step_3(uploaded_file):
    """Run only step 3 - marks extraction"""
    try:
        # Check dependencies first
        if not DEPENDENCIES_OK:
            return {
                'success': False,
                'error': "Missing required dependencies. Please install missing packages."
            }
        
        if not GEMINI_CLIENT_OK:
            return {
                'success': False,
                'error': "Gemini client not initialized. Check your API key."
            }
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            temp_pdf_path = tmp_file.name
        
        marks_path, raw_text = generate_marks_mapping(temp_pdf_path)
        
        # Cleanup
        os.unlink(temp_pdf_path)
        
        return {
            'success': True,
            'marks_path': marks_path,
            'raw_text': raw_text
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def run_step_4(uploaded_file):
    """Run only step 4 - full PDF question extraction"""
    try:
        # Check dependencies first
        if not DEPENDENCIES_OK:
            return {
                'success': False,
                'error': "Missing required dependencies. Please install missing packages."
            }
        
        if not GEMINI_CLIENT_OK:
            return {
                'success': False,
                'error': "Gemini client not initialized. Check your API key."
            }
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            temp_pdf_path = tmp_file.name
        
        questions_path, raw_response_path = extract_questions_from_pdf(temp_pdf_path)
        
        # Cleanup
        os.unlink(temp_pdf_path)
        
        return {
            'success': True,
            'questions_path': questions_path,
            'raw_response_path': raw_response_path
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def run_step_5(uploaded_file):
    """Run only step 5 - question card generation"""
    try:
        if not QUESTION_CARDS_AVAILABLE:
            return {
                'success': False,
                'error': "Question card generation not available (missing dependencies)"
            }
        
        # Get the PDF filename without extension
        pdf_filename = os.path.splitext(uploaded_file.name)[0]
        
        # Generate question cards
        generate_question_cards(pdf_filename)
        
        return {
            'success': True,
            'pdf_filename': pdf_filename,
            'cards_generated': True
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        } 