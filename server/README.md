# CBSE Question Parser API

A FastAPI-based REST API server for processing CBSE Mathematics exam papers. The API provides endpoints for extracting diagrams, mapping them to questions, extracting marks allocation, and generating clean Markdown questions.

## Features

- 🔍 **Diagram Extraction**: Extract diagrams from PDFs using DocLayout YOLO
- 🎯 **Diagram Mapping**: Map diagrams to their corresponding questions using Gemini AI
- 📊 **Marks Extraction**: Extract marks allocation and question types using Gemini AI
- 📝 **Question Extraction**: Extract questions in clean Markdown format using Gemini AI
- 🃏 **Question Cards**: Generate individual question cards with complete information
- 🚀 **End-to-End Pipeline**: Process entire exam papers in one API call

## API Endpoints

### Core Processing Endpoints

- `POST /api/v1/extract-diagrams` - Extract diagrams from PDF
- `POST /api/v1/map-diagrams` - Map diagrams to questions
- `POST /api/v1/extract-marks` - Extract marks allocation
- `POST /api/v1/extract-questions` - Extract questions in Markdown
- `POST /api/v1/generate-cards` - Generate question cards
- `POST /api/v1/process-pipeline` - Run complete end-to-end processing

### Status and Information Endpoints

- `GET /health` - Health check
- `GET /status` - Detailed system status
- `GET /api/v1/extract-diagrams/status` - Diagram extraction status
- `GET /api/v1/map-diagrams/status` - Diagram mapping status
- `GET /api/v1/extract-marks/status` - Marks extraction status
- `GET /api/v1/extract-questions/status` - Question extraction status
- `GET /api/v1/generate-cards/status` - Question cards status
- `GET /api/v1/process-pipeline/status` - Pipeline status

### Result Retrieval Endpoints

- `GET /api/v1/map-diagrams/result/{filename}` - Get mapping results
- `GET /api/v1/extract-marks/result/{filename}` - Get marks results
- `GET /api/v1/extract-questions/result/{filename}` - Get questions results
- `GET /api/v1/extract-questions/download/{filename}` - Download questions markdown
- `GET /api/v1/extract-questions/raw/{filename}` - Get raw AI response
- `GET /api/v1/generate-cards/check/{filename}` - Check card prerequisites

### Utility Endpoints

- `GET /api/v1/process-pipeline/logs` - Get pipeline logs information
- `DELETE /api/v1/process-pipeline/cleanup` - Clean up old logs
- `POST /api/v1/generate-cards/force/{filename}` - Force generate cards

## Quick Start

### Prerequisites

1. **Python 3.8+**
2. **Required Dependencies**:

   - PyTorch (for DocLayout YOLO)
   - FastAPI and Uvicorn
   - Google Genai SDK
   - Other dependencies listed in `requirements.txt`

3. **Environment Variables**:
   ```bash
   export GEMINI_API_KEY="your-gemini-api-key"
   ```

### Installation

1. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

2. **Start the server**:

   ```bash
   cd server
   python main.py
   ```

   Or using uvicorn directly:

   ```bash
   uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload
   ```

3. **Access the API**:
   - API Documentation: http://localhost:8000/docs
   - ReDoc Documentation: http://localhost:8000/redoc
   - Health Check: http://localhost:8000/health

## Usage Examples

### 1. Health Check

```bash
curl http://localhost:8000/health
```

### 2. Extract Diagrams

```bash
curl -X POST "http://localhost:8000/api/v1/extract-diagrams" \
  -H "Content-Type: multipart/form-data" \
  -F "pdf_file=@sample_paper.pdf" \
  -F "conf_threshold=0.25" \
  -F "iou_threshold=0.45"
```

### 3. Extract Questions

```bash
curl -X POST "http://localhost:8000/api/v1/extract-questions" \
  -H "Content-Type: multipart/form-data" \
  -F "pdf_file=@sample_paper.pdf"
```

### 4. Run Complete Pipeline

```bash
curl -X POST "http://localhost:8000/api/v1/process-pipeline" \
  -H "Content-Type: multipart/form-data" \
  -F "pdf_file=@sample_paper.pdf" \
  -F "conf_threshold=0.25" \
  -F "iou_threshold=0.45" \
  -F "include_cards=true"
```

### 5. Get Results

```bash
curl http://localhost:8000/api/v1/extract-questions/result/sample_paper
```

### 6. Download Questions

```bash
curl -O http://localhost:8000/api/v1/extract-questions/download/sample_paper
```

## Response Format

### Success Response

```json
{
  "success": true,
  "message": "Operation completed successfully",
  "timestamp": "2024-01-01T12:00:00Z",
  "data": {
    // endpoint-specific data
  }
}
```

### Error Response

