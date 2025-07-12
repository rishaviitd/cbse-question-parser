from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse
import os
import sys
import time
from typing import Optional

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import the actual processing function
from end_to_end import run_end_to_end_processing, DEPENDENCIES_OK, GEMINI_CLIENT_OK, QUESTION_CARDS_AVAILABLE

# Import models
from models.responses import PipelineResponse, ErrorResponse

router = APIRouter()

@router.post("/process-pipeline", response_model=PipelineResponse)
async def process_pipeline(
    pdf_file: UploadFile = File(..., description="PDF file to process"),
    conf_threshold: float = Form(default=0.25, ge=0.0, le=1.0, description="Confidence threshold for diagram detection"),
    iou_threshold: float = Form(default=0.45, ge=0.0, le=1.0, description="IoU threshold for NMS"),
    include_cards: bool = Form(default=True, description="Whether to generate question cards")
):
    """
    Run the complete end-to-end processing pipeline.
    
    This endpoint processes a CBSE Mathematics question paper through all steps:
    1. Extract diagrams from PDF
    2. Map diagrams to questions
    3. Extract marks allocation
    4. Extract questions in Markdown format
    5. Generate question cards (optional)
    
    Returns detailed results from each step and final outputs.
    """
    
    # Check basic dependencies
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
        
        # Track processing time
        start_time = time.time()
        
        # Create step callback for progress tracking
        step_messages = []
        def step_callback(message: str, status: str):
            step_messages.append({"message": message, "status": status, "timestamp": time.time()})
        
        # Process the file through the complete pipeline
        result = run_end_to_end_processing(mock_file, step_callback)
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Prepare response
        if result['success']:
            return PipelineResponse(
                success=True,
                message=f"Pipeline completed successfully in {processing_time:.2f} seconds",
                step_results=result['step_results'],
                final_outputs=result['final_outputs'],
                errors=result.get('errors', []),
                processing_time=processing_time
            )
        else:
            return PipelineResponse(
                success=False,
                message=f"Pipeline completed with errors after {processing_time:.2f} seconds",
                step_results=result['step_results'],
                final_outputs=result.get('final_outputs', {}),
                errors=result.get('errors', []),
                processing_time=processing_time
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error during pipeline processing: {str(e)}"
        )

@router.get("/process-pipeline/status")
async def get_pipeline_status():
    """
    Get the current status of the pipeline processing system.
    """
    return {
        "dependencies_ok": DEPENDENCIES_OK,
        "gemini_client_ok": GEMINI_CLIENT_OK,
        "question_cards_available": QUESTION_CARDS_AVAILABLE,
        "supported_formats": ["pdf"],
        "pipeline_steps": [
            {
                "step": 1,
                "name": "Diagram Extraction",
                "description": "Extract diagrams using DocLayout YOLO",
                "required": True,
                "dependencies": ["PyTorch", "DocLayout YOLO"]
            },
            {
                "step": 2,
                "name": "Diagram Mapping",
                "description": "Map diagrams to questions using Gemini AI",
                "required": False,
                "dependencies": ["Gemini API"]
            },
            {
                "step": 3,
                "name": "Marks Extraction",
                "description": "Extract marks allocation using Gemini AI",
                "required": True,
                "dependencies": ["Gemini API"]
            },
            {
                "step": 4,
                "name": "Question Extraction",
                "description": "Extract questions in Markdown format using Gemini AI",
                "required": True,
                "dependencies": ["Gemini API"]
            },
            {
                "step": 5,
                "name": "Question Cards",
                "description": "Generate individual question cards",
                "required": False,
                "dependencies": ["Question Card Generator"]
            }
        ],
        "estimated_processing_time": "2-5 minutes depending on PDF size and complexity"
    }

@router.get("/process-pipeline/logs")
async def get_pipeline_logs():
    """
    Get information about recent pipeline processing logs.
    """
    try:
        logs_info = {
            "logs_directory": "logs/",
            "available_outputs": {}
        }
        
        # Check each log directory
        log_dirs = [
            ("diagrams", "logs/diagrams"),
            ("full_pdf_questions", "logs/full_pdf_questions"),
            ("marks_mappings", "logs/marks_mappings"),
            ("diagram_mappings", "logs/diagram_mappings")
        ]
        
        for name, path in log_dirs:
            if os.path.exists(path):
                files = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
                logs_info["available_outputs"][name] = {
                    "path": path,
                    "file_count": len(files),
                    "latest_files": sorted(files, key=lambda x: os.path.getmtime(os.path.join(path, x)), reverse=True)[:5]
                }
            else:
                logs_info["available_outputs"][name] = {
                    "path": path,
                    "file_count": 0,
                    "latest_files": []
                }
        
        return logs_info
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving pipeline logs: {str(e)}"
        )

@router.delete("/process-pipeline/cleanup")
async def cleanup_pipeline_logs():
    """
    Clean up old pipeline processing logs (use with caution).
    """
    try:
        cleaned_dirs = []
        total_files_removed = 0
        
        # Define log directories to clean
        log_dirs = [
            "logs/diagrams",
            "logs/full_pdf_questions", 
            "logs/marks_mappings",
            "logs/diagram_mappings",
            "logs/gemini_questions"
        ]
        
        for log_dir in log_dirs:
            if os.path.exists(log_dir):
                files = [f for f in os.listdir(log_dir) if os.path.isfile(os.path.join(log_dir, f))]
                files_removed = 0
                
                for file in files:
                    file_path = os.path.join(log_dir, file)
                    try:
                        os.remove(file_path)
                        files_removed += 1
                    except Exception:
                        pass
                
                if files_removed > 0:
                    cleaned_dirs.append({
                        "directory": log_dir,
                        "files_removed": files_removed
                    })
                    total_files_removed += files_removed
        
        return {
            "success": True,
            "message": f"Cleaned up {total_files_removed} files from {len(cleaned_dirs)} directories",
            "cleaned_directories": cleaned_dirs,
            "total_files_removed": total_files_removed
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error cleaning up pipeline logs: {str(e)}"
        ) 