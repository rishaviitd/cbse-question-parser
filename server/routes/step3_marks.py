from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
import os
import sys
import json
from typing import Dict, Any
from collections import Counter

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import the actual processing function
from end_to_end import run_step_3, DEPENDENCIES_OK, GEMINI_CLIENT_OK

# Import models
from models.responses import MarksExtractionResponse, ErrorResponse

router = APIRouter()

@router.post("/extract-marks", response_model=MarksExtractionResponse)
async def extract_marks(
    pdf_file: UploadFile = File(..., description="PDF file to extract marks from")
):
    """
    Extract marks allocation from a CBSE Mathematics question paper.
    
    This endpoint:
    1. Analyzes the uploaded PDF file
    2. Uses Gemini AI to identify questions and their marks allocation
    3. Classifies questions by type (MCQ, Case Study, etc.)
    4. Returns detailed marks mapping in JSON format
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
        result = run_step_3(mock_file)
        
        if not result['success']:
            raise HTTPException(
                status_code=500,
                detail=f"Marks extraction failed: {result['error']}"
            )
        
        # Analyze the marks data
        total_questions = 0
        question_types = {}
        
        if result.get('marks_path') and os.path.exists(result['marks_path']):
            try:
                with open(result['marks_path'], 'r') as f:
                    marks_data = json.load(f)
                
                total_questions = len(marks_data)
                
                # Count question types
                type_counts = Counter()
                for question_data in marks_data.values():
                    question_type = question_data.get('question_type', 'Unknown')
                    type_counts[question_type] += 1
                
                question_types = dict(type_counts)
                
            except Exception as e:
                # If we can't parse the file, still return success but with limited info
                pass
        
        return MarksExtractionResponse(
            success=True,
            message=f"Successfully extracted marks for {total_questions} questions",
            marks_path=result['marks_path'],
            total_questions=total_questions,
            question_types=question_types
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error during marks extraction: {str(e)}"
        )

@router.get("/extract-marks/status")
async def get_marks_status():
    """
    Get the current status of the marks extraction system.
    """
    return {
        "dependencies_ok": DEPENDENCIES_OK,
        "gemini_client_ok": GEMINI_CLIENT_OK,
        "supported_formats": ["pdf"],
        "ai_model": "gemini-2.5-flash-lite-preview-06-17",
        "supported_question_types": [
            "MCQ",
            "Case Study", 
            "Normal Subjective",
            "Internal Choice Subjective",
            "Assertion Reasoning"
        ]
    }

@router.get("/extract-marks/result/{filename}")
async def get_marks_result(filename: str):
    """
    Get the marks extraction result for a specific filename.
    """
    try:
        # Remove .pdf extension if present
        base_filename = filename.replace('.pdf', '')
        marks_path = os.path.join('logs', 'marks_mappings', f"{base_filename}.json")
        
        if not os.path.exists(marks_path):
            raise HTTPException(
                status_code=404,
                detail=f"Marks file not found for {filename}"
            )
        
        with open(marks_path, 'r') as f:
            marks_data = json.load(f)
        
        # Analyze the data
        total_questions = len(marks_data)
        type_counts = Counter()
        marks_distribution = {}
        
        for question_id, question_data in marks_data.items():
            question_type = question_data.get('question_type', 'Unknown')
            type_counts[question_type] += 1
            
            # Try to extract numerical marks for distribution
            marks = question_data.get('marks', 0)
            if isinstance(marks, list):
                # For internal choice questions
                for mark_entry in marks:
                    if isinstance(mark_entry, str) and '[' in mark_entry and ']' in mark_entry:
                        try:
                            mark_val = int(mark_entry.split('[')[1].split(']')[0])
                            marks_distribution[mark_val] = marks_distribution.get(mark_val, 0) + 1
                        except:
                            pass
            elif isinstance(marks, str):
                if '[' in marks and ']' in marks:
                    try:
                        mark_val = int(marks.split('[')[1].split(']')[0])
                        marks_distribution[mark_val] = marks_distribution.get(mark_val, 0) + 1
                    except:
                        pass
        
        return {
            "success": True,
            "filename": filename,
            "marks_path": marks_path,
            "total_questions": total_questions,
            "question_types": dict(type_counts),
            "marks_distribution": marks_distribution,
            "marks_data": marks_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving marks result: {str(e)}"
        ) 