# PuzzleCraft AI - Phase 2 AI 서비스 구현 가이드

## 개요
Phase 2에서는 PuzzleCraft AI의 핵심 AI 서비스들을 구현했습니다. 이 문서는 구현된 AI 서비스들의 설정, 실행, 사용 방법을 안내합니다.

## 🎯 Phase 2에서 완료된 작업

### ✅ 구현된 AI 서비스들
1. **OCR 서비스** (포트 8001)
   - Pytesseract 및 EasyOCR 기반 텍스트 추출
   - 이미지 전처리 및 텍스트 퍼즐 생성
   - 한국어/영어 지원

2. **이미지 세그멘테이션 서비스** (포트 8002)
   - Mask R-CNN 기반 객체 분할
   - 세그멘테이션 기반 퍼즐 조각 생성
   - 이미지 복잡도 분석

3. **스타일 변환 서비스** (포트 8003)
   - 6가지 예술적 스타일 변환 (수채화, 만화, 픽셀아트, 유화, 스케치, 애니메이션)
   - 배치 스타일 적용
   - 미리보기 기능

## 🔧 설치 및 설정

### 1. 시스템 요구사항
```bash
# Python 3.9 이상
# CUDA 지원 GPU (권장, CPU도 가능)
# 최소 8GB RAM (GPU 사용 시 4GB VRAM 권장)
```

### 2. OCR 서비스 설정

#### 2.1 Tesseract 설치 (Windows)
```bash
# Tesseract OCR 다운로드 및 설치
# https://github.com/UB-Mannheim/tesseract/wiki
# 기본 설치 경로: C:\Program Files\Tesseract-OCR\tesseract.exe

# 한국어 언어팩 설치 필요
```

#### 2.2 OCR 서비스 의존성 설치
```bash
cd backend\ocr-service
pip install -r requirements.txt
```

#### 2.3 OCR 서비스 실행
```bash
cd backend\ocr-service
python main.py
# 서비스 URL: http://localhost:8001
```

### 3. 이미지 세그멘테이션 서비스 설정

#### 3.1 의존성 설치
```bash
cd backend\segmentation-service
pip install -r requirements.txt
```

#### 3.2 세그멘테이션 서비스 실행
```bash
cd backend\segmentation-service
python main.py
# 서비스 URL: http://localhost:8002
```

### 4. 스타일 변환 서비스 설정

#### 4.1 의존성 설치
```bash
cd backend\style-transfer
pip install -r requirements.txt
```

#### 4.2 OpenCV 추가 모듈 설치
```bash
# OpenCV contrib 모듈 설치 (oil painting 효과용)
pip install opencv-contrib-python==4.8.1.78
```

#### 4.3 스타일 변환 서비스 실행
```bash
cd backend\style-transfer
python main.py
# 서비스 URL: http://localhost:8003
```

## 📚 API 사용 가이드

### 1. OCR 서비스 API

#### 1.1 기본 엔드포인트
```bash
# 서비스 상태 확인
GET http://localhost:8001/health

# Pytesseract로 텍스트 추출
POST http://localhost:8001/extract-text/pytesseract
Content-Type: multipart/form-data
file: [이미지 파일]

# EasyOCR로 텍스트 추출
POST http://localhost:8001/extract-text/easyocr
Content-Type: multipart/form-data
file: [이미지 파일]

# 두 방법 모두 사용하여 최적 결과 반환
POST http://localhost:8001/extract-text/combined
Content-Type: multipart/form-data
file: [이미지 파일]
```

#### 1.2 텍스트 퍼즐 생성
```bash
POST http://localhost:8001/create-text-puzzle
Content-Type: multipart/form-data
file: [이미지 파일]
method: "combined"  # pytesseract, easyocr, combined 중 선택
```

#### 1.3 이미지 전처리
```bash
POST http://localhost:8001/preprocess-image
Content-Type: multipart/form-data
file: [이미지 파일]
```

### 2. 이미지 세그멘테이션 서비스 API

#### 2.1 객체 분할
```bash
POST http://localhost:8002/segment-objects
Content-Type: multipart/form-data
file: [이미지 파일]
confidence_threshold: 0.5  # 0.1-1.0 사이 값
```

#### 2.2 퍼즐 조각 생성
```bash
POST http://localhost:8002/create-puzzle-pieces
Content-Type: multipart/form-data
file: [이미지 파일]
piece_count: 20  # 5-200 사이 값
```

#### 2.3 통합 처리 (분할 + 퍼즐 생성)
```bash
POST http://localhost:8002/segment-and-create-puzzle
Content-Type: multipart/form-data
file: [이미지 파일]
piece_count: 20
confidence_threshold: 0.5
```

