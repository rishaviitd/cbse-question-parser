from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class BaseResponse(BaseModel):
    """Base response model"""
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Response message")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")

class ErrorResponse(BaseResponse):
    """Error response model"""
    error: str = Field(..., description="Error details")
    error_code: Optional[str] = Field(None, description="Error code")
    success: bool = Field(default=False, description="Always false for error responses")

class DiagramExtractionResponse(BaseResponse):
    """Response model for diagram extraction"""
    total_figures: int = Field(..., description="Total number of figures extracted")
    images_dir: Optional[str] = Field(None, description="Directory containing extracted images")
    meta_path: Optional[str] = Field(None, description="Path to metadata file")
    preview_path: Optional[str] = Field(None, description="Path to preview image")
    pages_processed: int = Field(..., description="Number of pages processed")

class DiagramMappingResponse(BaseResponse):
    """Response model for diagram mapping"""
    mapping_path: str = Field(..., description="Path to mapping JSON file")
    preview_used: Optional[str] = Field(None, description="Path to preview image used")
    mappings_count: int = Field(..., description="Number of mappings created")

class MarksExtractionResponse(BaseResponse):
    """Response model for marks extraction"""
    marks_path: str = Field(..., description="Path to marks mapping JSON file")
    total_questions: int = Field(..., description="Total number of questions found")
    question_types: Dict[str, int] = Field(..., description="Count of each question type")

class QuestionExtractionResponse(BaseResponse):
    """Response model for question extraction"""
    questions_path: str = Field(..., description="Path to extracted questions markdown file")
    raw_response_path: str = Field(..., description="Path to raw response file")
    total_questions: int = Field(..., description="Total number of questions extracted")

class QuestionCardResponse(BaseResponse):
    """Response model for question card generation"""
    cards_generated: bool = Field(..., description="Whether cards were generated successfully")
    pdf_filename: str = Field(..., description="PDF filename used for generation")
    cards_path: Optional[str] = Field(None, description="Path to generated cards")

class PipelineResponse(BaseResponse):
    """Response model for end-to-end pipeline"""
    step_results: Dict[str, Any] = Field(..., description="Results from each processing step")
    final_outputs: Dict[str, Any] = Field(..., description="Final output paths and summaries")
    errors: List[str] = Field(default_factory=list, description="Any errors encountered")
    processing_time: Optional[float] = Field(None, description="Total processing time in seconds")

class FileUploadResponse(BaseResponse):
    """Response model for file upload"""
    filename: str = Field(..., description="Name of uploaded file")
    file_size: int = Field(..., description="Size of uploaded file in bytes")
    file_path: str = Field(..., description="Path where file was saved")
    file_type: str = Field(..., description="Type of uploaded file")

class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="API status")
    dependencies_ok: bool = Field(..., description="Whether dependencies are available")
    gemini_client_ok: bool = Field(..., description="Whether Gemini client is available")
    message: str = Field(..., description="Status message")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")

class StatusResponse(BaseModel):
    """System status response"""
    api_version: str = Field(..., description="API version")
    dependencies: Dict[str, Any] = Field(..., description="Dependency status")
    available_endpoints: List[str] = Field(..., description="Available API endpoints")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")

class ProcessingStatusResponse(BaseModel):
    """Processing status response for long-running operations"""
    task_id: str = Field(..., description="Task identifier")
    status: str = Field(..., description="Current status (pending, running, completed, failed)")
    progress: float = Field(..., description="Progress percentage (0-100)")
    current_step: Optional[str] = Field(None, description="Current processing step")
    result: Optional[Dict[str, Any]] = Field(None, description="Result if completed")
    error: Optional[str] = Field(None, description="Error message if failed")
    started_at: datetime = Field(..., description="When processing started")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update time") 