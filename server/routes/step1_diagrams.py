from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
import os
import sys
import json
from typing import Optional

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import the actual processing function
from end_to_end import run_step_1, DEPENDENCIES_OK

# Import models
from models.responses import DiagramExtractionResponse, ErrorResponse

router = APIRouter()

@router.post("/extract-diagrams", response_model=DiagramExtractionResponse)
async def extract_diagrams(
    pdf_file: UploadFile = File(..., description="PDF file to extract diagrams from"),
    conf_threshold: float = Form(default=0.25, ge=0.0, le=1.0, description="Confidence threshold for detection"),
    iou_threshold: float = Form(default=0.45, ge=0.0, le=1.0, description="IoU threshold for NMS")
):
    """
    Extract diagrams from a PDF file using DocLayout YOLO model.
    
    This endpoint:
    1. Processes the uploaded PDF file
    2. Uses DocLayout YOLO to detect and extract diagrams
    3. Saves extracted diagrams to the logs/diagrams directory
    4. Generates a preview image with all diagrams
    5. Returns metadata about extracted diagrams
    """
    
    # Check dependencies
    if not DEPENDENCIES_OK:
        raise HTTPException(
            status_code=503,
            detail="Missing required dependencies. Please install PyTorch, DocLayout YOLO, and other required packages."
        )
    
    # Validate file type
    if not pdf_file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported"
        )
    
    try:
        # Create a file-like object for the processing function
        class MockUploadFile:
            def __init__(self, file_content, filename):
                self.file_content = file_content
                self.filename = filename
                self.name = filename
            
            def getvalue(self):
                return self.file_content
        
        # Read file content
        file_content = await pdf_file.read()
        mock_file = MockUploadFile(file_content, pdf_file.filename)
        
        # Process the file
        result = run_step_1(mock_file)
        
        if not result['success']:
            raise HTTPException(
                status_code=500,
                detail=f"Diagram extraction failed: {result['error']}"
            )
        
        # Get preview path from metadata
        preview_path = None
        if result.get('meta_path') and os.path.exists(result['meta_path']):
            try:
                with open(result['meta_path'], 'r') as f:
                    meta = json.load(f)
                preview_path = meta.get('preview')
            except Exception:
                pass
        
        # Count pages processed (assume from figure_snippets)
        pages_processed = len(result.get('figure_snippets', []))
        
        return DiagramExtractionResponse(
            success=True,
            message=f"Successfully extracted {result['total_figures']} diagrams from {pages_processed} pages",
            total_figures=result['total_figures'],
            images_dir=result.get('images_dir'),
            meta_path=result.get('meta_path'),
            preview_path=preview_path,
            pages_processed=pages_processed
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error during diagram extraction: {str(e)}"
        )

@router.get("/extract-diagrams/status")
async def get_extraction_status():
    """
    Get the current status of the diagram extraction system.
    """
    return {
        "dependencies_ok": DEPENDENCIES_OK,
        "model_loaded": DEPENDENCIES_OK,  # Model is loaded when dependencies are OK
        "supported_formats": ["pdf"],
        "default_thresholds": {
            "confidence": 0.25,
            "iou": 0.45
        }
    } 