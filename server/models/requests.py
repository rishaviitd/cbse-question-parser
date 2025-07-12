from pydantic import BaseModel, Field
from typing import Optional, List
from fastapi import UploadFile

class DiagramExtractionRequest(BaseModel):
    """Request model for diagram extraction"""
    conf_threshold: float = Field(default=0.25, ge=0.0, le=1.0, description="Confidence threshold for detection")
    iou_threshold: float = Field(default=0.45, ge=0.0, le=1.0, description="IoU threshold for NMS")

class DiagramMappingRequest(BaseModel):
    """Request model for diagram mapping"""
    pdf_filename: str = Field(..., description="Name of the PDF file to map")
    preview_image_path: Optional[str] = Field(None, description="Path to preview image (optional)")

class MarksExtractionRequest(BaseModel):
    """Request model for marks extraction"""
    pdf_filename: str = Field(..., description="Name of the PDF file to extract marks from")

class QuestionExtractionRequest(BaseModel):
    """Request model for question extraction"""
    pdf_filename: str = Field(..., description="Name of the PDF file to extract questions from")

class QuestionCardRequest(BaseModel):
    """Request model for question card generation"""
    pdf_filename: str = Field(..., description="Name of the PDF file to generate cards for")

class PipelineRequest(BaseModel):
    """Request model for end-to-end pipeline"""
    conf_threshold: float = Field(default=0.25, ge=0.0, le=1.0, description="Confidence threshold for diagram detection")
    iou_threshold: float = Field(default=0.45, ge=0.0, le=1.0, description="IoU threshold for NMS")
    include_cards: bool = Field(default=True, description="Whether to generate question cards")

class FileProcessingRequest(BaseModel):
    """Base request model for file processing"""
    filename: str = Field(..., description="Name of the uploaded file")
    
class BaseResponse(BaseModel):
    """Base response model"""
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Response message")
    
class ErrorResponse(BaseResponse):
    """Error response model"""
    error: str = Field(..., description="Error details")
    error_code: Optional[str] = Field(None, description="Error code")
    
class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="API status")
    dependencies_ok: bool = Field(..., description="Whether dependencies are available")
    gemini_client_ok: bool = Field(..., description="Whether Gemini client is available")
    message: str = Field(..., description="Status message") 