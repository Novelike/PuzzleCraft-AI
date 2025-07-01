import pytesseract
import easyocr
import torch
from PIL import Image
import cv2
import numpy as np
from typing import Dict, List, Any, Optional
import os
import logging
import hashlib
import json
import redis.asyncio as redis

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OCRProcessor:
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        """Initialize OCR processor with both pytesseract and easyocr"""
        try:
            # GPU 사용 가능 여부 확인
            gpu_available = torch.cuda.is_available()
            device = "cuda" if gpu_available else "cpu"

            # EasyOCR Reader 초기화 (GPU 설정 포함)
            self.easy_reader = easyocr.Reader(['ko', 'en'], gpu=gpu_available)

            logger.info(f"EasyOCR initialized successfully on device: {device}")
            if gpu_available:
                logger.info(f"GPU acceleration enabled - CUDA device: {torch.cuda.get_device_name(0)}")
            else:
                logger.info("GPU not available, using CPU for EasyOCR")

        except Exception as e:
            logger.error(f"Failed to initialize EasyOCR: {e}")
            self.easy_reader = None

        # Configure pytesseract path if needed (Windows)
        if os.name == 'nt':  # Windows
            pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

        # Redis 캐싱 설정
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
        self.cache_ttl = 3600  # 1시간 캐시 TTL

    async def initialize_redis(self):
        """Redis 클라이언트 초기화"""
        try:
            self.redis_client = redis.from_url(self.redis_url)
            await self.redis_client.ping()
            logger.info("Redis 캐싱 시스템 초기화 완료")
        except Exception as e:
            logger.warning(f"Redis 연결 실패: {str(e)}, 캐싱 없이 동작")
            self.redis_client = None

    async def shutdown_redis(self):
        """Redis 클라이언트 종료"""
        if self.redis_client:
            await self.redis_client.close()

    def _generate_cache_key(self, image_path: str, method: str) -> str:
        """이미지 파일의 캐시 키 생성"""
        try:
            # 파일 내용의 해시값 생성
            with open(image_path, 'rb') as f:
                file_hash = hashlib.md5(f.read()).hexdigest()
            return f"ocr:{method}:{file_hash}"
        except Exception as e:
            logger.error(f"캐시 키 생성 실패: {e}")
            return f"ocr:{method}:{os.path.basename(image_path)}"

    async def _get_cached_result(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """캐시에서 결과 조회"""
        if not self.redis_client:
            return None

        try:
            cached_data = await self.redis_client.get(cache_key)
            if cached_data:
                result = json.loads(cached_data)
                logger.info(f"캐시에서 OCR 결과 조회: {cache_key}")
                return result
        except Exception as e:
            logger.error(f"캐시 조회 실패: {e}")

        return None

    async def _set_cached_result(self, cache_key: str, result: Dict[str, Any]):
        """결과를 캐시에 저장"""
        if not self.redis_client:
            return

        try:
            await self.redis_client.setex(
                cache_key, 
                self.cache_ttl, 
                json.dumps(result, ensure_ascii=False)
            )
            logger.info(f"OCR 결과 캐시 저장: {cache_key}")
        except Exception as e:
            logger.error(f"캐시 저장 실패: {e}")

    async def extract_text_pytesseract_cached(self, image_path: str) -> Dict[str, Any]:
        """캐싱이 적용된 pytesseract 텍스트 추출"""
        cache_key = self._generate_cache_key(image_path, "pytesseract")

        # 캐시에서 결과 조회
        cached_result = await self._get_cached_result(cache_key)
        if cached_result:
            cached_result['from_cache'] = True
            return cached_result

        # 캐시에 없으면 실제 OCR 수행
        result = self.extract_text_pytesseract(image_path)
        result['from_cache'] = False

        # 결과를 캐시에 저장
        await self._set_cached_result(cache_key, result)

        return result

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

    async def extract_text_easyocr_cached(self, image_path: str) -> Dict[str, Any]:
        """캐싱이 적용된 EasyOCR 텍스트 추출"""
        cache_key = self._generate_cache_key(image_path, "easyocr")

        # 캐시에서 결과 조회
        cached_result = await self._get_cached_result(cache_key)
        if cached_result:
            cached_result['from_cache'] = True
            return cached_result

        # 캐시에 없으면 실제 OCR 수행
        result = self.extract_text_easyocr(image_path)
        result['from_cache'] = False

        # 결과를 캐시에 저장
        await self._set_cached_result(cache_key, result)

        return result

    async def extract_text_combined_cached(self, image_path: str) -> Dict[str, Any]:
        """캐싱이 적용된 통합 텍스트 추출"""
        cache_key = self._generate_cache_key(image_path, "combined")

        # 캐시에서 결과 조회
        cached_result = await self._get_cached_result(cache_key)
        if cached_result:
            cached_result['from_cache'] = True
            return cached_result

        # 캐시에 없으면 실제 OCR 수행
        pytesseract_result = await self.extract_text_pytesseract_cached(image_path)
        easyocr_result = await self.extract_text_easyocr_cached(image_path)

        # Choose the result with higher confidence
        if pytesseract_result.get('confidence', 0) > easyocr_result.get('confidence', 0):
            best_result = pytesseract_result
            alternative = easyocr_result
        else:
            best_result = easyocr_result
            alternative = pytesseract_result

        result = {
            'primary_result': best_result,
            'alternative_result': alternative,
            'combined_text': best_result.get('text', ''),
            'confidence': best_result.get('confidence', 0),
            'method': 'combined',
            'from_cache': False
        }

        # 결과를 캐시에 저장
        await self._set_cached_result(cache_key, result)

        return result

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
