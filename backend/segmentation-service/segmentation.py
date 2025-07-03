import torch
import torchvision.transforms as T
from torchvision.models.detection import maskrcnn_resnet50_fpn, MaskRCNN_ResNet50_FPN_Weights
import cv2
import numpy as np
from PIL import Image
import logging
from typing import Dict, List, Any, Tuple
import os
import json
import base64
import io

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ImageSegmentation:
    def __init__(self):
        """Initialize image segmentation with Mask R-CNN model"""
        try:
            # Load pre-trained Mask R-CNN model
            weights = MaskRCNN_ResNet50_FPN_Weights.DEFAULT
            self.model = maskrcnn_resnet50_fpn(weights=weights)
            self.model.eval()

            # Set device
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.model.to(self.device)

            # Image transformation
            self.transform = T.Compose([T.ToTensor()])

            # COCO class names
            self.class_names = weights.meta["categories"]

            logger.info(f"Image segmentation initialized on device: {self.device}")

        except Exception as e:
            logger.error(f"Failed to initialize segmentation model: {e}")
            raise

    def segment_objects(self, image_path: str, confidence_threshold: float = 0.5) -> Dict[str, Any]:
        """Segment objects in the image using Mask R-CNN"""
        try:
            # Load and preprocess image
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError("Could not read image")

            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            original_height, original_width = image_rgb.shape[:2]

            # Convert to tensor
            image_tensor = self.transform(image_rgb).unsqueeze(0).to(self.device)

            # Perform inference
            with torch.no_grad():
                predictions = self.model(image_tensor)

            prediction = predictions[0]

            # Filter predictions by confidence
            scores = prediction['scores'].cpu().numpy()
            high_conf_indices = scores > confidence_threshold

            if not np.any(high_conf_indices):
                return {
                    'objects_found': 0,
                    'masks': [],
                    'labels': [],
                    'scores': [],
                    'boxes': [],
                    'class_names': [],
                    'segmented_objects': [],
                    'image_info': {
                        'width': original_width,
                        'height': original_height,
                        'channels': 3
                    }
                }

            # Extract high-confidence predictions
            masks = prediction['masks'][high_conf_indices].cpu().numpy()
            labels = prediction['labels'][high_conf_indices].cpu().numpy()
            scores = scores[high_conf_indices]
            boxes = prediction['boxes'][high_conf_indices].cpu().numpy()

            # Get class names
            class_names = [self.class_names[label] for label in labels]

            # Extract segmented objects
            segmented_objects = self._extract_objects(image_rgb, masks, boxes)

            return {
                'objects_found': len(masks),
                'masks': masks.tolist(),
                'labels': labels.tolist(),
                'scores': scores.tolist(),
                'boxes': boxes.tolist(),
                'class_names': class_names,
                'segmented_objects': segmented_objects,
                'image_info': {
                    'width': original_width,
                    'height': original_height,
                    'channels': 3
                }
            }

        except Exception as e:
            logger.error(f"Object segmentation failed: {e}")
            return {
                'objects_found': 0,
                'masks': [],
                'labels': [],
                'scores': [],
                'boxes': [],
                'class_names': [],
                'segmented_objects': [],
                'error': str(e)
            }

    def create_puzzle_pieces(self, image_path: str, piece_count: int = 20) -> Dict[str, Any]:
        """Create puzzle pieces using segmentation-based approach"""
        try:
            # First, segment the image
            segmentation_result = self.segment_objects(image_path)

            if segmentation_result['objects_found'] == 0:
                # Fallback to grid-based segmentation
                return self._create_grid_based_pieces(image_path, piece_count)

            # Use segmented objects as basis for puzzle pieces
            image = cv2.imread(image_path)
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            puzzle_pieces = []
            masks = np.array(segmentation_result['masks'])

            for i, (mask, box, class_name, score) in enumerate(zip(
                masks,
                segmentation_result['boxes'],
                segmentation_result['class_names'],
                segmentation_result['scores']
            )):
                # Create puzzle piece from segmented object
                piece = self._create_piece_from_mask(
                    image_rgb, mask[0], box, i, class_name, score
                )
                puzzle_pieces.append(piece)

            # If we have fewer pieces than requested, add grid-based pieces
            if len(puzzle_pieces) < piece_count:
                additional_pieces = self._create_additional_grid_pieces(
                    image_rgb, piece_count - len(puzzle_pieces), len(puzzle_pieces)
                )
                puzzle_pieces.extend(additional_pieces)

            return {
                'puzzle_type': 'segmentation_based',
                'total_pieces': len(puzzle_pieces),
                'pieces': puzzle_pieces,
                'segmentation_info': {
                    'objects_detected': segmentation_result['objects_found'],
                    'classes_found': list(set(segmentation_result['class_names']))
                }
            }

        except Exception as e:
            logger.error(f"Puzzle piece creation failed: {e}")
            return {
                'puzzle_type': 'error',
                'total_pieces': 0,
                'pieces': [],
                'error': str(e)
            }

    def _extract_objects(self, image: np.ndarray, masks: np.ndarray, boxes: np.ndarray) -> List[Dict[str, Any]]:
        """Extract individual objects from the image using masks"""
        objects = []

        for i, (mask, box) in enumerate(zip(masks, boxes)):
            try:
                # Get mask for this object (threshold at 0.5)
                binary_mask = (mask[0] > 0.5).astype(np.uint8)

                # Extract bounding box coordinates
                x1, y1, x2, y2 = box.astype(int)

                # Crop the object using bounding box
                cropped_image = image[y1:y2, x1:x2]
                cropped_mask = binary_mask[y1:y2, x1:x2]

                # Apply mask to cropped image
                masked_object = cropped_image.copy()
                masked_object[cropped_mask == 0] = [255, 255, 255]  # White background

                objects.append({
                    'object_id': i,
                    'bbox': [int(x1), int(y1), int(x2), int(y2)],
                    'mask_area': int(np.sum(binary_mask)),
                    'object_image': masked_object.tolist(),
                    'mask': binary_mask.tolist()
                })

            except Exception as e:
                logger.warning(f"Failed to extract object {i}: {e}")
                continue

        return objects

    def _create_piece_from_mask(self, image: np.ndarray, mask: np.ndarray, box: np.ndarray, 
                               piece_id: int, class_name: str, score: float) -> Dict[str, Any]:
        """Create a puzzle piece from a segmented object"""
        # Get bounding box
        x1, y1, x2, y2 = box.astype(int)

        # Create binary mask
        binary_mask = (mask > 0.5).astype(np.uint8)

        # Calculate center of mass for the piece
        y_coords, x_coords = np.where(binary_mask)
        if len(x_coords) > 0:
            center_x = int(np.mean(x_coords))
            center_y = int(np.mean(y_coords))
        else:
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2

        # Generate puzzle piece edges
        edges = self._generate_puzzle_edges(piece_id)

        # Generate actual image data for the puzzle piece
        bbox = [int(x1), int(y1), int(x2), int(y2)]
        image_data = self._generate_piece_image_data(image, bbox, edges)

        return {
            'id': f"seg_{piece_id}",
            'type': 'segmented_object',
            'class_name': class_name,
            'confidence': float(score),
            'bbox': bbox,
            'center': [center_x, center_y],
            'mask_area': int(np.sum(binary_mask)),
            'difficulty': self._calculate_piece_difficulty(binary_mask, x2-x1, y2-y1),
            'edges': edges,
            'width': int(x2 - x1),
            'height': int(y2 - y1),
            'correctPosition': {'x': int(x1), 'y': int(y1)},
            'currentPosition': {'x': int(x1), 'y': int(y1)},
            'rotation': 0,
            'isPlaced': False,
            'isSelected': False,
            'imageData': image_data
        }

    def _create_grid_based_pieces(self, image_path: str, piece_count: int) -> Dict[str, Any]:
        """Fallback method to create grid-based puzzle pieces"""
        try:
            image = cv2.imread(image_path)
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            height, width = image_rgb.shape[:2]

            # Calculate grid dimensions
            cols = int(np.sqrt(piece_count * width / height))
            rows = int(piece_count / cols)

            piece_width = width // cols
            piece_height = height // rows

            pieces = []
            piece_id = 0

            for row in range(rows):
                for col in range(cols):
                    x1 = col * piece_width
                    y1 = row * piece_height
                    x2 = min(x1 + piece_width, width)
                    y2 = min(y1 + piece_height, height)

                    # Generate edges for grid piece with proper adjacency
                    edges = self._generate_grid_puzzle_edges(row, col, rows, cols)

                    # Generate actual image data for the puzzle piece
                    bbox = [x1, y1, x2, y2]
                    image_data = self._generate_piece_image_data(image_rgb, bbox, edges)

                    pieces.append({
                        'id': f"grid_{piece_id}",
                        'type': 'grid_piece',
                        'bbox': bbox,
                        'center': [(x1 + x2) // 2, (y1 + y2) // 2],
                        'grid_position': [row, col],
                        'difficulty': 'medium',
                        'edges': edges,
                        'width': x2 - x1,
                        'height': y2 - y1,
                        'correctPosition': {'x': x1, 'y': y1},
                        'currentPosition': {'x': x1, 'y': y1},
                        'rotation': 0,
                        'isPlaced': False,
                        'isSelected': False,
                        'imageData': image_data
                    })
                    piece_id += 1

            return {
                'puzzle_type': 'grid_based',
                'total_pieces': len(pieces),
                'pieces': pieces,
                'grid_info': {
                    'rows': rows,
                    'cols': cols,
                    'piece_size': [piece_width, piece_height]
                }
            }

        except Exception as e:
            logger.error(f"Grid-based piece creation failed: {e}")
            return {
                'puzzle_type': 'error',
                'total_pieces': 0,
                'pieces': [],
                'error': str(e)
            }

    def _create_additional_grid_pieces(self, image: np.ndarray, additional_count: int, 
                                     start_id: int) -> List[Dict[str, Any]]:
        """Create additional grid-based pieces to reach target count"""
        height, width = image.shape[:2]
        pieces = []

        # Simple grid subdivision for additional pieces
        cols = int(np.sqrt(additional_count))
        rows = int(np.ceil(additional_count / cols))

        piece_width = width // cols
        piece_height = height // rows

        piece_id = start_id
        count = 0

        for row in range(rows):
            for col in range(cols):
                if count >= additional_count:
                    break

                x1 = col * piece_width
                y1 = row * piece_height
                x2 = min(x1 + piece_width, width)
                y2 = min(y1 + piece_height, height)

                # Generate edges for additional grid piece
                edges = self._generate_grid_puzzle_edges(row, col, rows, cols)

                # Generate actual image data for the puzzle piece
                bbox = [x1, y1, x2, y2]
                image_data = self._generate_piece_image_data(image, bbox, edges)

                pieces.append({
                    'id': f"add_{piece_id}",
                    'type': 'additional_grid',
                    'bbox': bbox,
                    'center': [(x1 + x2) // 2, (y1 + y2) // 2],
                    'difficulty': 'easy',
                    'edges': edges,
                    'width': x2 - x1,
                    'height': y2 - y1,
                    'correctPosition': {'x': x1, 'y': y1},
                    'currentPosition': {'x': x1, 'y': y1},
                    'rotation': 0,
                    'isPlaced': False,
                    'isSelected': False,
                    'imageData': image_data
                })

                piece_id += 1
                count += 1

        return pieces

    def _generate_puzzle_edges(self, piece_id: int) -> Dict[str, str]:
        """Generate puzzle piece edges (tab/blank) for each side"""
        import random

        # Set seed based on piece_id for consistent generation
        random.seed(piece_id * 42)

        edges = {}
        sides = ['top', 'right', 'bottom', 'left']

        for side in sides:
            # Randomly assign tab or blank
            # 50% chance for each
            edges[side] = random.choice(['tab', 'blank'])

        return edges

    def _generate_grid_puzzle_edges(self, row: int, col: int, total_rows: int, total_cols: int) -> Dict[str, str]:
        """Generate puzzle piece edges for grid-based pieces with proper adjacency"""
        import random

        # Use consistent seed based on position
        random.seed((row * total_cols + col) * 123)

        edges = {}

        # Top edge
        if row == 0:
            edges['top'] = 'flat'  # Border pieces have flat edges
        else:
            # Must be opposite of the piece above
            above_seed = ((row - 1) * total_cols + col) * 123
            random.seed(above_seed)
            above_bottom = random.choice(['tab', 'blank'])
            edges['top'] = 'blank' if above_bottom == 'tab' else 'tab'

        # Right edge
        if col == total_cols - 1:
            edges['right'] = 'flat'  # Border pieces have flat edges
        else:
            edges['right'] = random.choice(['tab', 'blank'])

        # Bottom edge
        if row == total_rows - 1:
            edges['bottom'] = 'flat'  # Border pieces have flat edges
        else:
            edges['bottom'] = random.choice(['tab', 'blank'])

        # Left edge
        if col == 0:
            edges['left'] = 'flat'  # Border pieces have flat edges
        else:
            # Must be opposite of the piece to the left
            left_seed = (row * total_cols + (col - 1)) * 123
            random.seed(left_seed)
            left_right = random.choice(['tab', 'blank'])
            edges['left'] = 'blank' if left_right == 'tab' else 'tab'

        return edges

    def _generate_piece_image_data(self, image: np.ndarray, bbox: List[int], edges: Dict[str, str]) -> str:
        """Generate Base64 encoded image data for a puzzle piece with proper shape"""
        try:
            x1, y1, x2, y2 = bbox

            # Extract piece region from original image
            piece_image = image[y1:y2, x1:x2].copy()

            return self._generate_piece_image_data_from_array(piece_image, edges)

        except Exception as e:
            logger.error(f"Error generating piece image data: {e}")
            return ""

    def _generate_piece_image_data_from_array(self, piece_image: np.ndarray, edges: Dict[str, str]) -> str:
        """Generate Base64 encoded image data for a puzzle piece from numpy array with proper shape"""
        try:
            height, width = piece_image.shape[:2]

            # Create puzzle piece shape mask
            mask = self._create_puzzle_shape_mask(width, height, edges)
            mask_height, mask_width = mask.shape

            # Calculate tab extensions (consistent with mask calculation)
            tab_depth = 0.15
            tab_size = int(min(width, height) * tab_depth)

            # Calculate extensions for each side
            top_ext = tab_size if edges.get('top') == 'tab' else 0
            right_ext = tab_size if edges.get('right') == 'tab' else 0
            bottom_ext = tab_size if edges.get('bottom') == 'tab' else 0
            left_ext = tab_size if edges.get('left') == 'tab' else 0

            # Create extended canvas for the image
            extended_image = np.zeros((mask_height, mask_width, 3), dtype=np.uint8)

            # Place original piece image in the correct position
            extended_image[top_ext:top_ext+height, left_ext:left_ext+width] = piece_image

            # For tab areas, extend the image by replicating edge pixels
            # Top tab
            if edges.get('top') == 'tab':
                # Replicate top edge pixels upward
                for y in range(top_ext):
                    extended_image[y, left_ext:left_ext+width] = piece_image[0, :]

            # Right tab
            if edges.get('right') == 'tab':
                # Replicate right edge pixels rightward
                for x in range(left_ext + width, mask_width):
                    extended_image[top_ext:top_ext+height, x] = piece_image[:, -1]

            # Bottom tab
            if edges.get('bottom') == 'tab':
                # Replicate bottom edge pixels downward
                for y in range(top_ext + height, mask_height):
                    extended_image[y, left_ext:left_ext+width] = piece_image[-1, :]

            # Left tab
            if edges.get('left') == 'tab':
                # Replicate left edge pixels leftward
                for x in range(left_ext):
                    extended_image[top_ext:top_ext+height, x] = piece_image[:, 0]

            # Convert to PIL Image
            pil_image = Image.fromarray(extended_image)

            # Convert to RGBA for transparency support
            pil_image = pil_image.convert('RGBA')

            # Apply puzzle shape mask
            mask_pil = Image.fromarray((mask * 255).astype(np.uint8), mode='L')
            pil_image.putalpha(mask_pil)

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

    def _create_puzzle_shape_mask(self, width: int, height: int, edges: Dict[str, str]) -> np.ndarray:
        """Create a mask for puzzle piece shape based on edges information"""
        tab_depth = 0.15  # Tab depth as fraction of piece size
        tab_size = int(min(width, height) * tab_depth)

        # Calculate extended dimensions to accommodate tabs
        has_top_tab = edges.get('top') == 'tab'
        has_right_tab = edges.get('right') == 'tab'
        has_bottom_tab = edges.get('bottom') == 'tab'
        has_left_tab = edges.get('left') == 'tab'

        # Calculate extensions needed
        top_ext = tab_size if has_top_tab else 0
        right_ext = tab_size if has_right_tab else 0
        bottom_ext = tab_size if has_bottom_tab else 0
        left_ext = tab_size if has_left_tab else 0

        # Create extended mask
        extended_width = width + left_ext + right_ext
        extended_height = height + top_ext + bottom_ext
        mask = np.zeros((extended_height, extended_width), dtype=np.float32)

        # Fill the base rectangle in the extended mask
        mask[top_ext:top_ext + height, left_ext:left_ext + width] = 1.0

        # Calculate centers relative to the extended mask
        base_center_x = left_ext + width // 2
        base_center_y = top_ext + height // 2

        # Add tabs and blanks using circular shapes
        import cv2

        # Top edge
        if edges.get('top') == 'tab':
            # Add protruding tab at top
            tab_center_x = base_center_x
            tab_center_y = top_ext  # At the top edge of the base rectangle
            cv2.circle(mask, (tab_center_x, tab_center_y), tab_size, 1.0, -1)
        elif edges.get('top') == 'blank':
            # Create indentation at top
            blank_center_x = base_center_x
            blank_center_y = top_ext + tab_size  # Inside the base rectangle
            cv2.circle(mask, (blank_center_x, blank_center_y), tab_size, 0.0, -1)

        # Right edge
        if edges.get('right') == 'tab':
            # Add protruding tab at right
            tab_center_x = left_ext + width  # At the right edge of the base rectangle
            tab_center_y = base_center_y
            cv2.circle(mask, (tab_center_x, tab_center_y), tab_size, 1.0, -1)
        elif edges.get('right') == 'blank':
            # Create indentation at right
            blank_center_x = left_ext + width - tab_size  # Inside the base rectangle
            blank_center_y = base_center_y
            cv2.circle(mask, (blank_center_x, blank_center_y), tab_size, 0.0, -1)

        # Bottom edge
        if edges.get('bottom') == 'tab':
            # Add protruding tab at bottom
            tab_center_x = base_center_x
            tab_center_y = top_ext + height  # At the bottom edge of the base rectangle
            cv2.circle(mask, (tab_center_x, tab_center_y), tab_size, 1.0, -1)
        elif edges.get('bottom') == 'blank':
            # Create indentation at bottom
            blank_center_x = base_center_x
            blank_center_y = top_ext + height - tab_size  # Inside the base rectangle
            cv2.circle(mask, (blank_center_x, blank_center_y), tab_size, 0.0, -1)

        # Left edge
        if edges.get('left') == 'tab':
            # Add protruding tab at left
            tab_center_x = left_ext  # At the left edge of the base rectangle
            tab_center_y = base_center_y
            cv2.circle(mask, (tab_center_x, tab_center_y), tab_size, 1.0, -1)
        elif edges.get('left') == 'blank':
            # Create indentation at left
            blank_center_x = left_ext + tab_size  # Inside the base rectangle
            blank_center_y = base_center_y
            cv2.circle(mask, (blank_center_x, blank_center_y), tab_size, 0.0, -1)

        return mask

    def _calculate_piece_difficulty(self, mask: np.ndarray, width: int, height: int) -> str:
        """Calculate difficulty level for a puzzle piece"""
        # Calculate complexity based on mask shape and size
        mask_area = np.sum(mask)
        total_area = width * height
        area_ratio = mask_area / total_area if total_area > 0 else 0

        # Calculate edge complexity (perimeter to area ratio)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            perimeter = cv2.arcLength(contours[0], True)
            complexity = perimeter / (mask_area ** 0.5) if mask_area > 0 else 0
        else:
            complexity = 0

        # Determine difficulty
        if area_ratio < 0.3 or complexity > 15:
            return 'hard'
        elif area_ratio < 0.6 or complexity > 10:
            return 'medium'
        else:
            return 'easy'

    def segment_subject_background(self, image_path: str, confidence_threshold: float = 0.7) -> Dict[str, Any]:
        """고급 피사체/배경 분리 기능"""
        try:
            # 1. 기본 객체 분할 수행
            segmentation_result = self.segment_objects(image_path, confidence_threshold)

            if segmentation_result['objects_found'] == 0:
                return self._fallback_subject_background_separation(image_path)

            # 2. 주요 피사체 식별
            main_subject = self._identify_main_subject(segmentation_result)

            # 3. 피사체와 배경 마스크 생성
            image = cv2.imread(image_path)
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            height, width = image_rgb.shape[:2]

            subject_mask, background_mask = self._create_subject_background_masks(
                segmentation_result, main_subject, height, width
            )

            # 4. 분리 품질 평가
            separation_quality = self._evaluate_separation_quality(
                subject_mask, background_mask, segmentation_result
            )

            return {
                'success': True,
                'subject_mask': subject_mask.tolist(),
                'background_mask': background_mask.tolist(),
                'main_subject_info': main_subject,
                'separation_quality': separation_quality,
                'image_info': {
                    'width': width,
                    'height': height,
                    'total_objects': segmentation_result['objects_found']
                }
            }

        except Exception as e:
            logger.error(f"Subject/background separation failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'fallback_result': self._fallback_subject_background_separation(image_path)
            }

    def _identify_main_subject(self, segmentation_result: Dict[str, Any]) -> Dict[str, Any]:
        """주요 피사체 식별 (크기, 위치, 클래스 기반)"""
        if segmentation_result['objects_found'] == 0:
            return {}

        masks = np.array(segmentation_result['masks'])
        boxes = segmentation_result['boxes']
        class_names = segmentation_result['class_names']
        scores = segmentation_result['scores']

        # 피사체 우선순위 클래스 (사람, 동물 등)
        priority_classes = ['person', 'cat', 'dog', 'bird', 'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra', 'giraffe']

        candidates = []

        for i, (mask, box, class_name, score) in enumerate(zip(masks, boxes, class_names, scores)):
            # 마스크 면적 계산
            mask_area = np.sum(mask[0] > 0.5)

            # 중앙 위치 계산
            x1, y1, x2, y2 = box
            center_x = (x1 + x2) / 2
            center_y = (y1 + y2) / 2

            # 이미지 중앙으로부터의 거리
            image_center_x = segmentation_result['image_info']['width'] / 2
            image_center_y = segmentation_result['image_info']['height'] / 2
            distance_from_center = np.sqrt(
                (center_x - image_center_x) ** 2 + (center_y - image_center_y) ** 2
            )

            # 우선순위 점수 계산
            priority_score = 0
            if class_name in priority_classes:
                priority_score = 10

            # 종합 점수 (면적 + 중앙 위치 + 클래스 우선순위 + 신뢰도)
            total_score = (
                mask_area * 0.3 +  # 면적 가중치
                (1 / (distance_from_center + 1)) * 1000 * 0.3 +  # 중앙 위치 가중치
                priority_score * 0.2 +  # 클래스 우선순위
                score * 100 * 0.2  # 신뢰도
            )

            candidates.append({
                'index': i,
                'class_name': class_name,
                'score': score,
                'mask_area': mask_area,
                'center': [center_x, center_y],
                'distance_from_center': distance_from_center,
                'priority_score': priority_score,
                'total_score': total_score,
                'bbox': box
            })

        # 가장 높은 점수의 객체를 주요 피사체로 선택
        main_subject = max(candidates, key=lambda x: x['total_score'])

        return main_subject

    def _create_subject_background_masks(self, segmentation_result: Dict[str, Any], 
                                       main_subject: Dict[str, Any], height: int, width: int) -> Tuple[np.ndarray, np.ndarray]:
        """피사체와 배경 마스크 생성"""
        # 전체 이미지 크기의 마스크 초기화
        subject_mask = np.zeros((height, width), dtype=np.uint8)
        background_mask = np.ones((height, width), dtype=np.uint8)

        if not main_subject:
            return subject_mask, background_mask

        masks = np.array(segmentation_result['masks'])
        main_subject_index = main_subject['index']

        # 주요 피사체 마스크 설정
        main_mask = (masks[main_subject_index][0] > 0.5).astype(np.uint8)
        subject_mask = main_mask

        # 관련 객체들도 피사체에 포함 (같은 클래스이거나 인접한 객체)
        for i, (mask, class_name) in enumerate(zip(masks, segmentation_result['class_names'])):
            if i == main_subject_index:
                continue

            # 같은 클래스의 객체는 피사체에 포함
            if class_name == main_subject['class_name']:
                additional_mask = (mask[0] > 0.5).astype(np.uint8)
                subject_mask = np.logical_or(subject_mask, additional_mask).astype(np.uint8)

        # 배경 마스크는 피사체 마스크의 반전
        background_mask = (1 - subject_mask).astype(np.uint8)

        return subject_mask, background_mask

    def _evaluate_separation_quality(self, subject_mask: np.ndarray, background_mask: np.ndarray, 
                                   segmentation_result: Dict[str, Any]) -> Dict[str, Any]:
        """분리 품질 평가"""
        total_pixels = subject_mask.shape[0] * subject_mask.shape[1]
        subject_pixels = np.sum(subject_mask)
        background_pixels = np.sum(background_mask)

        # 피사체/배경 비율
        subject_ratio = subject_pixels / total_pixels
        background_ratio = background_pixels / total_pixels

        # 분리 품질 점수 계산
        quality_score = 0.0

        # 1. 적절한 피사체/배경 비율 (20-80% 사이가 이상적)
        if 0.2 <= subject_ratio <= 0.8:
            quality_score += 0.3

        # 2. 객체 탐지 신뢰도
        if segmentation_result['objects_found'] > 0:
            avg_confidence = np.mean(segmentation_result['scores'])
            quality_score += avg_confidence * 0.3

        # 3. 마스크 연속성 (contour 분석)
        contours, _ = cv2.findContours(subject_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            # 가장 큰 contour의 면적 비율
            largest_contour_area = max([cv2.contourArea(c) for c in contours])
            contour_ratio = largest_contour_area / subject_pixels if subject_pixels > 0 else 0
            quality_score += contour_ratio * 0.4

        # 품질 등급 결정
        if quality_score >= 0.8:
            quality_grade = 'excellent'
        elif quality_score >= 0.6:
            quality_grade = 'good'
        elif quality_score >= 0.4:
            quality_grade = 'fair'
        else:
            quality_grade = 'poor'

        return {
            'quality_score': quality_score,
            'quality_grade': quality_grade,
            'subject_ratio': subject_ratio,
            'background_ratio': background_ratio,
            'contour_count': len(contours) if contours else 0,
            'recommendations': self._get_quality_recommendations(quality_score, subject_ratio)
        }

    def _get_quality_recommendations(self, quality_score: float, subject_ratio: float) -> List[str]:
        """품질 개선 권장사항"""
        recommendations = []

        if quality_score < 0.5:
            recommendations.append("이미지의 피사체가 명확하지 않습니다. 더 선명한 이미지를 사용해보세요.")

        if subject_ratio < 0.1:
            recommendations.append("피사체가 너무 작습니다. 피사체가 더 크게 나온 이미지를 사용해보세요.")
        elif subject_ratio > 0.9:
            recommendations.append("배경이 너무 적습니다. 배경이 더 많이 보이는 이미지를 사용해보세요.")

        if quality_score < 0.3:
            recommendations.append("자동 분할이 어려운 이미지입니다. 수동 설정을 고려해보세요.")

        return recommendations

    def _fallback_subject_background_separation(self, image_path: str) -> Dict[str, Any]:
        """객체 탐지 실패 시 대체 분리 방법"""
        try:
            image = cv2.imread(image_path)
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            height, width = image_rgb.shape[:2]

            # 간단한 중앙 영역을 피사체로 가정
            center_x, center_y = width // 2, height // 2
            subject_width = int(width * 0.6)
            subject_height = int(height * 0.6)

            subject_mask = np.zeros((height, width), dtype=np.uint8)
            x1 = max(0, center_x - subject_width // 2)
            y1 = max(0, center_y - subject_height // 2)
            x2 = min(width, center_x + subject_width // 2)
            y2 = min(height, center_y + subject_height // 2)

            subject_mask[y1:y2, x1:x2] = 1
            background_mask = 1 - subject_mask

            return {
                'success': True,
                'method': 'fallback_center_region',
                'subject_mask': subject_mask.tolist(),
                'background_mask': background_mask.tolist(),
                'separation_quality': {
                    'quality_score': 0.3,
                    'quality_grade': 'fair',
                    'subject_ratio': 0.36,
                    'background_ratio': 0.64
                }
            }

        except Exception as e:
            logger.error(f"Fallback separation failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def generate_intelligent_puzzle_pieces(self, image_path: str, piece_count: int = 50, 
                                         subject_background_ratio: float = 0.6) -> Dict[str, Any]:
        """지능형 퍼즐 피스 생성 (피사체/배경 기반)"""
        try:
            # 1. 피사체/배경 분리
            separation_result = self.segment_subject_background(image_path)

            if not separation_result['success']:
                # 분리 실패 시 기본 방법 사용
                return self.create_puzzle_pieces(image_path, piece_count)

            # 2. 피사체와 배경 영역별 피스 수 계산
            subject_pieces_count = int(piece_count * subject_background_ratio)
            background_pieces_count = piece_count - subject_pieces_count

            # 3. 각 영역별 퍼즐 피스 생성
            subject_pieces = self._generate_subject_pieces(
                image_path, separation_result['subject_mask'], subject_pieces_count
            )

            background_pieces = self._generate_background_pieces(
                image_path, separation_result['background_mask'], background_pieces_count
            )

            # 4. 피스 난이도 최적화
            optimized_pieces = self._optimize_piece_difficulty(subject_pieces, background_pieces)

            # 5. 모든 조각에 edges 할당
            pieces = optimized_pieces
            # 1) 모든 조각 edges 초기화
            for p in pieces:
                p['edges'] = {'top': 'flat', 'right': 'flat', 'bottom': 'flat', 'left': 'flat'}

            # 2) 인접한 조각끼리 'tab'/'blank' 할당 (수정된 로직)
            tolerance = 5  # 인접 검사 허용 오차 (더 정확하게)
            for i, p in enumerate(pieces):
                for j, q in enumerate(pieces):
                    if i >= j:  # 중복 검사 방지
                        continue

                    # x, y, width, height에서 bbox 정보 계산
                    p_x1, p_y1 = p['bbox'][0], p['bbox'][1]
                    p_x2, p_y2 = p['bbox'][2], p['bbox'][3]
                    q_x1, q_y1 = q['bbox'][0], q['bbox'][1]
                    q_x2, q_y2 = q['bbox'][2], q['bbox'][3]

                    # p가 q의 왼쪽에 있는 경우 (p의 right edge와 q의 left edge가 인접)
                    if (abs(p_x2 - q_x1) < tolerance and 
                        abs(p_y1 - q_y1) < tolerance and 
                        abs(p_y2 - q_y2) < tolerance):
                        p['edges']['right'] = 'tab'
                        q['edges']['left'] = 'blank'

                    # p가 q의 오른쪽에 있는 경우 (p의 left edge와 q의 right edge가 인접)
                    elif (abs(p_x1 - q_x2) < tolerance and 
                          abs(p_y1 - q_y1) < tolerance and 
                          abs(p_y2 - q_y2) < tolerance):
                        p['edges']['left'] = 'tab'
                        q['edges']['right'] = 'blank'

                    # p가 q의 위쪽에 있는 경우 (p의 bottom edge와 q의 top edge가 인접)
                    elif (abs(p_y2 - q_y1) < tolerance and 
                          abs(p_x1 - q_x1) < tolerance and 
                          abs(p_x2 - q_x2) < tolerance):
                        p['edges']['bottom'] = 'tab'
                        q['edges']['top'] = 'blank'

                    # p가 q의 아래쪽에 있는 경우 (p의 top edge와 q의 bottom edge가 인접)
                    elif (abs(p_y1 - q_y2) < tolerance and 
                          abs(p_x1 - q_x1) < tolerance and 
                          abs(p_x2 - q_x2) < tolerance):
                        p['edges']['top'] = 'tab'
                        q['edges']['bottom'] = 'blank'

            # 6. 원본 이미지 로드 및 각 조각의 imageData 생성
            original_image = cv2.imread(image_path)
            if original_image is None:
                raise ValueError(f"Could not load image: {image_path}")

            original_image = cv2.cvtColor(original_image, cv2.COLOR_BGR2RGB)

            # 마스크를 numpy 배열로 변환
            subject_mask_np = np.array(separation_result['subject_mask'], dtype=np.uint8)
            background_mask_np = np.array(separation_result['background_mask'], dtype=np.uint8)

            for p in pieces:
                x1, y1, x2, y2 = p['bbox']

                # 조각 영역의 이미지 추출
                piece_img = original_image[y1:y2, x1:x2].copy()

                # 세그멘테이션 마스크 적용하여 피사체/배경 강조
                if p['region'] == 'subject':
                    # 피사체 조각: 배경 픽셀을 흰색으로 처리
                    mask_slice = background_mask_np[y1:y2, x1:x2]
                    piece_img[mask_slice == 1] = (255, 255, 255)  # 배경 부분을 흰색으로
                elif p['region'] == 'background':
                    # 배경 조각: 피사체 픽셀을 흰색으로 처리 (피사체 모양의 구멍 생성)
                    mask_slice = subject_mask_np[y1:y2, x1:x2]
                    piece_img[mask_slice == 1] = (255, 255, 255)  # 피사체 부분을 흰색으로

                # 마스크가 적용된 이미지로 퍼즐 조각 이미지 데이터 생성
                p['imageData'] = self._generate_piece_image_data_from_array(piece_img, p['edges'])
                p['width'] = x2 - x1
                p['height'] = y2 - y1
                p['x'] = x1  # JSON 형식에 맞게 x, y 속성 추가
                p['y'] = y1
                p['rotation'] = 0
                p['isPlaced'] = False
                p['isSelected'] = False

                # correctPosition과 currentPosition 설정
                p['correctPosition'] = {'x': x1, 'y': y1}
                p['currentPosition'] = {'x': x1, 'y': y1}  # 초기에는 정답 위치에 배치

            return {
                'puzzle_type': 'intelligent_subject_background',
                'total_pieces': len(pieces),
                'pieces': pieces,
                'separation_info': separation_result,
                'piece_distribution': {
                    'subject_pieces': len(subject_pieces),
                    'background_pieces': len(background_pieces),
                    'subject_ratio': subject_background_ratio
                }
            }

        except Exception as e:
            logger.error(f"Intelligent puzzle generation failed: {e}")
            return {
                'puzzle_type': 'error',
                'total_pieces': 0,
                'pieces': [],
                'error': str(e)
            }

    def _generate_subject_pieces(self, image_path: str, subject_mask: List, piece_count: int) -> List[Dict[str, Any]]:
        """피사체 영역 퍼즐 피스 생성"""
        pieces = []
        subject_mask_np = np.array(subject_mask, dtype=np.uint8)

        # 피사체 영역의 contour 찾기
        contours, _ = cv2.findContours(subject_mask_np, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return pieces

        # 가장 큰 contour 사용
        main_contour = max(contours, key=cv2.contourArea)

        # 피사체 영역을 적응적으로 분할
        x, y, w, h = cv2.boundingRect(main_contour)

        # 피사체 크기에 따른 그리드 계산
        cols = max(2, int(np.sqrt(piece_count * w / h)))
        rows = max(2, int(piece_count / cols))

        piece_width = w // cols
        piece_height = h // rows

        piece_id = 0
        for row in range(rows):
            for col in range(cols):
                if piece_id >= piece_count:
                    break

                px1 = x + col * piece_width
                py1 = y + row * piece_height
                px2 = min(x + w, px1 + piece_width)
                py2 = min(y + h, py1 + piece_height)

                # 해당 영역이 피사체 마스크와 겹치는지 확인
                piece_mask = subject_mask_np[py1:py2, px1:px2]
                overlap_ratio = np.sum(piece_mask) / (piece_mask.shape[0] * piece_mask.shape[1])

                if overlap_ratio > 0.3:  # 30% 이상 겹치면 유효한 피스
                    pieces.append({
                        'id': f"subject_{piece_id}",
                        'type': 'subject_piece',
                        'bbox': [px1, py1, px2, py2],
                        'center': [(px1 + px2) // 2, (py1 + py2) // 2],
                        'overlap_ratio': overlap_ratio,
                        'difficulty': 'hard' if overlap_ratio > 0.8 else 'medium',
                        'region': 'subject'
                    })
                    piece_id += 1

        return pieces

    def _generate_background_pieces(self, image_path: str, background_mask: List, piece_count: int) -> List[Dict[str, Any]]:
        """배경 영역 퍼즐 피스 생성"""
        pieces = []
        background_mask_np = np.array(background_mask, dtype=np.uint8)
        height, width = background_mask_np.shape

        # 배경 영역을 균등하게 분할
        cols = max(2, int(np.sqrt(piece_count * width / height)))
        rows = max(2, int(piece_count / cols))

        piece_width = width // cols
        piece_height = height // rows

        piece_id = 0
        for row in range(rows):
            for col in range(cols):
                if piece_id >= piece_count:
                    break

                bx1 = col * piece_width
                by1 = row * piece_height
                bx2 = min(width, bx1 + piece_width)
                by2 = min(height, by1 + piece_height)

                # 해당 영역이 배경 마스크와 겹치는지 확인
                piece_mask = background_mask_np[by1:by2, bx1:bx2]
                overlap_ratio = np.sum(piece_mask) / (piece_mask.shape[0] * piece_mask.shape[1])

                if overlap_ratio > 0.5:  # 50% 이상 겹치면 유효한 피스
                    pieces.append({
                        'id': f"background_{piece_id}",
                        'type': 'background_piece',
                        'bbox': [bx1, by1, bx2, by2],
                        'center': [(bx1 + bx2) // 2, (by1 + by2) // 2],
                        'overlap_ratio': overlap_ratio,
                        'difficulty': 'easy' if overlap_ratio > 0.8 else 'medium',
                        'region': 'background'
                    })
                    piece_id += 1

        return pieces

    def _optimize_piece_difficulty(self, subject_pieces: List[Dict[str, Any]], 
                                 background_pieces: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """피스 난이도 최적화"""
        all_pieces = subject_pieces + background_pieces

        # 난이도 분포 조정
        easy_count = len([p for p in all_pieces if p['difficulty'] == 'easy'])
        medium_count = len([p for p in all_pieces if p['difficulty'] == 'medium'])
        hard_count = len([p for p in all_pieces if p['difficulty'] == 'hard'])

        total_pieces = len(all_pieces)

        # 이상적인 난이도 분포: easy 40%, medium 40%, hard 20%
        target_easy = int(total_pieces * 0.4)
        target_medium = int(total_pieces * 0.4)
        target_hard = int(total_pieces * 0.2)

        # 난이도 재조정
        for piece in all_pieces:
            if piece['region'] == 'subject':
                # 피사체 피스는 일반적으로 더 어려움
                if piece['overlap_ratio'] > 0.9:
                    piece['difficulty'] = 'hard'
                elif piece['overlap_ratio'] > 0.6:
                    piece['difficulty'] = 'medium'
                else:
                    piece['difficulty'] = 'easy'
            else:
                # 배경 피스는 일반적으로 더 쉬움
                if piece['overlap_ratio'] > 0.9:
                    piece['difficulty'] = 'medium'
                else:
                    piece['difficulty'] = 'easy'

        return all_pieces
