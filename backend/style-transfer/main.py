from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import uvicorn
import os
import tempfile
import shutil
from pathlib import Path
import logging

from style_transfer import NeuralStyleTransfer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="PuzzleCraft AI - Style Transfer Service",
    description="Neural style transfer service for artistic image transformation",
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

# Initialize style transfer processor
try:
    style_processor = NeuralStyleTransfer()
    logger.info("Style transfer processor initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize style transfer processor: {e}")
    style_processor = None

# Create uploads and outputs directories
UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("outputs")
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# Pydantic models
class StyleTransferResponse(BaseModel):
    success: bool
    style_type: str
    output_path: Optional[str] = None
    style_info: Optional[Dict] = None
    processing_details: Optional[Dict] = None
    error: Optional[str] = None

class BatchStyleResponse(BaseModel):
    batch_results: Dict[str, Any]
    total_processed: int
    total_failed: int

class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    model_loaded: bool

class StyleInfo(BaseModel):
    name: str
    description: str
    characteristics: List[str]

@app.get("/", response_model=HealthResponse)
async def root():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        service="Style Transfer Service",
        version="1.0.0",
        model_loaded=style_processor is not None
    )

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Detailed health check"""
    return HealthResponse(
        status="healthy" if style_processor is not None else "unhealthy",
        service="Style Transfer Service",
        version="1.0.0",
        model_loaded=style_processor is not None
    )

@app.post("/apply-style", response_model=StyleTransferResponse)
async def apply_style(
    file: UploadFile = File(...),
    style_type: str = Form(...),
    iterations: int = Form(300)
):
    """Apply style transfer to uploaded image"""
    if style_processor is None:
        raise HTTPException(status_code=503, detail="Style transfer model not loaded")
    
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    available_styles = style_processor.get_available_styles()
    if style_type not in available_styles:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported style: {style_type}. Available: {list(available_styles.keys())}"
        )
    
    if not 50 <= iterations <= 1000:
        raise HTTPException(status_code=400, detail="Iterations must be between 50 and 1000")
    
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            tmp_path = tmp_file.name
        
        # Generate output path
        output_filename = f"{Path(file.filename).stem}_{style_type}.jpg"
        output_path = OUTPUT_DIR / output_filename
        
        # Apply style transfer
        result = style_processor.apply_style(tmp_path, style_type, str(output_path), iterations)
        
        # Clean up temporary file
        os.unlink(tmp_path)
        
        return StyleTransferResponse(**result)
        
    except Exception as e:
        logger.error(f"Style transfer error: {e}")
        raise HTTPException(status_code=500, detail=f"Style transfer failed: {str(e)}")

@app.post("/batch-apply-styles", response_model=BatchStyleResponse)
async def batch_apply_styles(
    file: UploadFile = File(...),
    styles: str = Form(...)  # Comma-separated list of styles
):
    """Apply multiple styles to the same image"""
    if style_processor is None:
        raise HTTPException(status_code=503, detail="Style transfer model not loaded")
    
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Parse styles list
    style_list = [style.strip() for style in styles.split(',')]
    available_styles = style_processor.get_available_styles()
    
    # Validate styles
    invalid_styles = [s for s in style_list if s not in available_styles]
    if invalid_styles:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid styles: {invalid_styles}. Available: {list(available_styles.keys())}"
        )
    
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            tmp_path = tmp_file.name
        
        # Apply batch style transfer
        result = style_processor.batch_apply_styles(tmp_path, style_list, str(OUTPUT_DIR))
        
        # Clean up temporary file
        os.unlink(tmp_path)
        
        return BatchStyleResponse(**result)
        
    except Exception as e:
        logger.error(f"Batch style transfer error: {e}")
        raise HTTPException(status_code=500, detail=f"Batch style transfer failed: {str(e)}")

@app.get("/available-styles")
async def get_available_styles():
    """Get list of available styles with descriptions"""
    if style_processor is None:
        raise HTTPException(status_code=503, detail="Style transfer model not loaded")
    
    try:
        styles = style_processor.get_available_styles()
        formatted_styles = []
        
        for name, info in styles.items():
            formatted_styles.append({
                "name": name,
                "description": info["description"],
                "characteristics": info["characteristics"]
            })
        
        return {
            "total_styles": len(styles),
            "styles": formatted_styles,
            "style_names": list(styles.keys())
        }
    except Exception as e:
        logger.error(f"Error getting available styles: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get available styles: {str(e)}")

@app.get("/style-info/{style_name}")
async def get_style_info(style_name: str):
    """Get detailed information about a specific style"""
    if style_processor is None:
        raise HTTPException(status_code=503, detail="Style transfer model not loaded")
    
    try:
        styles = style_processor.get_available_styles()
        if style_name not in styles:
            raise HTTPException(status_code=404, detail=f"Style '{style_name}' not found")
        
        return {
            "name": style_name,
            "info": styles[style_name],
            "usage_tips": {
                "watercolor": "Best for landscapes and portraits",
                "cartoon": "Great for creating animated-style images",
                "pixel_art": "Perfect for retro gaming aesthetics",
                "oil_painting": "Ideal for classical art reproduction",
                "sketch": "Good for creating artistic line drawings",
                "anime": "Best for character illustrations"
            }.get(style_name, "General artistic transformation")
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting style info: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get style info: {str(e)}")

@app.get("/download/{filename}")
async def download_file(filename: str):
    """Download processed image file"""
    file_path = OUTPUT_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type='image/jpeg'
    )

@app.delete("/cleanup/{filename}")
async def cleanup_file(filename: str):
    """Delete processed image file"""
    file_path = OUTPUT_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        os.unlink(file_path)
        return {"message": f"File {filename} deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")

@app.post("/preview-style")
async def preview_style(
    file: UploadFile = File(...),
    style_type: str = Form(...)
):
    """Generate a quick preview of style transfer (lower quality, faster processing)"""
    if style_processor is None:
        raise HTTPException(status_code=503, detail="Style transfer model not loaded")
    
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    available_styles = style_processor.get_available_styles()
    if style_type not in available_styles:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported style: {style_type}. Available: {list(available_styles.keys())}"
        )
    
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            tmp_path = tmp_file.name
        
        # Generate preview with fewer iterations for speed
        preview_filename = f"preview_{Path(file.filename).stem}_{style_type}.jpg"
        preview_path = OUTPUT_DIR / preview_filename
        
        # Apply style transfer with reduced iterations for preview
        result = style_processor.apply_style(tmp_path, style_type, str(preview_path), iterations=100)
        
        # Clean up temporary file
        os.unlink(tmp_path)
        
        if result.get('success'):
            return {
                "success": True,
                "preview_filename": preview_filename,
                "download_url": f"/download/{preview_filename}",
                "style_type": style_type,
                "note": "This is a quick preview with reduced quality"
            }
        else:
            return result
        
    except Exception as e:
        logger.error(f"Style preview error: {e}")
        raise HTTPException(status_code=500, detail=f"Style preview failed: {str(e)}")

@app.get("/model-info")
async def get_model_info():
    """Get information about the style transfer model"""
    if style_processor is None:
        raise HTTPException(status_code=503, detail="Style transfer model not loaded")
    
    try:
        import torch
        return {
            "model_name": "Neural Style Transfer with VGG19",
            "framework": "PyTorch",
            "pytorch_version": torch.__version__,
            "device": str(style_processor.device),
            "cuda_available": torch.cuda.is_available(),
            "supported_styles": len(style_processor.get_available_styles()),
            "input_format": "RGB images (resized to 512x512)",
            "output_format": "Stylized RGB images",
            "processing_time": "Varies by style and iterations (30s - 5min)"
        }
    except Exception as e:
        logger.error(f"Error getting model info: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get model info: {str(e)}")

@app.get("/list-outputs")
async def list_output_files():
    """List all processed output files"""
    try:
        files = []
        for file_path in OUTPUT_DIR.glob("*"):
            if file_path.is_file():
                files.append({
                    "filename": file_path.name,
                    "size": file_path.stat().st_size,
                    "created": file_path.stat().st_ctime,
                    "download_url": f"/download/{file_path.name}"
                })
        
        return {
            "total_files": len(files),
            "files": sorted(files, key=lambda x: x["created"], reverse=True)
        }
    except Exception as e:
        logger.error(f"Error listing output files: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list output files: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8003,
        reload=True,
        log_level="info"
    )