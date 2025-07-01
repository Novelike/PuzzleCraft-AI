import pytesseract
import easyocr
from PIL import Image
import cv2
import numpy as np
from typing import Dict, List, Any
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OCRProcessor:
    def __init__(self):
        """Initialize OCR processor with both pytesseract and easyocr"""
        try:
            self.easy_reader = easyocr.Reader(['ko', 'en'])
            logger.info("EasyOCR initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize EasyOCR: {e}")
            self.easy_reader = None
        
        # Configure pytesseract path if needed (Windows)
        if os.name == 'nt':  # Windows
            pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    
    def extract_text_pytesseract(self, image_path: str) -> Dict[str, Any]:
        """Extract text using pytesseract"""
        try:
            image = Image.open(image_path)
            
            # Extract text
            text = pytesseract.image_to_string(image, lang='kor+eng')
            
            # Extract bounding boxes
            boxes = pytesseract.image_to_boxes(image, lang='kor+eng')
            
            # Extract detailed data with confidence
            data = pytesseract.image_to_data(image, lang='kor+eng', output_type=pytesseract.Output.DICT)
            
            return {
                'text': text.strip(),
                'boxes': self._parse_boxes(boxes),
                'confidence': self._calculate_average_confidence(data),
                'detailed_data': data,
                'method': 'pytesseract'
            }
        except Exception as e:
            logger.error(f"Pytesseract extraction failed: {e}")
            return {
                'text': '',
                'boxes': [],
                'confidence': 0,
                'error': str(e),
                'method': 'pytesseract'
            }
    
    def extract_text_easyocr(self, image_path: str) -> Dict[str, Any]:
        """Extract text using easyocr"""
        if not self.easy_reader:
            return {
                'text': '',
                'boxes': [],
                'confidence': 0,
                'error': 'EasyOCR not initialized',
                'method': 'easyocr'
            }
        
        try:
            results = self.easy_reader.readtext(image_path)
            
            # Extract text and calculate average confidence
            texts = []
            confidences = []
            boxes = []
            
            for result in results:
                bbox, text, confidence = result
                texts.append(text)
                confidences.append(confidence)
                boxes.append({
                    'text': text,
                    'bbox': bbox,
                    'confidence': confidence
                })
            
            return {
                'text': ' '.join(texts),
                'boxes': boxes,
                'confidence': np.mean(confidences) if confidences else 0,
                'method': 'easyocr'
            }
        except Exception as e:
            logger.error(f"EasyOCR extraction failed: {e}")
            return {
                'text': '',
                'boxes': [],
                'confidence': 0,
                'error': str(e),
                'method': 'easyocr'
            }
    
    def extract_text_combined(self, image_path: str) -> Dict[str, Any]:
        """Extract text using both methods and return the best result"""
        pytesseract_result = self.extract_text_pytesseract(image_path)
        easyocr_result = self.extract_text_easyocr(image_path)
        
        # Choose the result with higher confidence
        if pytesseract_result.get('confidence', 0) > easyocr_result.get('confidence', 0):
            best_result = pytesseract_result
            alternative = easyocr_result
        else:
            best_result = easyocr_result
            alternative = pytesseract_result
        
        return {
            'primary_result': best_result,
            'alternative_result': alternative,
            'combined_text': best_result.get('text', ''),
            'confidence': best_result.get('confidence', 0),
            'method': 'combined'
        }
    
    def create_text_puzzle(self, ocr_results: Dict[str, Any]) -> Dict[str, Any]:
        """Create text puzzle from OCR results"""
        text = ocr_results.get('text', '')
        if not text:
            return {
                'puzzle_type': 'word_puzzle',
                'words': [],
                'positions': [],
                'hints': [],
                'error': 'No text found in image'
            }
        
        # Split text into words and filter out empty strings
        words = [word.strip() for word in text.split() if word.strip()]
        
        # Generate hints for words
        hints = self._generate_hints(words)
        
        return {
            'puzzle_type': 'word_puzzle',
            'words': words,
            'positions': ocr_results.get('boxes', []),
            'hints': hints,
            'original_text': text,
            'word_count': len(words)
        }
    
    def preprocess_image(self, image_path: str, output_path: str = None) -> str:
        """Preprocess image for better OCR results"""
        try:
            # Read image
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError("Could not read image")
            
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply noise reduction
            denoised = cv2.medianBlur(gray, 5)
            
            # Apply thresholding
            _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Save preprocessed image
            if output_path is None:
                base, ext = os.path.splitext(image_path)
                output_path = f"{base}_preprocessed{ext}"
            
            cv2.imwrite(output_path, thresh)
            return output_path
            
        except Exception as e:
            logger.error(f"Image preprocessing failed: {e}")
            return image_path  # Return original path if preprocessing fails
    
    def _parse_boxes(self, boxes_string: str) -> List[Dict[str, Any]]:
        """Parse pytesseract boxes string into structured data"""
        boxes = []
        for line in boxes_string.split('\n'):
            if line.strip():
                parts = line.split()
                if len(parts) >= 6:
                    boxes.append({
                        'char': parts[0],
                        'left': int(parts[1]),
                        'bottom': int(parts[2]),
                        'right': int(parts[3]),
                        'top': int(parts[4]),
                        'page': int(parts[5])
                    })
        return boxes
    
    def _calculate_average_confidence(self, data: Dict[str, List]) -> float:
        """Calculate average confidence from pytesseract data"""
        confidences = [conf for conf in data.get('conf', []) if conf > 0]
        return np.mean(confidences) if confidences else 0
    
    def _generate_hints(self, words: List[str]) -> List[str]:
        """Generate simple hints for words"""
        hints = []
        for word in words:
            if len(word) <= 2:
                hints.append(f"짧은 단어 ({len(word)}글자)")
            elif len(word) <= 5:
                hints.append(f"중간 길이 단어 ({len(word)}글자)")
            else:
                hints.append(f"긴 단어 ({len(word)}글자)")
        return hints