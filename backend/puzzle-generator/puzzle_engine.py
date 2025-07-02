import numpy as np
import cv2
from PIL import Image, ImageDraw
import json
import logging
import asyncio
import aiohttp
from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path
import tempfile
import os
from dataclasses import dataclass
from enum import Enum
import base64
import io

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PuzzleType(Enum):
    CLASSIC = "classic"
    SEGMENTATION_BASED = "segmentation_based"
    TEXT_PUZZLE = "text_puzzle"
    STYLE_ENHANCED = "style_enhanced"
    HYBRID = "hybrid"

class DifficultyLevel(Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXPERT = "expert"

@dataclass
class PuzzleConfig:
    piece_count: int = 20
    difficulty: DifficultyLevel = DifficultyLevel.MEDIUM
    puzzle_type: PuzzleType = PuzzleType.CLASSIC
    allow_rotation: bool = True
    style_type: Optional[str] = None
    use_ai_enhancement: bool = True
    confidence_threshold: float = 0.5

class IntelligentPuzzleEngine:
    def __init__(self):
        """Initialize the intelligent puzzle generation engine"""
        self.ai_services = {
            'ocr': 'http://localhost:8003',
            'segmentation': 'http://localhost:8006',
            'style_transfer': 'http://localhost:8007'
        }

        # Puzzle piece shapes and patterns
        self.piece_shapes = ['classic', 'organic', 'geometric', 'irregular']

        # Difficulty parameters
        self.difficulty_params = {
            DifficultyLevel.EASY: {
                'piece_count_range': (6, 15),
                'edge_complexity': 0.3,
                'color_similarity_threshold': 0.7
            },
            DifficultyLevel.MEDIUM: {
                'piece_count_range': (16, 35),
                'edge_complexity': 0.5,
                'color_similarity_threshold': 0.5
            },
            DifficultyLevel.HARD: {
                'piece_count_range': (36, 80),
                'edge_complexity': 0.7,
                'color_similarity_threshold': 0.3
            },
            DifficultyLevel.EXPERT: {
                'piece_count_range': (81, 200),
                'edge_complexity': 0.9,
                'color_similarity_threshold': 0.1
            }
        }

        logger.info("Intelligent Puzzle Engine initialized")

    async def generate_intelligent_puzzle(self, image_path: str, config: PuzzleConfig) -> Dict[str, Any]:
        """Generate an intelligent puzzle using AI services"""
        try:
            logger.info(f"Starting intelligent puzzle generation for {image_path}")

            # Step 1: Analyze image complexity
            complexity_analysis = await self._analyze_image_complexity(image_path)

            # Step 2: Adjust configuration based on analysis
            optimized_config = self._optimize_config(config, complexity_analysis)

            # Step 3: Generate puzzle based on type
            if optimized_config.puzzle_type == PuzzleType.TEXT_PUZZLE:
                puzzle_data = await self._generate_text_puzzle(image_path, optimized_config)
            elif optimized_config.puzzle_type == PuzzleType.SEGMENTATION_BASED:
                puzzle_data = await self._generate_segmentation_puzzle(image_path, optimized_config)
            elif optimized_config.puzzle_type == PuzzleType.STYLE_ENHANCED:
                puzzle_data = await self._generate_style_enhanced_puzzle(image_path, optimized_config)
            elif optimized_config.puzzle_type == PuzzleType.HYBRID:
                puzzle_data = await self._generate_hybrid_puzzle(image_path, optimized_config)
            else:
                puzzle_data = await self._generate_classic_puzzle(image_path, optimized_config)

            # Step 4: Add metadata and hints
            puzzle_data = self._add_puzzle_metadata(puzzle_data, complexity_analysis, optimized_config)

            # Step 5: Generate hint system
            puzzle_data['hints'] = self._generate_hint_system(puzzle_data, optimized_config)

            logger.info(f"Puzzle generation completed: {puzzle_data['total_pieces']} pieces")
            return puzzle_data

        except Exception as e:
            logger.error(f"Puzzle generation failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'puzzle_type': config.puzzle_type.value
            }

    async def _analyze_image_complexity(self, image_path: str) -> Dict[str, Any]:
        """Analyze image complexity using segmentation service"""
        try:
            async with aiohttp.ClientSession() as session:
                with open(image_path, 'rb') as f:
                    data = aiohttp.FormData()
                    data.add_field('file', f, filename=os.path.basename(image_path))

                    async with session.post(
                        f"{self.ai_services['segmentation']}/analyze-image-complexity",
                        data=data
                    ) as response:
                        if response.status == 200:
                            return await response.json()
                        else:
                            logger.warning(f"Complexity analysis failed: {response.status}")
                            return self._default_complexity_analysis()
        except Exception as e:
            logger.error(f"Error analyzing image complexity: {e}")
            return self._default_complexity_analysis()

    def _default_complexity_analysis(self) -> Dict[str, Any]:
        """Return default complexity analysis"""
        return {
            'complexity_level': 'medium',
            'objects_detected': 3,
            'unique_classes': 2,
            'recommended_piece_count': 25
        }

    def _optimize_config(self, config: PuzzleConfig, complexity: Dict[str, Any]) -> PuzzleConfig:
        """Optimize puzzle configuration based on image complexity"""
        optimized_config = PuzzleConfig(
            piece_count=config.piece_count,
            difficulty=config.difficulty,
            puzzle_type=config.puzzle_type,
            allow_rotation=config.allow_rotation,
            style_type=config.style_type,
            use_ai_enhancement=config.use_ai_enhancement,
            confidence_threshold=config.confidence_threshold
        )

        # Adjust piece count based on complexity
        if config.use_ai_enhancement:
            recommended_count = complexity.get('recommended_piece_count', config.piece_count)
            complexity_level = complexity.get('complexity_level', 'medium')

            if complexity_level == 'high':
                optimized_config.piece_count = max(config.piece_count, recommended_count)
                if config.difficulty == DifficultyLevel.EASY:
                    optimized_config.difficulty = DifficultyLevel.MEDIUM
            elif complexity_level == 'low':
                optimized_config.piece_count = min(config.piece_count, recommended_count)

        # Auto-select puzzle type based on content
        objects_detected = complexity.get('objects_detected', 0)
        if objects_detected >= 5 and config.puzzle_type == PuzzleType.CLASSIC:
            optimized_config.puzzle_type = PuzzleType.SEGMENTATION_BASED

        return optimized_config

    async def _generate_text_puzzle(self, image_path: str, config: PuzzleConfig) -> Dict[str, Any]:
        """Generate text-based puzzle using OCR service"""
        try:
            async with aiohttp.ClientSession() as session:
                with open(image_path, 'rb') as f:
                    data = aiohttp.FormData()
                    data.add_field('file', f, filename=os.path.basename(image_path))
                    data.add_field('method', 'combined')

                    async with session.post(
                        f"{self.ai_services['ocr']}/create-text-puzzle",
                        data=data
                    ) as response:
                        if response.status == 200:
                            ocr_result = await response.json()

                            # Enhance text puzzle with visual elements
                            enhanced_puzzle = self._enhance_text_puzzle(ocr_result, image_path, config)
                            return enhanced_puzzle
                        else:
                            logger.error(f"OCR service failed: {response.status}")
                            return await self._generate_classic_puzzle(image_path, config)
        except Exception as e:
            logger.error(f"Text puzzle generation failed: {e}")
            return await self._generate_classic_puzzle(image_path, config)

    async def _generate_segmentation_puzzle(self, image_path: str, config: PuzzleConfig) -> Dict[str, Any]:
        """Generate segmentation-based puzzle"""
        try:
            async with aiohttp.ClientSession() as session:
                with open(image_path, 'rb') as f:
                    data = aiohttp.FormData()
                    data.add_field('file', f, filename=os.path.basename(image_path))
                    data.add_field('piece_count', str(config.piece_count))

                    async with session.post(
                        f"{self.ai_services['segmentation']}/create-puzzle-pieces",
                        data=data
                    ) as response:
                        if response.status == 200:
                            seg_result = await response.json()

                            # Enhance segmentation puzzle
                            enhanced_puzzle = self._enhance_segmentation_puzzle(seg_result, config)
                            return enhanced_puzzle
                        else:
                            logger.error(f"Segmentation service failed: {response.status}")
                            return await self._generate_classic_puzzle(image_path, config)
        except Exception as e:
            logger.error(f"Segmentation puzzle generation failed: {e}")
            return await self._generate_classic_puzzle(image_path, config)

    async def _generate_style_enhanced_puzzle(self, image_path: str, config: PuzzleConfig) -> Dict[str, Any]:
        """Generate style-enhanced puzzle"""
        try:
            # First apply style transfer
            styled_image_path = await self._apply_style_transfer(image_path, config.style_type or 'watercolor')

            if styled_image_path:
                # Generate puzzle from styled image
                return await self._generate_classic_puzzle(styled_image_path, config)
            else:
                # Fallback to original image
                return await self._generate_classic_puzzle(image_path, config)

        except Exception as e:
            logger.error(f"Style-enhanced puzzle generation failed: {e}")
            return await self._generate_classic_puzzle(image_path, config)

    async def _generate_hybrid_puzzle(self, image_path: str, config: PuzzleConfig) -> Dict[str, Any]:
        """Generate hybrid puzzle combining multiple AI techniques"""
        try:
            # Combine segmentation and style transfer
            tasks = []

            # Task 1: Segmentation analysis
            tasks.append(self._analyze_segmentation(image_path, config))

            # Task 2: OCR analysis
            tasks.append(self._analyze_ocr(image_path))

            # Task 3: Style enhancement (if specified)
            if config.style_type:
                tasks.append(self._apply_style_transfer(image_path, config.style_type))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Combine results intelligently
            hybrid_puzzle = self._combine_ai_results(results, image_path, config)
            return hybrid_puzzle

        except Exception as e:
            logger.error(f"Hybrid puzzle generation failed: {e}")
            return await self._generate_classic_puzzle(image_path, config)

    async def _generate_classic_puzzle(self, image_path: str, config: PuzzleConfig) -> Dict[str, Any]:
        """Generate classic grid-based puzzle"""
        try:
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError("Could not read image")

            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            height, width = image_rgb.shape[:2]

            # Calculate optimal grid
            grid_info = self._calculate_optimal_grid(config.piece_count, width, height, config.difficulty)

            pieces = []
            piece_id = 0

            for row in range(grid_info['rows']):
                for col in range(grid_info['cols']):
                    piece = self._create_classic_piece(
                        image_rgb, row, col, grid_info, piece_id, config
                    )
                    pieces.append(piece)
                    piece_id += 1

            return {
                'success': True,
                'puzzle_type': 'classic_intelligent',
                'total_pieces': len(pieces),
                'pieces': pieces,
                'grid_info': grid_info,
                'image_info': {
                    'width': width,
                    'height': height,
                    'channels': 3
                }
            }

        except Exception as e:
            logger.error(f"Classic puzzle generation failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'puzzle_type': 'classic'
            }

    def _calculate_optimal_grid(self, piece_count: int, width: int, height: int, difficulty: DifficultyLevel) -> Dict[str, Any]:
        """Calculate optimal grid layout"""
        aspect_ratio = width / height

        # Adjust for difficulty
        difficulty_factor = {
            DifficultyLevel.EASY: 0.8,
            DifficultyLevel.MEDIUM: 1.0,
            DifficultyLevel.HARD: 1.2,
            DifficultyLevel.EXPERT: 1.5
        }[difficulty]

        adjusted_count = int(piece_count * difficulty_factor)

        # Calculate grid dimensions
        cols = int(np.sqrt(adjusted_count * aspect_ratio))
        rows = int(adjusted_count / cols)

        # Ensure minimum piece size
        min_piece_size = 50
        max_cols = width // min_piece_size
        max_rows = height // min_piece_size

        cols = min(cols, max_cols)
        rows = min(rows, max_rows)

        piece_width = width // cols
        piece_height = height // rows

        return {
            'rows': rows,
            'cols': cols,
            'piece_width': piece_width,
            'piece_height': piece_height,
            'total_pieces': rows * cols
        }

    def _create_classic_piece(self, image: np.ndarray, row: int, col: int, 
                            grid_info: Dict, piece_id: int, config: PuzzleConfig) -> Dict[str, Any]:
        """Create a classic puzzle piece with intelligent enhancements"""
        x1 = col * grid_info['piece_width']
        y1 = row * grid_info['piece_height']
        x2 = min(x1 + grid_info['piece_width'], image.shape[1])
        y2 = min(y1 + grid_info['piece_height'], image.shape[0])

        # Extract piece image
        piece_image = image[y1:y2, x1:x2]

        # Generate actual image data for the piece
        image_data = self._generate_piece_image_data(piece_image, shape_mask if 'shape_mask' in locals() else None)

        # Calculate piece characteristics
        piece_complexity = self._calculate_piece_complexity(piece_image)
        edge_info = self._generate_edge_info(row, col, grid_info, config)

        # Generate piece shape based on difficulty
        shape_mask = self._generate_piece_shape(
            grid_info['piece_width'], 
            grid_info['piece_height'], 
            config.difficulty,
            edge_info
        )

        # Regenerate image data with proper shape mask
        image_data = self._generate_piece_image_data(piece_image, shape_mask)

        return {
            'id': f"piece_{piece_id}",
            'type': 'classic_intelligent',
            'grid_position': {'row': row, 'col': col},
            'bbox': [x1, y1, x2, y2],
            'center': [(x1 + x2) // 2, (y1 + y2) // 2],
            'shape_mask': shape_mask.tolist() if shape_mask is not None else None,
            'edges': edge_info,
            'complexity': piece_complexity,
            'difficulty': config.difficulty.value,
            'rotation_allowed': config.allow_rotation,
            'dominant_colors': self._extract_dominant_colors(piece_image),
            'texture_features': self._extract_texture_features(piece_image),
            'imageData': image_data,  # 실제 이미지 데이터 추가
            'width': piece_image.shape[1],
            'height': piece_image.shape[0],
            'x': x1,
            'y': y1,
            'correctPosition': {'x': x1, 'y': y1},
            'currentPosition': {'x': x1, 'y': y1},
            'isPlaced': False,
            'isSelected': False,
            'rotation': 0
        }

    def _calculate_piece_complexity(self, piece_image: np.ndarray) -> Dict[str, float]:
        """Calculate complexity metrics for a puzzle piece"""
        # Color variance
        color_variance = np.var(piece_image, axis=(0, 1)).mean()

        # Edge density
        gray = cv2.cvtColor(piece_image, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / edges.size

        # Texture complexity using Laplacian variance
        texture_complexity = cv2.Laplacian(gray, cv2.CV_64F).var()

        return {
            'color_variance': float(color_variance),
            'edge_density': float(edge_density),
            'texture_complexity': float(texture_complexity),
            'overall_complexity': float((color_variance + edge_density * 100 + texture_complexity) / 3)
        }

    def _generate_edge_info(self, row: int, col: int, grid_info: Dict, config: PuzzleConfig) -> Dict[str, Any]:
        """Generate edge information for puzzle piece connections"""
        edges = {
            'top': 'flat' if row == 0 else 'tab' if np.random.random() > 0.5 else 'blank',
            'right': 'flat' if col == grid_info['cols'] - 1 else 'tab' if np.random.random() > 0.5 else 'blank',
            'bottom': 'flat' if row == grid_info['rows'] - 1 else 'tab' if np.random.random() > 0.5 else 'blank',
            'left': 'flat' if col == 0 else 'tab' if np.random.random() > 0.5 else 'blank'
        }

        # Ensure complementary edges for adjacent pieces
        # This would be enhanced with a global edge management system

        return edges

    def _generate_piece_shape(self, width: int, height: int, difficulty: DifficultyLevel, 
                            edge_info: Dict[str, str]) -> Optional[np.ndarray]:
        """Generate piece shape mask based on difficulty and edge information"""
        if difficulty == DifficultyLevel.EASY:
            # Simple rectangular pieces
            return None

        # Create base mask
        mask = np.ones((height, width), dtype=np.uint8) * 255

        # Add tabs and blanks based on edge info
        tab_size = min(width, height) // 6

        for edge, edge_type in edge_info.items():
            if edge_type == 'tab':
                mask = self._add_tab_to_mask(mask, edge, tab_size)
            elif edge_type == 'blank':
                mask = self._add_blank_to_mask(mask, edge, tab_size)

        return mask

    def _add_tab_to_mask(self, mask: np.ndarray, edge: str, tab_size: int) -> np.ndarray:
        """Add tab to piece mask"""
        h, w = mask.shape
        center_x, center_y = w // 2, h // 2

        if edge == 'top':
            cv2.circle(mask, (center_x, 0), tab_size, 255, -1)
        elif edge == 'right':
            cv2.circle(mask, (w - 1, center_y), tab_size, 255, -1)
        elif edge == 'bottom':
            cv2.circle(mask, (center_x, h - 1), tab_size, 255, -1)
        elif edge == 'left':
            cv2.circle(mask, (0, center_y), tab_size, 255, -1)

        return mask

    def _add_blank_to_mask(self, mask: np.ndarray, edge: str, tab_size: int) -> np.ndarray:
        """Add blank (indentation) to piece mask"""
        h, w = mask.shape
        center_x, center_y = w // 2, h // 2

        if edge == 'top':
            cv2.circle(mask, (center_x, 0), tab_size, 0, -1)
        elif edge == 'right':
            cv2.circle(mask, (w - 1, center_y), tab_size, 0, -1)
        elif edge == 'bottom':
            cv2.circle(mask, (center_x, h - 1), tab_size, 0, -1)
        elif edge == 'left':
            cv2.circle(mask, (0, center_y), tab_size, 0, -1)

        return mask

    def _generate_piece_image_data(self, piece_image: np.ndarray, shape_mask: Optional[np.ndarray] = None) -> str:
        """Generate Base64 encoded image data for a puzzle piece"""
        try:
            # Convert numpy array to PIL Image
            pil_image = Image.fromarray(piece_image)

            # Apply shape mask if provided
            if shape_mask is not None:
                # Resize mask to match piece image dimensions
                mask_resized = cv2.resize(shape_mask, (piece_image.shape[1], piece_image.shape[0]))

                # Convert mask to PIL Image
                mask_pil = Image.fromarray(mask_resized, mode='L')

                # Apply mask to create transparency
                pil_image = pil_image.convert('RGBA')
                pil_image.putalpha(mask_pil)
            else:
                # Convert to RGBA for consistency
                pil_image = pil_image.convert('RGBA')

            # Save to bytes buffer
            buffer = io.BytesIO()
            pil_image.save(buffer, format='PNG')
            buffer.seek(0)

            # Encode to Base64
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

            # Return as Data URL
            return f"data:image/png;base64,{image_base64}"

        except Exception as e:
            logger.error(f"Failed to generate piece image data: {e}")
            # Return empty data URL as fallback
            return "data:image/png;base64,"

    def _extract_dominant_colors(self, image: np.ndarray, k: int = 3) -> List[List[int]]:
        """Extract dominant colors from piece image"""
        data = image.reshape((-1, 3))
        data = np.float32(data)

        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
        _, labels, centers = cv2.kmeans(data, k, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)

        centers = np.uint8(centers)
        return centers.tolist()

    def _extract_texture_features(self, image: np.ndarray) -> Dict[str, float]:
        """Extract texture features from piece image"""
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)

        # Calculate texture features
        contrast = gray.std()
        homogeneity = 1.0 / (1.0 + gray.var())

        # Local Binary Pattern approximation
        lbp_var = cv2.Laplacian(gray, cv2.CV_64F).var()

        return {
            'contrast': float(contrast),
            'homogeneity': float(homogeneity),
            'lbp_variance': float(lbp_var)
        }

    async def _apply_style_transfer(self, image_path: str, style_type: str) -> Optional[str]:
        """Apply style transfer to image"""
        try:
            async with aiohttp.ClientSession() as session:
                with open(image_path, 'rb') as f:
                    data = aiohttp.FormData()
                    data.add_field('file', f, filename=os.path.basename(image_path))
                    data.add_field('style_type', style_type)
                    data.add_field('iterations', '200')  # Faster processing

                    async with session.post(
                        f"{self.ai_services['style_transfer']}/apply-style",
                        data=data
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            if result.get('success'):
                                return result.get('output_path')
            return None
        except Exception as e:
            logger.error(f"Style transfer failed: {e}")
            return None

    async def _analyze_segmentation(self, image_path: str, config: PuzzleConfig) -> Dict[str, Any]:
        """Analyze image segmentation"""
        try:
            async with aiohttp.ClientSession() as session:
                with open(image_path, 'rb') as f:
                    data = aiohttp.FormData()
                    data.add_field('file', f, filename=os.path.basename(image_path))
                    data.add_field('confidence_threshold', str(config.confidence_threshold))

                    async with session.post(
                        f"{self.ai_services['segmentation']}/segment-objects",
                        data=data
                    ) as response:
                        if response.status == 200:
                            return await response.json()
            return {}
        except Exception as e:
            logger.error(f"Segmentation analysis failed: {e}")
            return {}

    async def _analyze_ocr(self, image_path: str) -> Dict[str, Any]:
        """Analyze OCR content"""
        try:
            async with aiohttp.ClientSession() as session:
                with open(image_path, 'rb') as f:
                    data = aiohttp.FormData()
                    data.add_field('file', f, filename=os.path.basename(image_path))

                    async with session.post(
                        f"{self.ai_services['ocr']}/extract-text/combined",
                        data=data
                    ) as response:
                        if response.status == 200:
                            return await response.json()
            return {}
        except Exception as e:
            logger.error(f"OCR analysis failed: {e}")
            return {}

    def _enhance_text_puzzle(self, ocr_result: Dict, image_path: str, config: PuzzleConfig) -> Dict[str, Any]:
        """Enhance text puzzle with visual elements"""
        # Combine text puzzle with visual puzzle pieces
        enhanced_puzzle = ocr_result.copy()
        enhanced_puzzle['puzzle_type'] = 'text_enhanced'
        enhanced_puzzle['visual_elements'] = True

        # Add visual piece information
        if ocr_result.get('words'):
            enhanced_puzzle['text_pieces'] = len(ocr_result['words'])
            enhanced_puzzle['total_pieces'] = enhanced_puzzle['text_pieces'] + config.piece_count // 2

        return enhanced_puzzle

    def _enhance_segmentation_puzzle(self, seg_result: Dict, config: PuzzleConfig) -> Dict[str, Any]:
        """Enhance segmentation puzzle"""
        enhanced_puzzle = seg_result.copy()
        enhanced_puzzle['puzzle_type'] = 'segmentation_enhanced'

        # Add intelligent piece grouping
        if 'pieces' in seg_result:
            enhanced_puzzle['piece_groups'] = self._group_pieces_by_similarity(seg_result['pieces'])

        return enhanced_puzzle

    def _combine_ai_results(self, results: List, image_path: str, config: PuzzleConfig) -> Dict[str, Any]:
        """Combine multiple AI analysis results"""
        combined_puzzle = {
            'success': True,
            'puzzle_type': 'hybrid_intelligent',
            'ai_enhancements': []
        }

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"AI task {i} failed: {result}")
                continue

            if isinstance(result, dict) and result:
                combined_puzzle['ai_enhancements'].append({
                    'service': ['segmentation', 'ocr', 'style_transfer'][i],
                    'data': result
                })

        # Generate hybrid pieces based on combined analysis
        combined_puzzle['pieces'] = self._generate_hybrid_pieces(results, config)
        combined_puzzle['total_pieces'] = len(combined_puzzle['pieces'])

        return combined_puzzle

    def _generate_hybrid_pieces(self, ai_results: List, config: PuzzleConfig) -> List[Dict[str, Any]]:
        """Generate puzzle pieces using hybrid AI approach"""
        pieces = []

        # This would implement sophisticated piece generation
        # combining segmentation, OCR, and style transfer results

        # For now, return a basic implementation
        for i in range(config.piece_count):
            pieces.append({
                'id': f"hybrid_{i}",
                'type': 'hybrid',
                'ai_enhanced': True,
                'complexity': 'medium'
            })

        return pieces

    def _group_pieces_by_similarity(self, pieces: List[Dict]) -> List[List[int]]:
        """Group puzzle pieces by visual similarity"""
        # Implement piece grouping algorithm
        groups = []

        # Simple grouping by piece type for now
        type_groups = {}
        for i, piece in enumerate(pieces):
            piece_type = piece.get('type', 'unknown')
            if piece_type not in type_groups:
                type_groups[piece_type] = []
            type_groups[piece_type].append(i)

        return list(type_groups.values())

    def _add_puzzle_metadata(self, puzzle_data: Dict, complexity: Dict, config: PuzzleConfig) -> Dict[str, Any]:
        """Add comprehensive metadata to puzzle"""
        puzzle_data['metadata'] = {
            'generation_timestamp': np.datetime64('now').astype(str),
            'ai_enhanced': config.use_ai_enhancement,
            'difficulty_level': config.difficulty.value,
            'estimated_solve_time': self._estimate_solve_time(puzzle_data, config),
            'complexity_analysis': complexity,
            'recommended_strategies': self._generate_solving_strategies(puzzle_data, config),
            'accessibility_features': self._generate_accessibility_features(config)
        }

        return puzzle_data

    def _generate_hint_system(self, puzzle_data: Dict, config: PuzzleConfig) -> Dict[str, Any]:
        """Generate intelligent hint system"""
        hints = {
            'corner_pieces': [],
            'edge_pieces': [],
            'color_groups': [],
            'pattern_hints': [],
            'progressive_hints': []
        }

        # Identify corner and edge pieces
        if 'pieces' in puzzle_data:
            for piece in puzzle_data['pieces']:
                if 'grid_position' in piece:
                    row, col = piece['grid_position']['row'], piece['grid_position']['col']
                    grid_info = puzzle_data.get('grid_info', {})

                    if self._is_corner_piece(row, col, grid_info):
                        hints['corner_pieces'].append(piece['id'])
                    elif self._is_edge_piece(row, col, grid_info):
                        hints['edge_pieces'].append(piece['id'])

        # Generate progressive hints
        hints['progressive_hints'] = [
            "Start with corner pieces - they have two flat edges",
            "Build the border first using edge pieces",
            "Group pieces by dominant colors",
            "Look for distinctive patterns or textures",
            "Use the piece shape to guide connections"
        ]

        return hints

    def _is_corner_piece(self, row: int, col: int, grid_info: Dict) -> bool:
        """Check if piece is a corner piece"""
        rows, cols = grid_info.get('rows', 0), grid_info.get('cols', 0)
        return (row == 0 or row == rows - 1) and (col == 0 or col == cols - 1)

    def _is_edge_piece(self, row: int, col: int, grid_info: Dict) -> bool:
        """Check if piece is an edge piece"""
        rows, cols = grid_info.get('rows', 0), grid_info.get('cols', 0)
        return (row == 0 or row == rows - 1 or col == 0 or col == cols - 1) and not self._is_corner_piece(row, col, grid_info)

    def _estimate_solve_time(self, puzzle_data: Dict, config: PuzzleConfig) -> Dict[str, int]:
        """Estimate puzzle solving time"""
        base_time_per_piece = {
            DifficultyLevel.EASY: 30,      # seconds
            DifficultyLevel.MEDIUM: 60,
            DifficultyLevel.HARD: 120,
            DifficultyLevel.EXPERT: 300
        }

        piece_count = puzzle_data.get('total_pieces', config.piece_count)
        base_time = base_time_per_piece[config.difficulty] * piece_count

        # Adjust for puzzle type
        type_multiplier = {
            'classic': 1.0,
            'segmentation_based': 0.8,
            'text_puzzle': 1.2,
            'style_enhanced': 1.1,
            'hybrid': 1.3
        }

        puzzle_type = puzzle_data.get('puzzle_type', 'classic')
        adjusted_time = int(base_time * type_multiplier.get(puzzle_type, 1.0))

        return {
            'estimated_minutes': adjusted_time // 60,
            'estimated_seconds': adjusted_time % 60,
            'difficulty_factor': type_multiplier.get(puzzle_type, 1.0)
        }

    def _generate_solving_strategies(self, puzzle_data: Dict, config: PuzzleConfig) -> List[str]:
        """Generate recommended solving strategies"""
        strategies = []

        puzzle_type = puzzle_data.get('puzzle_type', 'classic')

        if puzzle_type == 'text_puzzle':
            strategies.extend([
                "Read the text content to understand the image context",
                "Use text positioning as guides for piece placement",
                "Group pieces by text vs. non-text areas"
            ])
        elif puzzle_type == 'segmentation_based':
            strategies.extend([
                "Identify distinct objects in the image",
                "Complete one object at a time",
                "Use object boundaries as natural groupings"
            ])
        elif puzzle_type == 'style_enhanced':
            strategies.extend([
                "Focus on the artistic style patterns",
                "Use color gradients and brush strokes as guides",
                "Look for style-specific features"
            ])

        # Add general strategies
        strategies.extend([
            "Start with high-contrast areas",
            "Use piece complexity as a difficulty indicator",
            "Group similar textures and patterns"
        ])

        return strategies

    def _generate_accessibility_features(self, config: PuzzleConfig) -> Dict[str, Any]:
        """Generate accessibility features"""
        return {
            'high_contrast_mode': True,
            'piece_numbering': config.difficulty in [DifficultyLevel.EASY, DifficultyLevel.MEDIUM],
            'color_blind_support': True,
            'large_piece_mode': config.difficulty == DifficultyLevel.EASY,
            'audio_hints': True,
            'magnification_support': True
        }

    async def get_puzzle_statistics(self, puzzle_id: str) -> Dict[str, Any]:
        """Get statistics for a generated puzzle"""
        # This would typically query a database
        # For now, return sample statistics
        return {
            'puzzle_id': puzzle_id,
            'generation_time': '2.5 seconds',
            'ai_services_used': ['segmentation', 'ocr'],
            'optimization_applied': True,
            'estimated_difficulty': 'medium',
            'player_feedback': {
                'average_rating': 4.2,
                'completion_rate': 0.78,
                'average_solve_time': '45 minutes'
            }
        }

    def validate_puzzle_config(self, config: PuzzleConfig) -> Tuple[bool, List[str]]:
        """Validate puzzle configuration"""
        errors = []

        if config.piece_count < 4:
            errors.append("Piece count must be at least 4")
        elif config.piece_count > 1000:
            errors.append("Piece count cannot exceed 1000")

        if config.confidence_threshold < 0.1 or config.confidence_threshold > 1.0:
            errors.append("Confidence threshold must be between 0.1 and 1.0")

        if config.style_type and config.puzzle_type != PuzzleType.STYLE_ENHANCED:
            errors.append("Style type can only be used with STYLE_ENHANCED puzzle type")

        return len(errors) == 0, errors
