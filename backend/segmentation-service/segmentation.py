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
        
        return {
            'id': f"seg_{piece_id}",
            'type': 'segmented_object',
            'class_name': class_name,
            'confidence': float(score),
            'bbox': [int(x1), int(y1), int(x2), int(y2)],
            'center': [center_x, center_y],
            'mask_area': int(np.sum(binary_mask)),
            'difficulty': self._calculate_piece_difficulty(binary_mask, x2-x1, y2-y1)
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
                    
                    pieces.append({
                        'id': f"grid_{piece_id}",
                        'type': 'grid_piece',
                        'bbox': [x1, y1, x2, y2],
                        'center': [(x1 + x2) // 2, (y1 + y2) // 2],
                        'grid_position': [row, col],
                        'difficulty': 'medium'
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
                
                pieces.append({
                    'id': f"add_{piece_id}",
                    'type': 'additional_grid',
                    'bbox': [x1, y1, x2, y2],
                    'center': [(x1 + x2) // 2, (y1 + y2) // 2],
                    'difficulty': 'easy'
                })
                
                piece_id += 1
                count += 1
        
        return pieces
    
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