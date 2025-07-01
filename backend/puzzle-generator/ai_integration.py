import asyncio
import aiohttp
import logging
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import json
import time
from dataclasses import dataclass
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIServiceType(Enum):
    OCR = "ocr"
    SEGMENTATION = "segmentation"
    STYLE_TRANSFER = "style_transfer"

@dataclass
class AIServiceConfig:
    service_type: AIServiceType
    base_url: str
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0

@dataclass
class AIProcessingRequest:
    image_path: str
    service_type: AIServiceType
    parameters: Dict[str, Any]
    priority: int = 1  # 1=high, 2=medium, 3=low

class AIServiceIntegrator:
    def __init__(self):
        """Initialize AI service integrator"""
        self.services = {
            AIServiceType.OCR: AIServiceConfig(
                service_type=AIServiceType.OCR,
                base_url="http://localhost:8001",
                timeout=30
            ),
            AIServiceType.SEGMENTATION: AIServiceConfig(
                service_type=AIServiceType.SEGMENTATION,
                base_url="http://localhost:8002",
                timeout=60
            ),
            AIServiceType.STYLE_TRANSFER: AIServiceConfig(
                service_type=AIServiceType.STYLE_TRANSFER,
                base_url="http://localhost:8003",
                timeout=120
            )
        }
        
        # Service health status
        self.service_health = {
            service_type: {'status': 'unknown', 'last_check': 0}
            for service_type in AIServiceType
        }
        
        # Request queue for load balancing
        self.request_queue = asyncio.Queue()
        self.processing_stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'average_response_time': 0.0
        }
        
        logger.info("AI Service Integrator initialized")

    async def health_check_all_services(self) -> Dict[AIServiceType, bool]:
        """Check health of all AI services"""
        health_results = {}
        
        tasks = []
        for service_type in AIServiceType:
            tasks.append(self._check_service_health(service_type))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for service_type, result in zip(AIServiceType, results):
            if isinstance(result, Exception):
                health_results[service_type] = False
                logger.error(f"{service_type.value} service health check failed: {result}")
            else:
                health_results[service_type] = result
        
        return health_results

    async def _check_service_health(self, service_type: AIServiceType) -> bool:
        """Check health of a specific service"""
        try:
            config = self.services[service_type]
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.get(f"{config.base_url}/health") as response:
                    if response.status == 200:
                        data = await response.json()
                        is_healthy = data.get('status') == 'healthy'
                        
                        self.service_health[service_type] = {
                            'status': 'healthy' if is_healthy else 'unhealthy',
                            'last_check': time.time(),
                            'response_time': time.time()
                        }
                        
                        return is_healthy
                    else:
                        self.service_health[service_type]['status'] = 'unhealthy'
                        return False
        except Exception as e:
            logger.warning(f"Health check failed for {service_type.value}: {e}")
            self.service_health[service_type]['status'] = 'error'
            return False

    async def process_ocr_request(self, image_path: str, method: str = "combined") -> Dict[str, Any]:
        """Process OCR request"""
        try:
            start_time = time.time()
            
            config = self.services[AIServiceType.OCR]
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=config.timeout)) as session:
                with open(image_path, 'rb') as f:
                    data = aiohttp.FormData()
                    data.add_field('file', f, filename=Path(image_path).name)
                    
                    if method == "combined":
                        endpoint = "/extract-text/combined"
                    elif method == "pytesseract":
                        endpoint = "/extract-text/pytesseract"
                    elif method == "easyocr":
                        endpoint = "/extract-text/easyocr"
                    else:
                        endpoint = "/extract-text/combined"
                    
                    async with session.post(f"{config.base_url}{endpoint}", data=data) as response:
                        result = await self._handle_response(response, AIServiceType.OCR, start_time)
                        return result
                        
        except Exception as e:
            logger.error(f"OCR request failed: {e}")
            return self._create_error_response(AIServiceType.OCR, str(e))

    async def process_ocr_text_puzzle(self, image_path: str, method: str = "combined") -> Dict[str, Any]:
        """Process OCR text puzzle creation request"""
        try:
            start_time = time.time()
            
            config = self.services[AIServiceType.OCR]
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=config.timeout)) as session:
                with open(image_path, 'rb') as f:
                    data = aiohttp.FormData()
                    data.add_field('file', f, filename=Path(image_path).name)
                    data.add_field('method', method)
                    
                    async with session.post(f"{config.base_url}/create-text-puzzle", data=data) as response:
                        result = await self._handle_response(response, AIServiceType.OCR, start_time)
                        return result
                        
        except Exception as e:
            logger.error(f"OCR text puzzle request failed: {e}")
            return self._create_error_response(AIServiceType.OCR, str(e))

    async def process_segmentation_request(self, image_path: str, confidence_threshold: float = 0.5) -> Dict[str, Any]:
        """Process image segmentation request"""
        try:
            start_time = time.time()
            
            config = self.services[AIServiceType.SEGMENTATION]
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=config.timeout)) as session:
                with open(image_path, 'rb') as f:
                    data = aiohttp.FormData()
                    data.add_field('file', f, filename=Path(image_path).name)
                    data.add_field('confidence_threshold', str(confidence_threshold))
                    
                    async with session.post(f"{config.base_url}/segment-objects", data=data) as response:
                        result = await self._handle_response(response, AIServiceType.SEGMENTATION, start_time)
                        return result
                        
        except Exception as e:
            logger.error(f"Segmentation request failed: {e}")
            return self._create_error_response(AIServiceType.SEGMENTATION, str(e))

    async def process_segmentation_puzzle_pieces(self, image_path: str, piece_count: int = 20) -> Dict[str, Any]:
        """Process segmentation-based puzzle piece creation"""
        try:
            start_time = time.time()
            
            config = self.services[AIServiceType.SEGMENTATION]
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=config.timeout)) as session:
                with open(image_path, 'rb') as f:
                    data = aiohttp.FormData()
                    data.add_field('file', f, filename=Path(image_path).name)
                    data.add_field('piece_count', str(piece_count))
                    
                    async with session.post(f"{config.base_url}/create-puzzle-pieces", data=data) as response:
                        result = await self._handle_response(response, AIServiceType.SEGMENTATION, start_time)
                        return result
                        
        except Exception as e:
            logger.error(f"Segmentation puzzle pieces request failed: {e}")
            return self._create_error_response(AIServiceType.SEGMENTATION, str(e))

    async def process_complexity_analysis(self, image_path: str) -> Dict[str, Any]:
        """Process image complexity analysis"""
        try:
            start_time = time.time()
            
            config = self.services[AIServiceType.SEGMENTATION]
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=config.timeout)) as session:
                with open(image_path, 'rb') as f:
                    data = aiohttp.FormData()
                    data.add_field('file', f, filename=Path(image_path).name)
                    
                    async with session.post(f"{config.base_url}/analyze-image-complexity", data=data) as response:
                        result = await self._handle_response(response, AIServiceType.SEGMENTATION, start_time)
                        return result
                        
        except Exception as e:
            logger.error(f"Complexity analysis request failed: {e}")
            return self._create_error_response(AIServiceType.SEGMENTATION, str(e))

    async def process_style_transfer_request(self, image_path: str, style_type: str, iterations: int = 300) -> Dict[str, Any]:
        """Process style transfer request"""
        try:
            start_time = time.time()
            
            config = self.services[AIServiceType.STYLE_TRANSFER]
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=config.timeout)) as session:
                with open(image_path, 'rb') as f:
                    data = aiohttp.FormData()
                    data.add_field('file', f, filename=Path(image_path).name)
                    data.add_field('style_type', style_type)
                    data.add_field('iterations', str(iterations))
                    
                    async with session.post(f"{config.base_url}/apply-style", data=data) as response:
                        result = await self._handle_response(response, AIServiceType.STYLE_TRANSFER, start_time)
                        return result
                        
        except Exception as e:
            logger.error(f"Style transfer request failed: {e}")
            return self._create_error_response(AIServiceType.STYLE_TRANSFER, str(e))

    async def process_batch_style_transfer(self, image_path: str, styles: List[str]) -> Dict[str, Any]:
        """Process batch style transfer request"""
        try:
            start_time = time.time()
            
            config = self.services[AIServiceType.STYLE_TRANSFER]
            styles_str = ','.join(styles)
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=config.timeout)) as session:
                with open(image_path, 'rb') as f:
                    data = aiohttp.FormData()
                    data.add_field('file', f, filename=Path(image_path).name)
                    data.add_field('styles', styles_str)
                    
                    async with session.post(f"{config.base_url}/batch-apply-styles", data=data) as response:
                        result = await self._handle_response(response, AIServiceType.STYLE_TRANSFER, start_time)
                        return result
                        
        except Exception as e:
            logger.error(f"Batch style transfer request failed: {e}")
            return self._create_error_response(AIServiceType.STYLE_TRANSFER, str(e))

    async def process_style_preview(self, image_path: str, style_type: str) -> Dict[str, Any]:
        """Process style transfer preview request"""
        try:
            start_time = time.time()
            
            config = self.services[AIServiceType.STYLE_TRANSFER]
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=config.timeout)) as session:
                with open(image_path, 'rb') as f:
                    data = aiohttp.FormData()
                    data.add_field('file', f, filename=Path(image_path).name)
                    data.add_field('style_type', style_type)
                    
                    async with session.post(f"{config.base_url}/preview-style", data=data) as response:
                        result = await self._handle_response(response, AIServiceType.STYLE_TRANSFER, start_time)
                        return result
                        
        except Exception as e:
            logger.error(f"Style preview request failed: {e}")
            return self._create_error_response(AIServiceType.STYLE_TRANSFER, str(e))

    async def process_parallel_ai_analysis(self, image_path: str, 
                                         include_ocr: bool = True,
                                         include_segmentation: bool = True,
                                         include_style_preview: bool = False,
                                         style_type: str = "watercolor") -> Dict[str, Any]:
        """Process multiple AI analyses in parallel"""
        try:
            tasks = []
            task_names = []
            
            if include_ocr:
                tasks.append(self.process_ocr_request(image_path))
                task_names.append('ocr')
            
            if include_segmentation:
                tasks.append(self.process_complexity_analysis(image_path))
                task_names.append('complexity')
                
                tasks.append(self.process_segmentation_request(image_path))
                task_names.append('segmentation')
            
            if include_style_preview:
                tasks.append(self.process_style_preview(image_path, style_type))
                task_names.append('style_preview')
            
            # Execute all tasks in parallel
            start_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            total_time = time.time() - start_time
            
            # Combine results
            combined_results = {
                'success': True,
                'processing_time': total_time,
                'results': {}
            }
            
            for task_name, result in zip(task_names, results):
                if isinstance(result, Exception):
                    combined_results['results'][task_name] = {
                        'success': False,
                        'error': str(result)
                    }
                    logger.warning(f"Parallel task {task_name} failed: {result}")
                else:
                    combined_results['results'][task_name] = result
            
            # Calculate success rate
            successful_tasks = sum(1 for result in results if not isinstance(result, Exception))
            combined_results['success_rate'] = successful_tasks / len(results) if results else 0
            
            return combined_results
            
        except Exception as e:
            logger.error(f"Parallel AI analysis failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'processing_time': 0
            }

    async def get_available_styles(self) -> Dict[str, Any]:
        """Get available styles from style transfer service"""
        try:
            config = self.services[AIServiceType.STYLE_TRANSFER]
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(f"{config.base_url}/available-styles") as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        return {'error': f'HTTP {response.status}'}
                        
        except Exception as e:
            logger.error(f"Failed to get available styles: {e}")
            return {'error': str(e)}

    async def get_supported_ocr_languages(self) -> Dict[str, Any]:
        """Get supported OCR languages"""
        try:
            config = self.services[AIServiceType.OCR]
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(f"{config.base_url}/supported-languages") as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        return {'error': f'HTTP {response.status}'}
                        
        except Exception as e:
            logger.error(f"Failed to get supported languages: {e}")
            return {'error': str(e)}

    async def get_segmentation_classes(self) -> Dict[str, Any]:
        """Get supported segmentation classes"""
        try:
            config = self.services[AIServiceType.SEGMENTATION]
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(f"{config.base_url}/supported-classes") as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        return {'error': f'HTTP {response.status}'}
                        
        except Exception as e:
            logger.error(f"Failed to get segmentation classes: {e}")
            return {'error': str(e)}

    async def _handle_response(self, response: aiohttp.ClientResponse, 
                             service_type: AIServiceType, start_time: float) -> Dict[str, Any]:
        """Handle AI service response"""
        processing_time = time.time() - start_time
        
        self.processing_stats['total_requests'] += 1
        
        if response.status == 200:
            self.processing_stats['successful_requests'] += 1
            result = await response.json()
            
            # Add processing metadata
            result['processing_metadata'] = {
                'service': service_type.value,
                'processing_time': processing_time,
                'timestamp': time.time(),
                'success': True
            }
            
            # Update average response time
            self._update_average_response_time(processing_time)
            
            return result
        else:
            self.processing_stats['failed_requests'] += 1
            error_text = await response.text()
            
            return {
                'success': False,
                'error': f'HTTP {response.status}: {error_text}',
                'processing_metadata': {
                    'service': service_type.value,
                    'processing_time': processing_time,
                    'timestamp': time.time(),
                    'success': False
                }
            }

    def _create_error_response(self, service_type: AIServiceType, error_message: str) -> Dict[str, Any]:
        """Create standardized error response"""
        self.processing_stats['total_requests'] += 1
        self.processing_stats['failed_requests'] += 1
        
        return {
            'success': False,
            'error': error_message,
            'processing_metadata': {
                'service': service_type.value,
                'processing_time': 0,
                'timestamp': time.time(),
                'success': False
            }
        }

    def _update_average_response_time(self, new_time: float):
        """Update average response time"""
        current_avg = self.processing_stats['average_response_time']
        successful_requests = self.processing_stats['successful_requests']
        
        if successful_requests == 1:
            self.processing_stats['average_response_time'] = new_time
        else:
            # Calculate running average
            self.processing_stats['average_response_time'] = (
                (current_avg * (successful_requests - 1) + new_time) / successful_requests
            )

    async def process_with_retry(self, request: AIProcessingRequest) -> Dict[str, Any]:
        """Process AI request with retry logic"""
        service_config = self.services[request.service_type]
        
        for attempt in range(service_config.max_retries):
            try:
                if request.service_type == AIServiceType.OCR:
                    if 'method' in request.parameters:
                        if request.parameters.get('create_puzzle', False):
                            result = await self.process_ocr_text_puzzle(
                                request.image_path, 
                                request.parameters.get('method', 'combined')
                            )
                        else:
                            result = await self.process_ocr_request(
                                request.image_path,
                                request.parameters.get('method', 'combined')
                            )
                    else:
                        result = await self.process_ocr_request(request.image_path)
                
                elif request.service_type == AIServiceType.SEGMENTATION:
                    if request.parameters.get('create_pieces', False):
                        result = await self.process_segmentation_puzzle_pieces(
                            request.image_path,
                            request.parameters.get('piece_count', 20)
                        )
                    elif request.parameters.get('analyze_complexity', False):
                        result = await self.process_complexity_analysis(request.image_path)
                    else:
                        result = await self.process_segmentation_request(
                            request.image_path,
                            request.parameters.get('confidence_threshold', 0.5)
                        )
                
                elif request.service_type == AIServiceType.STYLE_TRANSFER:
                    if request.parameters.get('batch_styles'):
                        result = await self.process_batch_style_transfer(
                            request.image_path,
                            request.parameters['batch_styles']
                        )
                    elif request.parameters.get('preview_only', False):
                        result = await self.process_style_preview(
                            request.image_path,
                            request.parameters.get('style_type', 'watercolor')
                        )
                    else:
                        result = await self.process_style_transfer_request(
                            request.image_path,
                            request.parameters.get('style_type', 'watercolor'),
                            request.parameters.get('iterations', 300)
                        )
                
                # If successful, return result
                if result.get('success', True):
                    return result
                
                # If failed but not the last attempt, retry
                if attempt < service_config.max_retries - 1:
                    logger.warning(f"Attempt {attempt + 1} failed for {request.service_type.value}, retrying...")
                    await asyncio.sleep(service_config.retry_delay * (attempt + 1))
                else:
                    return result
                    
            except Exception as e:
                if attempt < service_config.max_retries - 1:
                    logger.warning(f"Attempt {attempt + 1} failed for {request.service_type.value}: {e}, retrying...")
                    await asyncio.sleep(service_config.retry_delay * (attempt + 1))
                else:
                    return self._create_error_response(request.service_type, str(e))
        
        return self._create_error_response(request.service_type, "Max retries exceeded")

    def get_processing_statistics(self) -> Dict[str, Any]:
        """Get processing statistics"""
        success_rate = (
            self.processing_stats['successful_requests'] / self.processing_stats['total_requests']
            if self.processing_stats['total_requests'] > 0 else 0
        )
        
        return {
            'total_requests': self.processing_stats['total_requests'],
            'successful_requests': self.processing_stats['successful_requests'],
            'failed_requests': self.processing_stats['failed_requests'],
            'success_rate': success_rate,
            'average_response_time': self.processing_stats['average_response_time'],
            'service_health': self.service_health
        }

    def reset_statistics(self):
        """Reset processing statistics"""
        self.processing_stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'average_response_time': 0.0
        }

    async def optimize_ai_workflow(self, image_path: str, target_puzzle_type: str) -> Dict[str, Any]:
        """Optimize AI workflow based on target puzzle type"""
        workflow_plan = {
            'steps': [],
            'estimated_time': 0,
            'parallel_tasks': [],
            'sequential_tasks': []
        }
        
        if target_puzzle_type == 'text_puzzle':
            workflow_plan['steps'] = [
                {'service': 'ocr', 'priority': 1, 'required': True},
                {'service': 'complexity_analysis', 'priority': 2, 'required': False}
            ]
            workflow_plan['estimated_time'] = 15  # seconds
            
        elif target_puzzle_type == 'segmentation_based':
            workflow_plan['steps'] = [
                {'service': 'complexity_analysis', 'priority': 1, 'required': True},
                {'service': 'segmentation', 'priority': 1, 'required': True},
                {'service': 'ocr', 'priority': 3, 'required': False}
            ]
            workflow_plan['estimated_time'] = 25
            
        elif target_puzzle_type == 'style_enhanced':
            workflow_plan['steps'] = [
                {'service': 'style_preview', 'priority': 1, 'required': True},
                {'service': 'complexity_analysis', 'priority': 2, 'required': True}
            ]
            workflow_plan['estimated_time'] = 20
            
        elif target_puzzle_type == 'hybrid':
            workflow_plan['steps'] = [
                {'service': 'ocr', 'priority': 1, 'required': False},
                {'service': 'segmentation', 'priority': 1, 'required': True},
                {'service': 'complexity_analysis', 'priority': 1, 'required': True},
                {'service': 'style_preview', 'priority': 2, 'required': False}
            ]
            workflow_plan['estimated_time'] = 35
            
        else:  # classic
            workflow_plan['steps'] = [
                {'service': 'complexity_analysis', 'priority': 1, 'required': True}
            ]
            workflow_plan['estimated_time'] = 10
        
        # Separate parallel and sequential tasks
        high_priority = [step for step in workflow_plan['steps'] if step['priority'] == 1]
        low_priority = [step for step in workflow_plan['steps'] if step['priority'] > 1]
        
        workflow_plan['parallel_tasks'] = high_priority
        workflow_plan['sequential_tasks'] = low_priority
        
        return workflow_plan

    async def execute_optimized_workflow(self, image_path: str, workflow_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Execute optimized AI workflow"""
        results = {
            'workflow_results': {},
            'execution_time': 0,
            'success': True
        }
        
        start_time = time.time()
        
        try:
            # Execute parallel tasks first
            if workflow_plan['parallel_tasks']:
                parallel_tasks = []
                task_names = []
                
                for task in workflow_plan['parallel_tasks']:
                    service = task['service']
                    
                    if service == 'ocr':
                        parallel_tasks.append(self.process_ocr_request(image_path))
                        task_names.append('ocr')
                    elif service == 'segmentation':
                        parallel_tasks.append(self.process_segmentation_request(image_path))
                        task_names.append('segmentation')
                    elif service == 'complexity_analysis':
                        parallel_tasks.append(self.process_complexity_analysis(image_path))
                        task_names.append('complexity_analysis')
                    elif service == 'style_preview':
                        parallel_tasks.append(self.process_style_preview(image_path, 'watercolor'))
                        task_names.append('style_preview')
                
                parallel_results = await asyncio.gather(*parallel_tasks, return_exceptions=True)
                
                for task_name, result in zip(task_names, parallel_results):
                    if isinstance(result, Exception):
                        results['workflow_results'][task_name] = {
                            'success': False,
                            'error': str(result)
                        }
                    else:
                        results['workflow_results'][task_name] = result
            
            # Execute sequential tasks
            for task in workflow_plan['sequential_tasks']:
                service = task['service']
                
                try:
                    if service == 'ocr':
                        result = await self.process_ocr_request(image_path)
                    elif service == 'segmentation':
                        result = await self.process_segmentation_request(image_path)
                    elif service == 'complexity_analysis':
                        result = await self.process_complexity_analysis(image_path)
                    elif service == 'style_preview':
                        result = await self.process_style_preview(image_path, 'watercolor')
                    else:
                        continue
                    
                    results['workflow_results'][service] = result
                    
                except Exception as e:
                    results['workflow_results'][service] = {
                        'success': False,
                        'error': str(e)
                    }
                    
                    if task['required']:
                        results['success'] = False
                        break
            
            results['execution_time'] = time.time() - start_time
            
        except Exception as e:
            results['success'] = False
            results['error'] = str(e)
            results['execution_time'] = time.time() - start_time
        
        return results