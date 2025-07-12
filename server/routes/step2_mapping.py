from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
import os
import sys
import json
from typing import Optional

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import the actual processing function
from end_to_end import run_step_2, DEPENDENCIES_OK, GEMINI_CLIENT_OK

# Import models
from models.responses import DiagramMappingResponse, ErrorResponse

router = APIRouter()

@router.post("/map-diagrams", response_model=DiagramMappingResponse)
async def map_diagrams(
    pdf_file: UploadFile = File(..., description="PDF file to map diagrams from"),
    preview_image_path: Optional[str] = Form(None, description="Path to preview image (optional)")
):
    """
    Map extracted diagrams to their corresponding questions in the PDF.
    
    This endpoint:
    1. Takes the uploaded PDF file
    2. Uses a preview image of extracted diagrams (if provided)
    3. Uses Gemini AI to analyze and map diagrams to questions
    4. Returns mapping information in JSON format
    
    Note: If preview_image_path is not provided, the endpoint will first 
    run diagram extraction to get the preview image.
    """
    
    # Check dependencies
    if not DEPENDENCIES_OK:
        raise HTTPException(
            status_code=503,
            detail="Missing required dependencies. Please install PyTorch, DocLayout YOLO, and other required packages."
        )
    
    if not GEMINI_CLIENT_OK:
        raise HTTPException(
            status_code=503,
            detail="Gemini client not available. Please check your API key configuration."
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
        result = run_step_2(mock_file, preview_image_path)
        
        if not result['success']:
            raise HTTPException(
                status_code=500,
                detail=f"Diagram mapping failed: {result['error']}"
            )
        
        # Count mappings from the generated file
        mappings_count = 0
        if result.get('mapping_path') and os.path.exists(result['mapping_path']):
            try:
                with open(result['mapping_path'], 'r') as f:
                    mapping_data = json.load(f)
                mappings_count = len(mapping_data)
            except Exception:
                pass
        
        return DiagramMappingResponse(
            success=True,
            message=f"Successfully created {mappings_count} diagram mappings",
            mapping_path=result['mapping_path'],
            preview_used=result.get('preview_used'),
            mappings_count=mappings_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error during diagram mapping: {str(e)}"
        )

@router.get("/map-diagrams/status")
async def get_mapping_status():
    """
    Get the current status of the diagram mapping system.
    """
    return {
        "dependencies_ok": DEPENDENCIES_OK,
        "gemini_client_ok": GEMINI_CLIENT_OK,
        "supported_formats": ["pdf"],
        "requires_preview": True,
        "ai_model": "gemini-2.5-flash"
    }

@router.get("/map-diagrams/result/{filename}")
async def get_mapping_result(filename: str):
    """
    Get the mapping result for a specific filename.
    """
    try:
        mapping_path = os.path.join('logs', 'diagram_mappings', f"{filename}.json")
        
        if not os.path.exists(mapping_path):
            raise HTTPException(
                status_code=404,
                detail=f"Mapping file not found for {filename}"
            )
        
        with open(mapping_path, 'r') as f:
            mapping_data = json.load(f)
        
        return {
            "success": True,
            "filename": filename,
            "mapping_path": mapping_path,
            "mappings": mapping_data,
            "total_mappings": len(mapping_data)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving mapping result: {str(e)}"
        ) 