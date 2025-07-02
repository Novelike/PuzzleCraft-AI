import torch
import torch.nn as nn
import torchvision.transforms as transforms
from torchvision.models import vgg19, VGG19_Weights
from PIL import Image
import numpy as np
import cv2
import logging
from typing import Dict, Any, Optional, Tuple
import os
from pathlib import Path
import requests
import io

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NeuralStyleTransfer:
    def __init__(self):
        """Initialize neural style transfer with VGG19 model"""
        try:
            # Set device
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

            # Load VGG19 model
            weights = VGG19_Weights.DEFAULT
            self.vgg = vgg19(weights=weights).features.to(self.device).eval()

            # Freeze VGG parameters
            for param in self.vgg.parameters():
                param.requires_grad_(False)

            # Style layers for feature extraction
            self.style_layers = ['conv_1', 'conv_2', 'conv_3', 'conv_4', 'conv_5']
            self.content_layers = ['conv_4']

            # Image transformation
            self.transform = transforms.Compose([
                transforms.Resize((512, 512)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                                   std=[0.229, 0.224, 0.225])
            ])

            self.denormalize = transforms.Normalize(
                mean=[-0.485/0.229, -0.456/0.224, -0.406/0.225],
                std=[1/0.229, 1/0.224, 1/0.225]
            )

            # Available styles with their characteristics
            self.available_styles = {
                'watercolor': {
                    'description': 'Soft, flowing watercolor painting style',
                    'characteristics': ['soft_edges', 'color_bleeding', 'transparency']
                },
                'cartoon': {
                    'description': 'Bold, simplified cartoon style',
                    'characteristics': ['bold_lines', 'flat_colors', 'simplified_shapes']
                },
                'pixel_art': {
                    'description': 'Retro pixel art style',
                    'characteristics': ['pixelated', 'limited_colors', 'sharp_edges']
                },
                'oil_painting': {
                    'description': 'Rich, textured oil painting style',
                    'characteristics': ['thick_texture', 'rich_colors', 'brush_strokes']
                },
                'sketch': {
                    'description': 'Pencil sketch style',
                    'characteristics': ['line_art', 'grayscale', 'hand_drawn']
                },
                'anime': {
                    'description': 'Japanese anime/manga style',
                    'characteristics': ['clean_lines', 'cel_shading', 'vibrant_colors']
                }
            }

            logger.info(f"Neural style transfer initialized on device: {self.device}")

        except Exception as e:
            logger.error(f"Failed to initialize style transfer: {e}")
            raise

    def apply_style(self, content_image_path: str, style_type: str, 
                   output_path: Optional[str] = None, iterations: int = 300) -> Dict[str, Any]:
        """Apply style transfer to content image"""
        try:
            if style_type not in self.available_styles:
                return {
                    'success': False,
                    'error': f"Unsupported style: {style_type}. Available: {list(self.available_styles.keys())}"
                }

            # Load and preprocess content image
            content_image = self._load_image(content_image_path)

            # Apply style-specific processing
            if style_type == 'watercolor':
                stylized_image = self._apply_watercolor_style(content_image)
            elif style_type == 'cartoon':
                stylized_image = self._apply_cartoon_style(content_image)
            elif style_type == 'pixel_art':
                stylized_image = self._apply_pixel_art_style(content_image)
            elif style_type == 'oil_painting':
                stylized_image = self._apply_oil_painting_style(content_image)
            elif style_type == 'sketch':
                stylized_image = self._apply_sketch_style(content_image)
            elif style_type == 'anime':
                stylized_image = self._apply_anime_style(content_image)
            else:
                # Fallback to basic neural style transfer
                stylized_image = self._apply_basic_style_transfer(content_image, iterations)

            # Save result
            if output_path is None:
                base_path = Path(content_image_path)
                output_path = base_path.parent / f"{base_path.stem}_{style_type}{base_path.suffix}"

            self._save_image(stylized_image, str(output_path))

            return {
                'success': True,
                'style_type': style_type,
                'output_path': str(output_path),
                'style_info': self.available_styles[style_type],
                'processing_details': {
                    'iterations': iterations if style_type == 'neural' else 'N/A',
                    'device': str(self.device)
                }
            }

        except Exception as e:
            logger.error(f"Style transfer failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'style_type': style_type
            }

    def _apply_watercolor_style(self, image_tensor: torch.Tensor) -> torch.Tensor:
        """Apply watercolor painting effect"""
        # Convert to numpy for OpenCV processing
        image_np = self._tensor_to_numpy(image_tensor)

        # Apply bilateral filter for smooth color regions
        smooth = cv2.bilateralFilter(image_np, 15, 80, 80)

        # Create edge mask
        gray = cv2.cvtColor(smooth, cv2.COLOR_RGB2GRAY)
        # Convert to uint8 for adaptiveThreshold
        gray_uint8 = (gray * 255).astype(np.uint8)
        edges = cv2.adaptiveThreshold(gray_uint8, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 7, 7)
        edges = cv2.cvtColor(edges, cv2.COLOR_GRAY2RGB)
        edges = edges / 255.0

        # Blend with original for watercolor effect
        watercolor = smooth * 0.8 + image_np * 0.2
        watercolor = watercolor * edges

        # Add slight blur for soft edges
        watercolor = cv2.GaussianBlur(watercolor, (3, 3), 0)

        return self._numpy_to_tensor(watercolor)

    def _apply_cartoon_style(self, image_tensor: torch.Tensor) -> torch.Tensor:
        """Apply cartoon/animation effect"""
        image_np = self._tensor_to_numpy(image_tensor)

        # Reduce colors using K-means clustering
        data = image_np.reshape((-1, 3))
        data = np.float32(data)

        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
        _, labels, centers = cv2.kmeans(data, 8, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)

        # Convert back to uint8 and reshape
        centers = np.uint8(centers)
        cartoon_data = centers[labels.flatten()]
        cartoon = cartoon_data.reshape(image_np.shape)

        # Create edge mask
        gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
        gray_blur = cv2.medianBlur(gray, 5)
        # Convert to uint8 for adaptiveThreshold
        gray_blur_uint8 = (gray_blur * 255).astype(np.uint8)
        edges = cv2.adaptiveThreshold(gray_blur_uint8, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 7, 7)
        edges = cv2.cvtColor(edges, cv2.COLOR_GRAY2RGB)

        # Combine cartoon colors with edges
        cartoon = cv2.bitwise_and(cartoon, edges)

        return self._numpy_to_tensor(cartoon / 255.0)

    def _apply_pixel_art_style(self, image_tensor: torch.Tensor) -> torch.Tensor:
        """Apply pixel art effect"""
        image_np = self._tensor_to_numpy(image_tensor)

        # Downscale image
        height, width = image_np.shape[:2]
        small_height, small_width = height // 8, width // 8

        # Resize down and then up for pixelation
        small = cv2.resize(image_np, (small_width, small_height), interpolation=cv2.INTER_LINEAR)
        pixelated = cv2.resize(small, (width, height), interpolation=cv2.INTER_NEAREST)

        # Reduce color palette
        data = pixelated.reshape((-1, 3))
        data = np.float32(data)

        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
        _, labels, centers = cv2.kmeans(data, 16, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)

        centers = np.uint8(centers)
        pixel_data = centers[labels.flatten()]
        pixel_art = pixel_data.reshape(pixelated.shape)

        return self._numpy_to_tensor(pixel_art / 255.0)

    def _apply_oil_painting_style(self, image_tensor: torch.Tensor) -> torch.Tensor:
        """Apply oil painting effect"""
        image_np = self._tensor_to_numpy(image_tensor)

        # Convert to uint8 for OpenCV
        image_uint8 = (image_np * 255).astype(np.uint8)

        # Apply oil painting effect using OpenCV
        oil_painting = cv2.xphoto.oilPainting(image_uint8, 7, 1)

        # Add texture using noise
        noise = np.random.normal(0, 0.02, image_np.shape)
        textured = oil_painting / 255.0 + noise
        textured = np.clip(textured, 0, 1)

        return self._numpy_to_tensor(textured)

    def _apply_sketch_style(self, image_tensor: torch.Tensor) -> torch.Tensor:
        """Apply pencil sketch effect"""
        image_np = self._tensor_to_numpy(image_tensor)

        # Convert to grayscale
        gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)

        # Invert the image
        inverted = 1.0 - gray

        # Apply Gaussian blur
        blurred = cv2.GaussianBlur(inverted, (21, 21), 0)

        # Invert the blurred image
        inverted_blur = 1.0 - blurred

        # Create sketch by dividing
        sketch = gray / inverted_blur
        sketch = np.clip(sketch, 0, 1)

        # Convert back to RGB
        sketch_rgb = cv2.cvtColor(sketch, cv2.COLOR_GRAY2RGB)

        return self._numpy_to_tensor(sketch_rgb)

    def _apply_anime_style(self, image_tensor: torch.Tensor) -> torch.Tensor:
        """Apply anime/manga style effect"""
        image_np = self._tensor_to_numpy(image_tensor)

        # Smooth the image
        smooth = cv2.bilateralFilter(image_np, 15, 80, 80)

        # Create edge mask
        gray = cv2.cvtColor(smooth, cv2.COLOR_RGB2GRAY)
        # Convert to uint8 for adaptiveThreshold
        gray_uint8 = (gray * 255).astype(np.uint8)
        edges = cv2.adaptiveThreshold(gray_uint8, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 7, 7)
        edges = cv2.cvtColor(edges, cv2.COLOR_GRAY2RGB)
        edges = edges / 255.0

        # Enhance colors (anime-like saturation)
        hsv = cv2.cvtColor(smooth, cv2.COLOR_RGB2HSV)
        hsv[:, :, 1] = hsv[:, :, 1] * 1.3  # Increase saturation
        enhanced = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
        enhanced = np.clip(enhanced, 0, 1)

        # Combine with edges
        anime = enhanced * edges

        return self._numpy_to_tensor(anime)

    def _apply_basic_style_transfer(self, content_image: torch.Tensor, iterations: int) -> torch.Tensor:
        """Apply basic neural style transfer (placeholder for full implementation)"""
        # This is a simplified version - full neural style transfer would require style images
        # For now, apply a basic artistic filter
        image_np = self._tensor_to_numpy(content_image)

        # Apply artistic filter
        artistic = cv2.bilateralFilter(image_np, 20, 80, 80)
        artistic = cv2.edgePreservingFilter(artistic, flags=1, sigma_s=50, sigma_r=0.4)

        return self._numpy_to_tensor(artistic)

    def _load_image(self, image_path: str) -> torch.Tensor:
        """Load and preprocess image"""
        image = Image.open(image_path).convert('RGB')
        return self.transform(image).unsqueeze(0).to(self.device)

    def _save_image(self, tensor: torch.Tensor, path: str):
        """Save tensor as image"""
        # Denormalize and convert to PIL
        image = tensor.cpu().clone()
        image = image.squeeze(0)
        image = self.denormalize(image)
        image = torch.clamp(image, 0, 1)

        # Convert to PIL and save
        to_pil = transforms.ToPILImage()
        pil_image = to_pil(image)
        pil_image.save(path)

    def _tensor_to_numpy(self, tensor: torch.Tensor) -> np.ndarray:
        """Convert tensor to numpy array for OpenCV processing"""
        image = tensor.cpu().clone().squeeze(0)
        image = self.denormalize(image)
        image = torch.clamp(image, 0, 1)
        image = image.permute(1, 2, 0).numpy()
        return image

    def _numpy_to_tensor(self, array: np.ndarray) -> torch.Tensor:
        """Convert numpy array back to tensor"""
        # Ensure array is in correct format
        if array.dtype != np.float32:
            array = array.astype(np.float32)

        # Convert to tensor and normalize
        tensor = torch.from_numpy(array).permute(2, 0, 1).unsqueeze(0)

        # Apply normalization
        normalize = transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                                       std=[0.229, 0.224, 0.225])
        tensor = normalize(tensor)

        return tensor.to(self.device)

    def get_available_styles(self) -> Dict[str, Any]:
        """Get list of available styles with descriptions"""
        return self.available_styles

    def batch_apply_styles(self, image_path: str, styles: list, output_dir: str) -> Dict[str, Any]:
        """Apply multiple styles to the same image"""
        results = {}
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        for style in styles:
            if style in self.available_styles:
                output_file = output_path / f"{Path(image_path).stem}_{style}.jpg"
                result = self.apply_style(image_path, style, str(output_file))
                results[style] = result
            else:
                results[style] = {
                    'success': False,
                    'error': f"Unsupported style: {style}"
                }

        return {
            'batch_results': results,
            'total_processed': len([r for r in results.values() if r.get('success', False)]),
            'total_failed': len([r for r in results.values() if not r.get('success', False)])
        }