#### 2.4 이미지 복잡도 분석
```bash
POST http://localhost:8002/analyze-image-complexity
Content-Type: multipart/form-data
file: [이미지 파일]
```

### 3. 스타일 변환 서비스 API

#### 3.1 스타일 적용
```bash
POST http://localhost:8003/apply-style
Content-Type: multipart/form-data
file: [이미지 파일]
style_type: "watercolor"  # watercolor, cartoon, pixel_art, oil_painting, sketch, anime
iterations: 300  # 50-1000 사이 값
```

#### 3.2 배치 스타일 적용
```bash
POST http://localhost:8003/batch-apply-styles
Content-Type: multipart/form-data
file: [이미지 파일]
styles: "watercolor,cartoon,sketch"  # 쉼표로 구분된 스타일 목록
```

#### 3.3 스타일 미리보기
```bash
POST http://localhost:8003/preview-style
Content-Type: multipart/form-data
file: [이미지 파일]
style_type: "watercolor"
```

#### 3.4 사용 가능한 스타일 조회
```bash
GET http://localhost:8003/available-styles
```

#### 3.5 결과 파일 다운로드
```bash
GET http://localhost:8003/download/{filename}
```

## 🔄 서비스 통합 예제

### Python 클라이언트 예제
```python
import requests
import json

# 1. OCR로 텍스트 추출
def extract_text(image_path):
    with open(image_path, 'rb') as f:
        files = {'file': f}
        response = requests.post('http://localhost:8001/extract-text/combined', files=files)
        return response.json()

# 2. 이미지 세그멘테이션
def segment_image(image_path):
    with open(image_path, 'rb') as f:
        files = {'file': f}
        data = {'confidence_threshold': 0.5}
        response = requests.post('http://localhost:8002/segment-objects', files=files, data=data)
        return response.json()

# 3. 스타일 변환
def apply_style(image_path, style_type):
    with open(image_path, 'rb') as f:
        files = {'file': f}
        data = {'style_type': style_type, 'iterations': 300}
        response = requests.post('http://localhost:8003/apply-style', files=files, data=data)
        return response.json()

# 사용 예제
image_path = "test_image.jpg"

# OCR 실행
ocr_result = extract_text(image_path)
print("추출된 텍스트:", ocr_result.get('text', ''))

# 세그멘테이션 실행
seg_result = segment_image(image_path)
print("감지된 객체 수:", seg_result.get('objects_found', 0))

# 스타일 변환 실행
style_result = apply_style(image_path, 'watercolor')
print("스타일 변환 결과:", style_result.get('output_path', ''))
```

### JavaScript/Node.js 클라이언트 예제
```javascript
const FormData = require('form-data');
const fs = require('fs');
const axios = require('axios');

// OCR 텍스트 추출
async function extractText(imagePath) {
    const form = new FormData();
    form.append('file', fs.createReadStream(imagePath));
    
    try {
        const response = await axios.post('http://localhost:8001/extract-text/combined', form, {
            headers: form.getHeaders()
        });
        return response.data;
    } catch (error) {
        console.error('OCR 오류:', error.message);
        return null;
    }
}

// 스타일 변환
async function applyStyle(imagePath, styleType) {
    const form = new FormData();
    form.append('file', fs.createReadStream(imagePath));
    form.append('style_type', styleType);
    form.append('iterations', '300');
    
    try {
        const response = await axios.post('http://localhost:8003/apply-style', form, {
            headers: form.getHeaders()
        });
        return response.data;
    } catch (error) {
        console.error('스타일 변환 오류:', error.message);
        return null;
    }
}

// 사용 예제
(async () => {
    const imagePath = 'test_image.jpg';
    
    // OCR 실행
    const ocrResult = await extractText(imagePath);
    if (ocrResult) {
        console.log('추출된 텍스트:', ocrResult.text);
    }
    
    // 스타일 변환 실행
    const styleResult = await applyStyle(imagePath, 'cartoon');
    if (styleResult && styleResult.success) {
        console.log('스타일 변환 완료:', styleResult.output_path);
    }
})();
```

## 🐳 Docker를 사용한 실행

### 1. 개별 서비스 Docker 실행
```bash
# OCR 서비스
cd backend\ocr-service
docker build -t puzzlecraft-ocr .
docker run -p 8001:8001 puzzlecraft-ocr

# 세그멘테이션 서비스
cd backend\segmentation-service
docker build -t puzzlecraft-segmentation .
docker run -p 8002:8002 puzzlecraft-segmentation

# 스타일 변환 서비스
cd backend\style-transfer
docker build -t puzzlecraft-style .
docker run -p 8003:8003 puzzlecraft-style
```

