from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse
import os
import sys
import re
from typing import Optional

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import the actual processing function
from end_to_end import run_step_4, DEPENDENCIES_OK, GEMINI_CLIENT_OK

# Import models
from models.responses import QuestionExtractionResponse, ErrorResponse

router = APIRouter()

@router.post("/extract-questions", response_model=QuestionExtractionResponse)
async def extract_questions(
    pdf_file: UploadFile = File(..., description="PDF file to extract questions from")
):
    """
    Extract questions from a CBSE Mathematics question paper in Markdown format.
    
    This endpoint:
    1. Analyzes the uploaded PDF file
    2. Uses Gemini AI to extract only the questions (excludes instructions)
    3. Formats questions in clean Markdown with proper structure
    4. Returns both clean questions and raw AI response
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
        result = run_step_4(mock_file)
        
        if not result['success']:
            raise HTTPException(
                status_code=500,
                detail=f"Question extraction failed: {result['error']}"
            )
        
        # Count questions from the generated markdown file
        total_questions = 0
        if result.get('questions_path') and os.path.exists(result['questions_path']):
            try:
                with open(result['questions_path'], 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Count questions by looking for [####] markers
                question_markers = content.count('[####]')
                total_questions = question_markers
                
            except Exception as e:
                # If we can't parse the file, still return success but with limited info
                pass
        
        return QuestionExtractionResponse(
            success=True,
            message=f"Successfully extracted {total_questions} questions",
            questions_path=result['questions_path'],
            raw_response_path=result['raw_response_path'],
            total_questions=total_questions
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error during question extraction: {str(e)}"
        )

@router.get("/extract-questions/status")
async def get_questions_status():
    """
    Get the current status of the question extraction system.
    """
    return {
        "dependencies_ok": DEPENDENCIES_OK,
        "gemini_client_ok": GEMINI_CLIENT_OK,
        "supported_formats": ["pdf"],
        "ai_model": "gemini-2.5-flash-lite-preview-06-17",
        "output_format": "markdown",
        "features": [
            "Verbatim question extraction",
            "Mathematical expressions in LaTeX",
            "Proper question separation",
            "Internal choice tagging",
            "Excludes instructions and diagrams"
        ]
    }

@router.get("/extract-questions/result/{filename}")
async def get_questions_result(filename: str):
    """
    Get the question extraction result for a specific filename.
    """
    try:
        # Remove .pdf extension if present
        base_filename = filename.replace('.pdf', '')
        questions_path = os.path.join('logs', 'full_pdf_questions', f"{base_filename}.md")
        
        if not os.path.exists(questions_path):
            raise HTTPException(
                status_code=404,
                detail=f"Questions file not found for {filename}"
            )
        
        with open(questions_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Count questions and analyze content
        question_markers = content.count('[####]')
        or_markers = content.count('[%OR%]')
        
        # Extract first few questions as preview
        lines = content.split('\n')
        preview_lines = []
        for i, line in enumerate(lines):
            preview_lines.append(line)
            if '[####]' in line or i >= 20:  # First question or 20 lines max
                break
        
        preview = '\n'.join(preview_lines)
        
        return {
            "success": True,
            "filename": filename,
            "questions_path": questions_path,
            "total_questions": question_markers,
            "internal_choices": or_markers,
            "file_size": os.path.getsize(questions_path),
            "preview": preview,
            "full_content": content
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving questions result: {str(e)}"
        )

@router.get("/extract-questions/download/{filename}")
async def download_questions(filename: str):
    """
    Download the extracted questions markdown file.
    """
    try:
        # Remove .pdf extension if present
        base_filename = filename.replace('.pdf', '')
        questions_path = os.path.join('logs', 'full_pdf_questions', f"{base_filename}.md")
        
        if not os.path.exists(questions_path):
            raise HTTPException(
                status_code=404,
                detail=f"Questions file not found for {filename}"
            )
        
        return FileResponse(
            questions_path,
            media_type='text/markdown',
            filename=f"{base_filename}_questions.md"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error downloading questions file: {str(e)}"
        )

@router.get("/extract-questions/raw/{filename}")
async def get_raw_response(filename: str):
    """
    Get the raw AI response for a specific filename.
    """
    try:
        # Remove .pdf extension if present
        base_filename = filename.replace('.pdf', '')
        raw_path = os.path.join('logs', 'full_pdf_questions', f"{base_filename}_raw_response.txt")
        
        if not os.path.exists(raw_path):
            raise HTTPException(
                status_code=404,
                detail=f"Raw response file not found for {filename}"
            )
        
        with open(raw_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return {
            "success": True,
            "filename": filename,
            "raw_response_path": raw_path,
            "file_size": os.path.getsize(raw_path),
            "content": content
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving raw response: {str(e)}"
        ) 