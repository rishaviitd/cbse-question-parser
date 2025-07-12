from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
import os
import sys
from typing import Optional

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import the actual processing function
from end_to_end import run_step_5, QUESTION_CARDS_AVAILABLE

# Import models
from models.responses import QuestionCardResponse, ErrorResponse

router = APIRouter()

@router.post("/generate-cards", response_model=QuestionCardResponse)
async def generate_cards(
    pdf_file: UploadFile = File(..., description="PDF file to generate cards from"),
    require_all_steps: bool = Form(default=False, description="Whether to require all previous steps to be completed")
):
    """
    Generate question cards from a CBSE Mathematics question paper.
    
    This endpoint:
    1. Uses the uploaded PDF filename to identify processed data
    2. Combines extracted questions, diagrams, and marks allocation
    3. Generates individual question cards with complete information
    4. Returns confirmation of card generation
    
    Note: This step requires that previous steps (questions, diagrams, marks) 
    have been completed for the same PDF file.
    """
    
    # Check if question cards are available
    if not QUESTION_CARDS_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Question card generation not available. Missing required dependencies."
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
        
        # Check if previous steps are completed (if required)
        if require_all_steps:
            base_filename = pdf_file.filename.replace('.pdf', '')
            
            # Check for questions file
            questions_path = os.path.join('logs', 'full_pdf_questions', f"{base_filename}.md")
            if not os.path.exists(questions_path):
                raise HTTPException(
                    status_code=400,
                    detail=f"Questions file not found for {base_filename}. Please run question extraction first."
                )
            
            # Check for marks file
            marks_path = os.path.join('logs', 'marks_mappings', f"{base_filename}.json")
            if not os.path.exists(marks_path):
                raise HTTPException(
                    status_code=400,
                    detail=f"Marks file not found for {base_filename}. Please run marks extraction first."
                )
        
        # Process the file
        result = run_step_5(mock_file)
        
        if not result['success']:
            raise HTTPException(
                status_code=500,
                detail=f"Question card generation failed: {result['error']}"
            )
        
        return QuestionCardResponse(
            success=True,
            message="Question cards generated successfully",
            cards_generated=result['cards_generated'],
            pdf_filename=result['pdf_filename'],
            cards_path=result.get('cards_path')
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error during question card generation: {str(e)}"
        )

@router.get("/generate-cards/status")
async def get_cards_status():
    """
    Get the current status of the question card generation system.
    """
    return {
        "cards_available": QUESTION_CARDS_AVAILABLE,
        "requires_previous_steps": True,
        "dependencies": [
            "Question extraction",
            "Marks extraction", 
            "Diagram extraction (optional)"
        ],
        "output_format": "Individual question cards",
        "features": [
            "Complete question cards",
            "Integrated diagram mapping",
            "Marks allocation",
            "Question type classification"
        ]
    }

@router.get("/generate-cards/check/{filename}")
async def check_prerequisites(filename: str):
    """
    Check if all prerequisites are met for question card generation.
    """
    try:
        # Remove .pdf extension if present
        base_filename = filename.replace('.pdf', '')
        
        # Check for required files
        requirements = {
            "questions_extracted": False,
            "marks_extracted": False,
            "diagrams_extracted": False,
            "diagram_mapping": False
        }
        
        # Check questions file
        questions_path = os.path.join('logs', 'full_pdf_questions', f"{base_filename}.md")
        requirements["questions_extracted"] = os.path.exists(questions_path)
        
        # Check marks file
        marks_path = os.path.join('logs', 'marks_mappings', f"{base_filename}.json")
        requirements["marks_extracted"] = os.path.exists(marks_path)
        
        # Check diagrams
        diagrams_meta = os.path.join('logs', 'diagrams', 'meta_data.json')
        requirements["diagrams_extracted"] = os.path.exists(diagrams_meta)
        
        # Check diagram mapping
        mapping_files = []
        mapping_dir = os.path.join('logs', 'diagram_mappings')
        if os.path.exists(mapping_dir):
            for file in os.listdir(mapping_dir):
                if file.startswith(base_filename) and file.endswith('.json'):
                    mapping_files.append(file)
        requirements["diagram_mapping"] = len(mapping_files) > 0
        
        # Determine if ready
        ready_for_cards = requirements["questions_extracted"] and requirements["marks_extracted"]
        
        return {
            "filename": filename,
            "requirements": requirements,
            "ready_for_cards": ready_for_cards,
            "missing_required": [
                req for req, status in requirements.items() 
                if not status and req in ["questions_extracted", "marks_extracted"]
            ],
            "missing_optional": [
                req for req, status in requirements.items() 
                if not status and req in ["diagrams_extracted", "diagram_mapping"]
            ]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error checking prerequisites: {str(e)}"
        )

@router.post("/generate-cards/force/{filename}")
async def force_generate_cards(filename: str):
    """
    Force question card generation for a specific filename without uploading file again.
    """
    try:
        if not QUESTION_CARDS_AVAILABLE:
            raise HTTPException(
                status_code=503,
                detail="Question card generation not available. Missing required dependencies."
            )
        
        # Remove .pdf extension if present
        base_filename = filename.replace('.pdf', '')
        
        # Import and use the question card generator directly
        from utils.question_card_generator import generate_question_cards
        
        # Generate cards
        generate_question_cards(base_filename)
        
        return QuestionCardResponse(
            success=True,
            message=f"Question cards generated successfully for {base_filename}",
            cards_generated=True,
            pdf_filename=base_filename,
            cards_path=None  # Path would be determined by the generator
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error forcing card generation: {str(e)}"
        ) 