### 2. Docker Compose로 전체 실행
```yaml
# docker-compose.ai-services.yml
version: '3.8'

services:
  ocr-service:
    build: ./backend/ocr-service
    ports:
      - "8001:8001"
    volumes:
      - ./backend/ocr-service:/app
    environment:
      - PYTHONPATH=/app

  segmentation-service:
    build: ./backend/segmentation-service
    ports:
      - "8002:8002"
    volumes:
      - ./backend/segmentation-service:/app
    environment:
      - PYTHONPATH=/app

  style-transfer-service:
    build: ./backend/style-transfer
    ports:
      - "8003:8003"
    volumes:
      - ./backend/style-transfer:/app
    environment:
      - PYTHONPATH=/app
```

```bash
# 실행
docker-compose -f docker-compose.ai-services.yml up -d
```

## 🔧 성능 최적화

### 1. GPU 가속 설정
```python
# 각 서비스에서 GPU 사용 확인
import torch
print(f"CUDA 사용 가능: {torch.cuda.is_available()}")
print(f"GPU 개수: {torch.cuda.device_count()}")
```

### 2. 메모리 최적화
```bash
# 환경 변수 설정으로 메모리 사용량 제한
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512
```

### 3. 배치 처리 최적화
```python
# 여러 이미지 동시 처리를 위한 배치 크기 조정
# 각 서비스의 설정에서 batch_size 매개변수 조정
```

## 🧪 테스트 및 검증

### 1. 서비스 상태 확인
```bash
# 모든 서비스 상태 확인
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
```

### 2. 기능 테스트
```bash
# 테스트 이미지로 각 서비스 기능 확인
# test_images/ 디렉토리에 샘플 이미지 준비 필요
```

### 3. 성능 벤치마크
```python
import time
import requests

def benchmark_service(url, image_path, iterations=10):
    times = []
    for i in range(iterations):
        start_time = time.time()
        with open(image_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(url, files=files)
        end_time = time.time()
        times.append(end_time - start_time)
    
    avg_time = sum(times) / len(times)
    print(f"평균 처리 시간: {avg_time:.2f}초")
    return avg_time

# 각 서비스 벤치마크
benchmark_service('http://localhost:8001/extract-text/combined', 'test.jpg')
benchmark_service('http://localhost:8002/segment-objects', 'test.jpg')
benchmark_service('http://localhost:8003/apply-style', 'test.jpg')
```

## 🚀 다음 단계 (Phase 3)

Phase 2 완료 후 다음 작업들을 진행합니다:
1. **퍼즐 생성 엔진 개발** - AI 서비스들을 통합한 지능형 퍼즐 생성
2. **웹 프론트엔드 AI 통합** - React 앱에서 AI 서비스 호출
3. **실시간 처리 최적화** - WebSocket을 통한 실시간 AI 처리
4. **캐싱 및 성능 개선** - Redis를 활용한 결과 캐싱

## 📞 문제 해결

### 일반적인 문제들

#### 1. CUDA 메모리 부족
```bash
# 해결 방법: 배치 크기 줄이기 또는 CPU 모드 사용
export CUDA_VISIBLE_DEVICES=""  # CPU 모드 강제 사용
```

#### 2. Tesseract 경로 오류
```python
# ocr_processor.py에서 경로 수정
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
```

#### 3. 모델 다운로드 실패
```bash
# 인터넷 연결 확인 및 방화벽 설정
# 프록시 환경에서는 환경 변수 설정 필요
```

#### 4. 포트 충돌
```bash
# 다른 포트 사용
python main.py --port 8011  # OCR 서비스
python main.py --port 8012  # 세그멘테이션 서비스
python main.py --port 8013  # 스타일 변환 서비스
```

## 📝 참고 자료

- [PyTorch 공식 문서](https://pytorch.org/docs/)
- [OpenCV 공식 문서](https://docs.opencv.org/)
- [Tesseract OCR 문서](https://tesseract-ocr.github.io/)
- [EasyOCR GitHub](https://github.com/JaidedAI/EasyOCR)
- [Mask R-CNN 논문](https://arxiv.org/abs/1703.06870)
- [Neural Style Transfer 논문](https://arxiv.org/abs/1508.06576)

이제 Phase 2의 핵심 AI 서비스들이 완성되었습니다. 각 서비스는 독립적으로 실행되며, RESTful API를 통해 다른 서비스들과 통신할 수 있습니다.