from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uvicorn
import os
import tempfile
import shutil
from pathlib import Path
import logging

from ocr_processor import OCRProcessor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="PuzzleCraft AI - OCR Service",
    description="OCR service for text extraction and puzzle generation",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize OCR processor
ocr_processor = OCRProcessor()

# Create uploads directory
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Pydantic models
class OCRResponse(BaseModel):
    text: str
    confidence: float
    method: str
    boxes: list
    error: Optional[str] = None

class TextPuzzleResponse(BaseModel):
    puzzle_type: str
    words: list
    positions: list
    hints: list
    original_text: str
    word_count: int
    error: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    service: str
    version: str

@app.get("/", response_model=HealthResponse)
async def root():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        service="OCR Service",
        version="1.0.0"
    )

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Detailed health check"""
    return HealthResponse(
        status="healthy",
        service="OCR Service",
        version="1.0.0"
    )

@app.post("/extract-text/pytesseract", response_model=OCRResponse)
async def extract_text_pytesseract(file: UploadFile = File(...)):
    """Extract text using Pytesseract"""
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            tmp_path = tmp_file.name
        
        # Process with OCR
        result = ocr_processor.extract_text_pytesseract(tmp_path)
        
        # Clean up temporary file
        os.unlink(tmp_path)
        
        return OCRResponse(**result)
        
    except Exception as e:
        logger.error(f"Pytesseract extraction error: {e}")
        raise HTTPException(status_code=500, detail=f"OCR processing failed: {str(e)}")

@app.post("/extract-text/easyocr", response_model=OCRResponse)
async def extract_text_easyocr(file: UploadFile = File(...)):
    """Extract text using EasyOCR"""
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            tmp_path = tmp_file.name
        
        # Process with OCR
        result = ocr_processor.extract_text_easyocr(tmp_path)
        
        # Clean up temporary file
        os.unlink(tmp_path)
        
        return OCRResponse(**result)
        
    except Exception as e:
        logger.error(f"EasyOCR extraction error: {e}")
        raise HTTPException(status_code=500, detail=f"OCR processing failed: {str(e)}")

@app.post("/extract-text/combined")
async def extract_text_combined(file: UploadFile = File(...)):
    """Extract text using both OCR methods and return the best result"""
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            tmp_path = tmp_file.name
        
        # Process with combined OCR
        result = ocr_processor.extract_text_combined(tmp_path)
        
        # Clean up temporary file
        os.unlink(tmp_path)
        
        return JSONResponse(content=result)
        
    except Exception as e:
        logger.error(f"Combined OCR extraction error: {e}")
        raise HTTPException(status_code=500, detail=f"OCR processing failed: {str(e)}")

@app.post("/create-text-puzzle", response_model=TextPuzzleResponse)
async def create_text_puzzle(file: UploadFile = File(...), method: str = Form("combined")):
    """Create a text puzzle from an image"""
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    if method not in ["pytesseract", "easyocr", "combined"]:
        raise HTTPException(status_code=400, detail="Method must be 'pytesseract', 'easyocr', or 'combined'")
    
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            tmp_path = tmp_file.name
        
        # Extract text based on method
        if method == "pytesseract":
            ocr_result = ocr_processor.extract_text_pytesseract(tmp_path)
        elif method == "easyocr":
            ocr_result = ocr_processor.extract_text_easyocr(tmp_path)
        else:  # combined
            combined_result = ocr_processor.extract_text_combined(tmp_path)
            ocr_result = combined_result.get('primary_result', {})
        
        # Create text puzzle
        puzzle_result = ocr_processor.create_text_puzzle(ocr_result)
        
        # Clean up temporary file
        os.unlink(tmp_path)
        
        return TextPuzzleResponse(**puzzle_result)
        
    except Exception as e:
        logger.error(f"Text puzzle creation error: {e}")
        raise HTTPException(status_code=500, detail=f"Puzzle creation failed: {str(e)}")

@app.post("/preprocess-image")
async def preprocess_image(file: UploadFile = File(...)):
    """Preprocess image for better OCR results"""
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            tmp_path = tmp_file.name
        
        # Preprocess image
        processed_path = ocr_processor.preprocess_image(tmp_path)
        
        # Read processed image
        with open(processed_path, 'rb') as f:
            processed_content = f.read()
        
        # Clean up temporary files
        os.unlink(tmp_path)
        if processed_path != tmp_path:
            os.unlink(processed_path)
        
        return JSONResponse(
            content={
                "message": "Image preprocessed successfully",
                "original_size": len(await file.read()),
                "processed_size": len(processed_content)
            }
        )
        
    except Exception as e:
        logger.error(f"Image preprocessing error: {e}")
        raise HTTPException(status_code=500, detail=f"Image preprocessing failed: {str(e)}")

@app.get("/supported-languages")
async def get_supported_languages():
    """Get list of supported languages"""
    return {
        "pytesseract": ["kor", "eng", "kor+eng"],
        "easyocr": ["ko", "en"],
        "default": "kor+eng"
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8003,
        reload=True,
        log_level="info"
    )