```json
{
  "success": false,
  "message": "Error description",
  "timestamp": "2024-01-01T12:00:00Z",
  "error": "Detailed error message",
  "error_code": "ERROR_CODE"
}
```

## Processing Pipeline

The complete processing pipeline consists of 5 steps:

1. **Step 1: Diagram Extraction**

   - Uses DocLayout YOLO to detect and extract diagrams
   - Generates preview images and metadata
   - Saves extracted diagrams to `logs/diagrams/`

2. **Step 2: Diagram Mapping**

   - Maps extracted diagrams to their corresponding questions
   - Uses Gemini AI for intelligent analysis
   - Saves mappings to `logs/diagram_mappings/`

3. **Step 3: Marks Extraction**

   - Extracts marks allocation for each question
   - Classifies question types (MCQ, Case Study, etc.)
   - Saves marks data to `logs/marks_mappings/`

4. **Step 4: Question Extraction**

   - Extracts questions in clean Markdown format
   - Excludes instructions and diagrams
   - Saves questions to `logs/full_pdf_questions/`

5. **Step 5: Question Cards**
   - Generates individual question cards
   - Combines all extracted information
   - Creates complete question cards with diagrams and marks

## Output Files

All processing outputs are saved in the `logs/` directory:

- `logs/diagrams/` - Extracted diagram images and metadata
- `logs/diagram_mappings/` - Diagram-to-question mappings (JSON)
- `logs/marks_mappings/` - Marks allocation data (JSON)
- `logs/full_pdf_questions/` - Extracted questions (Markdown)
- `logs/gemini_questions/` - Individual page questions (Markdown)

## Error Handling

The API provides comprehensive error handling:

- **503 Service Unavailable**: Missing dependencies or API keys
- **400 Bad Request**: Invalid file format or parameters
- **404 Not Found**: Requested resource not found
- **500 Internal Server Error**: Processing errors

## Configuration

### Environment Variables

- `GEMINI_API_KEY`: Required for AI processing
- `CUDA_VISIBLE_DEVICES`: GPU configuration (optional)

### Default Parameters

- Diagram detection confidence threshold: 0.25
- IoU threshold for NMS: 0.45
- Maximum file size: 50MB
- Supported formats: PDF only

## Dependencies

### Core Dependencies

- `fastapi>=0.104.1`
- `uvicorn>=0.24.0`
- `pydantic>=2.5.0`
- `python-multipart>=0.0.6`

### Processing Dependencies

- `torch` (PyTorch for DocLayout YOLO)
- `doclayout-yolo>=0.0.4`
- `google-genai` (Gemini AI SDK)
- `PyMuPDF` (PDF processing)
- `pdf2image>=1.16.3`

### Optional Dependencies

- `streamlit>=1.28.1` (for UI)
- `boto3>=1.38.36` (for AWS integration)

## Development

### Project Structure

```
server/
├── main.py              # FastAPI application
├── models/              # Pydantic models
│   ├── requests.py      # Request models
│   └── responses.py     # Response models
├── routes/              # API route handlers
│   ├── step1_diagrams.py
│   ├── step2_mapping.py
│   ├── step3_marks.py
│   ├── step4_questions.py
│   ├── step5_cards.py
│   └── pipeline.py
└── utils/               # Utility functions
    └── file_handler.py
```

### Adding New Endpoints

1. Create route handler in `routes/`
2. Define request/response models in `models/`
3. Register router in `main.py`
4. Update documentation

## Monitoring

### Health Checks

- `/health` - Basic health check
- `/status` - Detailed system status
- Individual endpoint status checks

### Logging

- All processing steps are logged
- Error tracking and reporting
- Performance monitoring

## Security

- File type validation
- File size limits
- Filename sanitization
- CORS configuration
- Error message sanitization

## Performance

- Parallel processing where possible
- Efficient file handling
- Memory optimization
- GPU acceleration (when available)

## Troubleshooting

### Common Issues

1. **"Missing required dependencies"**

   - Install PyTorch and other dependencies
   - Check GPU availability for DocLayout YOLO

2. **"Gemini client not available"**

   - Set GEMINI_API_KEY environment variable
   - Verify API key is valid

3. **"File processing failed"**

   - Check file format (PDF only)
   - Verify file is not corrupted
   - Check file size limits

4. **"Previous steps not completed"**
   - Run steps in order or use pipeline endpoint
   - Check logs directory for required files

### Debug Mode

Start server with debug mode:

```bash
uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload --log-level debug
```

## Support

For issues and questions:

1. Check the API documentation at `/docs`
2. Review error messages and logs
3. Verify dependencies and configuration
4. Check file format and size requirements

## License

This project is part of the CBSE Question Parser system. See main project LICENSE for details.
