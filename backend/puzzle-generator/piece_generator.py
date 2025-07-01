import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFilter
import math
import random
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PieceShape(Enum):
    CLASSIC = "classic"
    ORGANIC = "organic"
    GEOMETRIC = "geometric"
    IRREGULAR = "irregular"
    CURVED = "curved"

class EdgeType(Enum):
    FLAT = "flat"
    TAB = "tab"
    BLANK = "blank"
    CURVED_TAB = "curved_tab"
    CURVED_BLANK = "curved_blank"

@dataclass
class PieceEdge:
    edge_type: EdgeType
    position: str  # 'top', 'right', 'bottom', 'left'
    curve_points: Optional[List[Tuple[float, float]]] = None
    tab_size: float = 0.3  # Relative to piece size
    curve_intensity: float = 0.5

@dataclass
class PieceGeometry:
    width: int
    height: int
    center: Tuple[int, int]
    edges: Dict[str, PieceEdge]
    shape_points: List[Tuple[float, float]]
    complexity_score: float

class AdvancedPieceGenerator:
    def __init__(self):
        """Initialize advanced puzzle piece generator"""
        self.shape_generators = {
            PieceShape.CLASSIC: self._generate_classic_shape,
            PieceShape.ORGANIC: self._generate_organic_shape,
            PieceShape.GEOMETRIC: self._generate_geometric_shape,
            PieceShape.IRREGULAR: self._generate_irregular_shape,
            PieceShape.CURVED: self._generate_curved_shape
        }
        
        # Golden ratio for aesthetically pleasing proportions
        self.golden_ratio = (1 + math.sqrt(5)) / 2
        
        # Noise generators for organic shapes
        self.noise_scale = 0.1
        self.noise_octaves = 4
        
        logger.info("Advanced Piece Generator initialized")

    def generate_puzzle_pieces(self, image: np.ndarray, grid_rows: int, grid_cols: int,
                             shape_type: PieceShape = PieceShape.CLASSIC,
                             difficulty_level: str = "medium",
                             allow_rotation: bool = True) -> List[Dict[str, Any]]:
        """Generate puzzle pieces with advanced algorithms"""
        try:
            height, width = image.shape[:2]
            piece_width = width // grid_cols
            piece_height = height // grid_rows
            
            pieces = []
            edge_compatibility_map = self._create_edge_compatibility_map(grid_rows, grid_cols)
            
            for row in range(grid_rows):
                for col in range(grid_cols):
                    piece_id = row * grid_cols + col
                    
                    # Calculate piece boundaries
                    x1 = col * piece_width
                    y1 = row * piece_height
                    x2 = min(x1 + piece_width, width)
                    y2 = min(y1 + piece_height, height)
                    
                    # Extract piece image
                    piece_image = image[y1:y2, x1:x2]
                    
                    # Generate piece geometry
                    piece_geometry = self._generate_piece_geometry(
                        piece_width, piece_height, row, col, grid_rows, grid_cols,
                        shape_type, edge_compatibility_map
                    )
                    
                    # Create piece mask
                    piece_mask = self._create_piece_mask(piece_geometry)
                    
                    # Calculate piece properties
                    piece_properties = self._calculate_piece_properties(
                        piece_image, piece_mask, piece_geometry, difficulty_level
                    )
                    
                    # Generate connection points
                    connection_points = self._generate_connection_points(piece_geometry)
                    
                    piece_data = {
                        'id': f"piece_{piece_id}",
                        'grid_position': {'row': row, 'col': col},
                        'bbox': [x1, y1, x2, y2],
                        'center': [(x1 + x2) // 2, (y1 + y2) // 2],
                        'geometry': {
                            'width': piece_geometry.width,
                            'height': piece_geometry.height,
                            'shape_type': shape_type.value,
                            'shape_points': piece_geometry.shape_points,
                            'complexity_score': piece_geometry.complexity_score
                        },
                        'edges': {
                            pos: {
                                'type': edge.edge_type.value,
                                'tab_size': edge.tab_size,
                                'curve_points': edge.curve_points,
                                'curve_intensity': edge.curve_intensity
                            }
                            for pos, edge in piece_geometry.edges.items()
                        },
                        'mask': piece_mask.tolist(),
                        'properties': piece_properties,
                        'connection_points': connection_points,
                        'rotation_allowed': allow_rotation,
                        'difficulty_indicators': self._calculate_difficulty_indicators(
                            piece_image, piece_geometry, row, col, grid_rows, grid_cols
                        )
                    }
                    
                    pieces.append(piece_data)
            
            # Post-process pieces for better connectivity
            pieces = self._optimize_piece_connectivity(pieces, grid_rows, grid_cols)
            
            return pieces
            
        except Exception as e:
            logger.error(f"Piece generation failed: {e}")
            return []

    def _create_edge_compatibility_map(self, rows: int, cols: int) -> Dict[Tuple[int, int], Dict[str, EdgeType]]:
        """Create a map ensuring compatible edges between adjacent pieces"""
        edge_map = {}
        
        for row in range(rows):
            for col in range(cols):
                edges = {}
                
                # Top edge
                if row == 0:
                    edges['top'] = EdgeType.FLAT
                else:
                    # Get complementary edge from piece above
                    above_pos = (row - 1, col)
                    if above_pos in edge_map:
                        above_bottom = edge_map[above_pos]['bottom']
                        edges['top'] = self._get_complementary_edge(above_bottom)
                    else:
                        edges['top'] = random.choice([EdgeType.TAB, EdgeType.BLANK])
                
                # Right edge
                if col == cols - 1:
                    edges['right'] = EdgeType.FLAT
                else:
                    edges['right'] = random.choice([EdgeType.TAB, EdgeType.BLANK, EdgeType.CURVED_TAB, EdgeType.CURVED_BLANK])
                
                # Bottom edge
                if row == rows - 1:
                    edges['bottom'] = EdgeType.FLAT
                else:
                    edges['bottom'] = random.choice([EdgeType.TAB, EdgeType.BLANK, EdgeType.CURVED_TAB, EdgeType.CURVED_BLANK])
                
                # Left edge
                if col == 0:
                    edges['left'] = EdgeType.FLAT
                else:
                    # Get complementary edge from piece to the left
                    left_pos = (row, col - 1)
                    if left_pos in edge_map:
                        left_right = edge_map[left_pos]['right']
                        edges['left'] = self._get_complementary_edge(left_right)
                    else:
                        edges['left'] = random.choice([EdgeType.TAB, EdgeType.BLANK])
                
                edge_map[(row, col)] = edges
        
        return edge_map

    def _get_complementary_edge(self, edge_type: EdgeType) -> EdgeType:
        """Get the complementary edge type for connection"""
        complementary_map = {
            EdgeType.TAB: EdgeType.BLANK,
            EdgeType.BLANK: EdgeType.TAB,
            EdgeType.CURVED_TAB: EdgeType.CURVED_BLANK,
            EdgeType.CURVED_BLANK: EdgeType.CURVED_TAB,
            EdgeType.FLAT: EdgeType.FLAT
        }
        return complementary_map.get(edge_type, EdgeType.FLAT)

    def _generate_piece_geometry(self, width: int, height: int, row: int, col: int,
                               total_rows: int, total_cols: int, shape_type: PieceShape,
                               edge_map: Dict[Tuple[int, int], Dict[str, EdgeType]]) -> PieceGeometry:
        """Generate piece geometry based on shape type"""
        center = (width // 2, height // 2)
        
        # Get edge types from compatibility map
        edge_types = edge_map.get((row, col), {
            'top': EdgeType.FLAT,
            'right': EdgeType.FLAT,
            'bottom': EdgeType.FLAT,
            'left': EdgeType.FLAT
        })
        
        # Create piece edges
        edges = {}
        for position, edge_type in edge_types.items():
            edges[position] = PieceEdge(
                edge_type=edge_type,
                position=position,
                tab_size=random.uniform(0.2, 0.4),
                curve_intensity=random.uniform(0.3, 0.7)
            )
        
        # Generate shape points using the appropriate generator
        shape_generator = self.shape_generators.get(shape_type, self._generate_classic_shape)
        shape_points = shape_generator(width, height, edges)
        
        # Calculate complexity score
        complexity_score = self._calculate_shape_complexity(shape_points, edges)
        
        return PieceGeometry(
            width=width,
            height=height,
            center=center,
            edges=edges,
            shape_points=shape_points,
            complexity_score=complexity_score
        )

    def _generate_classic_shape(self, width: int, height: int, 
                              edges: Dict[str, PieceEdge]) -> List[Tuple[float, float]]:
        """Generate classic jigsaw puzzle piece shape"""
        points = []
        
        # Start from top-left corner
        current_x, current_y = 0, 0
        
        # Top edge
        top_edge = edges.get('top', PieceEdge(EdgeType.FLAT, 'top'))
        points.extend(self._generate_edge_points(
            (0, 0), (width, 0), top_edge, 'horizontal'
        ))
        
        # Right edge
        right_edge = edges.get('right', PieceEdge(EdgeType.FLAT, 'right'))
        points.extend(self._generate_edge_points(
            (width, 0), (width, height), right_edge, 'vertical'
        ))
        
        # Bottom edge (reverse direction)
        bottom_edge = edges.get('bottom', PieceEdge(EdgeType.FLAT, 'bottom'))
        points.extend(self._generate_edge_points(
            (width, height), (0, height), bottom_edge, 'horizontal', reverse=True
        ))
        
        # Left edge (reverse direction)
        left_edge = edges.get('left', PieceEdge(EdgeType.FLAT, 'left'))
        points.extend(self._generate_edge_points(
            (0, height), (0, 0), left_edge, 'vertical', reverse=True
        ))
        
        return points

    def _generate_organic_shape(self, width: int, height: int,
                              edges: Dict[str, PieceEdge]) -> List[Tuple[float, float]]:
        """Generate organic, natural-looking piece shape"""
        # Start with classic shape
        base_points = self._generate_classic_shape(width, height, edges)
        
        # Add organic variations using Perlin noise simulation
        organic_points = []
        for i, (x, y) in enumerate(base_points):
            # Add noise-based displacement
            noise_x = self._simple_noise(i * 0.1, 0) * width * 0.05
            noise_y = self._simple_noise(0, i * 0.1) * height * 0.05
            
            # Ensure points stay within reasonable bounds
            new_x = max(0, min(width, x + noise_x))
            new_y = max(0, min(height, y + noise_y))
            
            organic_points.append((new_x, new_y))
        
        return organic_points

    def _generate_geometric_shape(self, width: int, height: int,
                                edges: Dict[str, PieceEdge]) -> List[Tuple[float, float]]:
        """Generate geometric puzzle piece with angular features"""
        points = []
        
        # Create more angular, geometric variations
        for edge_pos in ['top', 'right', 'bottom', 'left']:
            edge = edges.get(edge_pos, PieceEdge(EdgeType.FLAT, edge_pos))
            
            if edge_pos == 'top':
                start, end = (0, 0), (width, 0)
            elif edge_pos == 'right':
                start, end = (width, 0), (width, height)
            elif edge_pos == 'bottom':
                start, end = (width, height), (0, height)
            else:  # left
                start, end = (0, height), (0, 0)
            
            edge_points = self._generate_geometric_edge_points(start, end, edge)
            points.extend(edge_points)
        
        return points

    def _generate_irregular_shape(self, width: int, height: int,
                                edges: Dict[str, PieceEdge]) -> List[Tuple[float, float]]:
        """Generate irregular, asymmetric piece shape"""
        # Start with base shape and add irregular variations
        base_points = self._generate_classic_shape(width, height, edges)
        
        irregular_points = []
        for i, (x, y) in enumerate(base_points):
            # Add random but controlled irregularities
            irregularity_factor = 0.1
            random_x = random.uniform(-irregularity_factor, irregularity_factor) * width
            random_y = random.uniform(-irregularity_factor, irregularity_factor) * height
            
            new_x = max(0, min(width, x + random_x))
            new_y = max(0, min(height, y + random_y))
            
            irregular_points.append((new_x, new_y))
        
        return irregular_points

    def _generate_curved_shape(self, width: int, height: int,
                             edges: Dict[str, PieceEdge]) -> List[Tuple[float, float]]:
        """Generate piece with smooth, curved edges"""
        points = []
        
        # Generate smooth curves for each edge
        for edge_pos in ['top', 'right', 'bottom', 'left']:
            edge = edges.get(edge_pos, PieceEdge(EdgeType.FLAT, edge_pos))
            
            if edge_pos == 'top':
                start, end = (0, 0), (width, 0)
            elif edge_pos == 'right':
                start, end = (width, 0), (width, height)
            elif edge_pos == 'bottom':
                start, end = (width, height), (0, height)
            else:  # left
                start, end = (0, height), (0, 0)
            
            curved_points = self._generate_curved_edge_points(start, end, edge)
            points.extend(curved_points)
        
        return points

    def _generate_edge_points(self, start: Tuple[float, float], end: Tuple[float, float],
                            edge: PieceEdge, direction: str, reverse: bool = False) -> List[Tuple[float, float]]:
        """Generate points for a specific edge"""
        points = []
        
        if edge.edge_type == EdgeType.FLAT:
            # Simple straight line
            if not reverse:
                points = [start, end]
            else:
                points = [end, start]
        
        elif edge.edge_type in [EdgeType.TAB, EdgeType.BLANK]:
            # Generate tab or blank
            points = self._generate_tab_blank_points(start, end, edge, direction, reverse)
        
        elif edge.edge_type in [EdgeType.CURVED_TAB, EdgeType.CURVED_BLANK]:
            # Generate curved tab or blank
            points = self._generate_curved_tab_blank_points(start, end, edge, direction, reverse)
        
        return points

    def _generate_tab_blank_points(self, start: Tuple[float, float], end: Tuple[float, float],
                                 edge: PieceEdge, direction: str, reverse: bool = False) -> List[Tuple[float, float]]:
        """Generate points for tab or blank edge"""
        points = []
        
        # Calculate edge parameters
        if direction == 'horizontal':
            edge_length = abs(end[0] - start[0])
            is_vertical_tab = True
        else:
            edge_length = abs(end[1] - start[1])
            is_vertical_tab = False
        
        tab_size = edge.tab_size * edge_length
        
        # Calculate tab/blank position (center of edge)
        mid_point = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
        
        if not reverse:
            points.append(start)
        else:
            points.append(end)
        
        # Generate tab/blank geometry
        if is_vertical_tab:
            # Horizontal edge, vertical tab/blank
            tab_direction = 1 if edge.edge_type == EdgeType.TAB else -1
            
            # Points for the tab/blank
            tab_start_x = mid_point[0] - tab_size / 2
            tab_end_x = mid_point[0] + tab_size / 2
            tab_y = start[1] + tab_direction * tab_size
            
            if not reverse:
                points.extend([
                    (tab_start_x, start[1]),
                    (tab_start_x, tab_y),
                    (tab_end_x, tab_y),
                    (tab_end_x, start[1]),
                    end
                ])
            else:
                points.extend([
                    (tab_end_x, start[1]),
                    (tab_end_x, tab_y),
                    (tab_start_x, tab_y),
                    (tab_start_x, start[1]),
                    start
                ])
        else:
            # Vertical edge, horizontal tab/blank
            tab_direction = 1 if edge.edge_type == EdgeType.TAB else -1
            
            tab_start_y = mid_point[1] - tab_size / 2
            tab_end_y = mid_point[1] + tab_size / 2
            tab_x = start[0] + tab_direction * tab_size
            
            if not reverse:
                points.extend([
                    (start[0], tab_start_y),
                    (tab_x, tab_start_y),
                    (tab_x, tab_end_y),
                    (start[0], tab_end_y),
                    end
                ])
            else:
                points.extend([
                    (start[0], tab_end_y),
                    (tab_x, tab_end_y),
                    (tab_x, tab_start_y),
                    (start[0], tab_start_y),
                    start
                ])
        
        return points

    def _generate_curved_tab_blank_points(self, start: Tuple[float, float], end: Tuple[float, float],
                                        edge: PieceEdge, direction: str, reverse: bool = False) -> List[Tuple[float, float]]:
        """Generate points for curved tab or blank edge"""
        points = []
        
        # Generate smooth curved tab/blank using Bezier curves
        num_points = 20  # Number of points for smooth curve
        
        if direction == 'horizontal':
            edge_length = abs(end[0] - start[0])
        else:
            edge_length = abs(end[1] - start[1])
        
        tab_size = edge.tab_size * edge_length
        curve_intensity = edge.curve_intensity
        
        # Generate Bezier curve points
        for i in range(num_points + 1):
            t = i / num_points
            
            if direction == 'horizontal':
                x = start[0] + t * (end[0] - start[0])
                
                # Create curved tab/blank
                if 0.3 <= t <= 0.7:  # Tab/blank region
                    tab_factor = math.sin((t - 0.3) / 0.4 * math.pi)
                    tab_direction = 1 if edge.edge_type == EdgeType.CURVED_TAB else -1
                    y = start[1] + tab_direction * tab_size * tab_factor * curve_intensity
                else:
                    y = start[1]
                
                points.append((x, y))
            else:
                y = start[1] + t * (end[1] - start[1])
                
                if 0.3 <= t <= 0.7:  # Tab/blank region
                    tab_factor = math.sin((t - 0.3) / 0.4 * math.pi)
                    tab_direction = 1 if edge.edge_type == EdgeType.CURVED_TAB else -1
                    x = start[0] + tab_direction * tab_size * tab_factor * curve_intensity
                else:
                    x = start[0]
                
                points.append((x, y))
        
        if reverse:
            points.reverse()
        
        return points

    def _generate_geometric_edge_points(self, start: Tuple[float, float], end: Tuple[float, float],
                                      edge: PieceEdge) -> List[Tuple[float, float]]:
        """Generate geometric edge points with angular features"""
        points = [start]
        
        if edge.edge_type != EdgeType.FLAT:
            # Add angular geometric features
            mid_point = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
            
            # Create angular tab/blank
            if start[0] == end[0]:  # Vertical edge
                offset = edge.tab_size * abs(end[1] - start[1])
                direction = 1 if edge.edge_type in [EdgeType.TAB, EdgeType.CURVED_TAB] else -1
                
                points.extend([
                    (start[0], mid_point[1] - offset/3),
                    (start[0] + direction * offset, mid_point[1] - offset/3),
                    (start[0] + direction * offset, mid_point[1] + offset/3),
                    (start[0], mid_point[1] + offset/3)
                ])
            else:  # Horizontal edge
                offset = edge.tab_size * abs(end[0] - start[0])
                direction = 1 if edge.edge_type in [EdgeType.TAB, EdgeType.CURVED_TAB] else -1
                
                points.extend([
                    (mid_point[0] - offset/3, start[1]),
                    (mid_point[0] - offset/3, start[1] + direction * offset),
                    (mid_point[0] + offset/3, start[1] + direction * offset),
                    (mid_point[0] + offset/3, start[1])
                ])
        
        points.append(end)
        return points

    def _generate_curved_edge_points(self, start: Tuple[float, float], end: Tuple[float, float],
                                   edge: PieceEdge) -> List[Tuple[float, float]]:
        """Generate smooth curved edge points"""
        points = []
        num_points = 15
        
        for i in range(num_points + 1):
            t = i / num_points
            
            # Linear interpolation for base
            x = start[0] + t * (end[0] - start[0])
            y = start[1] + t * (end[1] - start[1])
            
            # Add smooth curve variation
            if edge.edge_type != EdgeType.FLAT:
                curve_factor = math.sin(t * math.pi) * edge.curve_intensity
                
                if start[0] == end[0]:  # Vertical edge
                    direction = 1 if edge.edge_type in [EdgeType.CURVED_TAB, EdgeType.TAB] else -1
                    x += direction * edge.tab_size * abs(end[1] - start[1]) * curve_factor
                else:  # Horizontal edge
                    direction = 1 if edge.edge_type in [EdgeType.CURVED_TAB, EdgeType.TAB] else -1
                    y += direction * edge.tab_size * abs(end[0] - start[0]) * curve_factor
            
            points.append((x, y))
        
        return points

    def _create_piece_mask(self, geometry: PieceGeometry) -> np.ndarray:
        """Create binary mask for the piece shape"""
        mask = np.zeros((geometry.height, geometry.width), dtype=np.uint8)
        
        # Convert shape points to integer coordinates
        points = [(int(x), int(y)) for x, y in geometry.shape_points]
        
        # Create polygon mask
        cv2.fillPoly(mask, [np.array(points)], 255)
        
        return mask

    def _calculate_piece_properties(self, piece_image: np.ndarray, piece_mask: np.ndarray,
                                  geometry: PieceGeometry, difficulty_level: str) -> Dict[str, Any]:
        """Calculate various properties of the puzzle piece"""
        # Color analysis
        masked_image = cv2.bitwise_and(piece_image, piece_image, mask=piece_mask)
        dominant_colors = self._extract_dominant_colors(masked_image, piece_mask)
        
        # Texture analysis
        texture_features = self._analyze_texture(masked_image, piece_mask)
        
        # Edge analysis
        edge_complexity = self._analyze_edge_complexity(piece_mask)
        
        # Visual distinctiveness
        distinctiveness = self._calculate_visual_distinctiveness(masked_image, piece_mask)
        
        return {
            'dominant_colors': dominant_colors,
            'texture_features': texture_features,
            'edge_complexity': edge_complexity,
            'visual_distinctiveness': distinctiveness,
            'area': int(np.sum(piece_mask > 0)),
            'perimeter': self._calculate_perimeter(piece_mask),
            'compactness': self._calculate_compactness(piece_mask),
            'difficulty_score': self._calculate_piece_difficulty_score(
                edge_complexity, texture_features, distinctiveness, difficulty_level
            )
        }

    def _extract_dominant_colors(self, image: np.ndarray, mask: np.ndarray, k: int = 3) -> List[List[int]]:
        """Extract dominant colors from masked image"""
        # Get pixels within mask
        masked_pixels = image[mask > 0]
        
        if len(masked_pixels) == 0:
            return [[0, 0, 0]]
        
        # Reshape for k-means
        data = masked_pixels.reshape((-1, 3))
        data = np.float32(data)
        
        # Apply k-means clustering
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
        _, labels, centers = cv2.kmeans(data, k, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
        
        centers = np.uint8(centers)
        return centers.tolist()

    def _analyze_texture(self, image: np.ndarray, mask: np.ndarray) -> Dict[str, float]:
        """Analyze texture features of the piece"""
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image
        
        # Apply mask
        masked_gray = cv2.bitwise_and(gray, gray, mask=mask)
        
        # Calculate texture features
        contrast = float(np.std(masked_gray[mask > 0])) if np.any(mask > 0) else 0.0
        
        # Local Binary Pattern approximation
        laplacian_var = float(cv2.Laplacian(masked_gray, cv2.CV_64F).var())
        
        # Gradient magnitude
        grad_x = cv2.Sobel(masked_gray, cv2.CV_64F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(masked_gray, cv2.CV_64F, 0, 1, ksize=3)
        gradient_magnitude = np.sqrt(grad_x**2 + grad_y**2)
        avg_gradient = float(np.mean(gradient_magnitude[mask > 0])) if np.any(mask > 0) else 0.0
        
        return {
            'contrast': contrast,
            'laplacian_variance': laplacian_var,
            'average_gradient': avg_gradient,
            'texture_energy': contrast * laplacian_var / 1000.0 if laplacian_var > 0 else 0.0
        }

    def _analyze_edge_complexity(self, mask: np.ndarray) -> Dict[str, float]:
        """Analyze complexity of piece edges"""
        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return {'perimeter': 0.0, 'area': 0.0, 'complexity_ratio': 0.0}
        
        # Get the largest contour (main piece outline)
        main_contour = max(contours, key=cv2.contourArea)
        
        perimeter = cv2.arcLength(main_contour, True)
        area = cv2.contourArea(main_contour)
        
        # Calculate complexity ratio (higher = more complex edge)
        complexity_ratio = perimeter / (2 * math.sqrt(math.pi * area)) if area > 0 else 0.0
        
        return {
            'perimeter': float(perimeter),
            'area': float(area),
            'complexity_ratio': float(complexity_ratio)
        }

    def _calculate_visual_distinctiveness(self, image: np.ndarray, mask: np.ndarray) -> float:
        """Calculate how visually distinctive the piece is"""
        if not np.any(mask > 0):
            return 0.0
        
        # Calculate color variance
        masked_pixels = image[mask > 0]
        color_variance = np.var(masked_pixels, axis=0).mean()
        
        # Calculate edge density
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image
        
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges[mask > 0] > 0) / np.sum(mask > 0)
        
        # Combine metrics
        distinctiveness = (color_variance / 255.0 + edge_density) / 2.0
        
        return float(distinctiveness)

    def _calculate_perimeter(self, mask: np.ndarray) -> float:
        """Calculate perimeter of the piece"""
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            return float(cv2.arcLength(contours[0], True))
        return 0.0

    def _calculate_compactness(self, mask: np.ndarray) -> float:
        """Calculate compactness (circularity) of the piece"""
        area = np.sum(mask > 0)
        perimeter = self._calculate_perimeter(mask)
        
        if perimeter > 0:
            compactness = 4 * math.pi * area / (perimeter ** 2)
            return float(compactness)
        return 0.0

    def _calculate_piece_difficulty_score(self, edge_complexity: Dict[str, float],
                                        texture_features: Dict[str, float],
                                        distinctiveness: float, difficulty_level: str) -> float:
        """Calculate overall difficulty score for the piece"""
        # Base difficulty from edge complexity
        edge_score = min(edge_complexity.get('complexity_ratio', 0.0) / 2.0, 1.0)
        
        # Texture difficulty
        texture_score = min(texture_features.get('texture_energy', 0.0) / 100.0, 1.0)
        
        # Visual distinctiveness (inverse - less distinctive = harder)
        distinctiveness_score = 1.0 - min(distinctiveness, 1.0)
        
        # Combine scores
        base_score = (edge_score + texture_score + distinctiveness_score) / 3.0
        
        # Adjust for target difficulty level
        difficulty_multipliers = {
            'easy': 0.5,
            'medium': 1.0,
            'hard': 1.5,
            'expert': 2.0
        }
        
        multiplier = difficulty_multipliers.get(difficulty_level, 1.0)
        final_score = min(base_score * multiplier, 1.0)
        
        return float(final_score)

    def _generate_connection_points(self, geometry: PieceGeometry) -> Dict[str, List[Tuple[float, float]]]:
        """Generate connection points for piece edges"""
        connection_points = {}
        
        for position, edge in geometry.edges.items():
            if edge.edge_type in [EdgeType.TAB, EdgeType.CURVED_TAB]:
                # Tab pieces have connection points at the tab
                if position in ['top', 'bottom']:
                    connection_points[position] = [(geometry.width / 2, 0 if position == 'top' else geometry.height)]
                else:  # left, right
                    connection_points[position] = [(0 if position == 'left' else geometry.width, geometry.height / 2)]
            elif edge.edge_type in [EdgeType.BLANK, EdgeType.CURVED_BLANK]:
                # Blank pieces have connection points at the blank area
                if position in ['top', 'bottom']:
                    connection_points[position] = [(geometry.width / 2, 0 if position == 'top' else geometry.height)]
                else:  # left, right
                    connection_points[position] = [(0 if position == 'left' else geometry.width, geometry.height / 2)]
        
        return connection_points

    def _calculate_difficulty_indicators(self, image: np.ndarray, geometry: PieceGeometry,
                                       row: int, col: int, total_rows: int, total_cols: int) -> Dict[str, Any]:
        """Calculate various difficulty indicators for the piece"""
        # Position-based difficulty
        is_corner = (row == 0 or row == total_rows - 1) and (col == 0 or col == total_cols - 1)
        is_edge = (row == 0 or row == total_rows - 1 or col == 0 or col == total_cols - 1) and not is_corner
        is_interior = not is_corner and not is_edge
        
        position_difficulty = {
            'corner': 0.2,  # Easiest
            'edge': 0.5,    # Medium
            'interior': 0.8  # Hardest
        }
        
        if is_corner:
            pos_diff = position_difficulty['corner']
        elif is_edge:
            pos_diff = position_difficulty['edge']
        else:
            pos_diff = position_difficulty['interior']
        
        # Shape complexity
        shape_difficulty = geometry.complexity_score
        
        # Color uniformity (more uniform = harder)
        color_variance = np.var(image, axis=(0, 1)).mean()
        color_difficulty = 1.0 - min(color_variance / 255.0, 1.0)
        
        return {
            'position_type': 'corner' if is_corner else 'edge' if is_edge else 'interior',
            'position_difficulty': float(pos_diff),
            'shape_difficulty': float(shape_difficulty),
            'color_difficulty': float(color_difficulty),
            'overall_difficulty': float((pos_diff + shape_difficulty + color_difficulty) / 3.0)
        }

    def _calculate_shape_complexity(self, shape_points: List[Tuple[float, float]],
                                  edges: Dict[str, PieceEdge]) -> float:
        """Calculate complexity score for the piece shape"""
        if len(shape_points) < 3:
            return 0.0
        
        # Calculate perimeter and area
        perimeter = 0.0
        area = 0.0
        
        for i in range(len(shape_points)):
            x1, y1 = shape_points[i]
            x2, y2 = shape_points[(i + 1) % len(shape_points)]
            
            # Add to perimeter
            perimeter += math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
            
            # Add to area (shoelace formula)
            area += x1 * y2 - x2 * y1
        
        area = abs(area) / 2.0
        
        # Calculate complexity ratio
        if area > 0:
            complexity = perimeter / (2 * math.sqrt(math.pi * area))
        else:
            complexity = 0.0
        
        # Add edge complexity bonus
        edge_bonus = 0.0
        for edge in edges.values():
            if edge.edge_type in [EdgeType.TAB, EdgeType.BLANK]:
                edge_bonus += 0.1
            elif edge.edge_type in [EdgeType.CURVED_TAB, EdgeType.CURVED_BLANK]:
                edge_bonus += 0.2
        
        return min(complexity + edge_bonus, 2.0)

    def _optimize_piece_connectivity(self, pieces: List[Dict[str, Any]], 
                                   rows: int, cols: int) -> List[Dict[str, Any]]:
        """Optimize piece connectivity and ensure proper fitting"""
        # Create adjacency map
        adjacency_map = {}
        
        for piece in pieces:
            row = piece['grid_position']['row']
            col = piece['grid_position']['col']
            adjacency_map[(row, col)] = piece
        
        # Optimize connections
        for piece in pieces:
            row = piece['grid_position']['row']
            col = piece['grid_position']['col']
            
            # Check and optimize connections with adjacent pieces
            adjacent_positions = [
                (row - 1, col, 'top', 'bottom'),    # Above
                (row + 1, col, 'bottom', 'top'),    # Below
                (row, col - 1, 'left', 'right'),    # Left
                (row, col + 1, 'right', 'left')     # Right
            ]
            
            for adj_row, adj_col, my_edge, their_edge in adjacent_positions:
                if (adj_row, adj_col) in adjacency_map:
                    adjacent_piece = adjacency_map[(adj_row, adj_col)]
                    
                    # Ensure complementary edges
                    my_edge_type = piece['edges'][my_edge]['type']
                    their_edge_type = adjacent_piece['edges'][their_edge]['type']
                    
                    # Add connection metadata
                    if 'connections' not in piece:
                        piece['connections'] = {}
                    
                    piece['connections'][my_edge] = {
                        'connected_piece_id': adjacent_piece['id'],
                        'connection_strength': self._calculate_connection_strength(
                            my_edge_type, their_edge_type
                        )
                    }
        
        return pieces

    def _calculate_connection_strength(self, edge_type1: str, edge_type2: str) -> float:
        """Calculate connection strength between two edge types"""
        compatible_pairs = {
            ('tab', 'blank'): 1.0,
            ('blank', 'tab'): 1.0,
            ('curved_tab', 'curved_blank'): 0.9,
            ('curved_blank', 'curved_tab'): 0.9,
            ('flat', 'flat'): 0.8
        }
        
        return compatible_pairs.get((edge_type1, edge_type2), 0.0)

    def _simple_noise(self, x: float, y: float) -> float:
        """Simple noise function for organic shape generation"""
        # Simple pseudo-random noise based on coordinates
        return math.sin(x * 12.9898 + y * 78.233) * 43758.5453 % 1.0 - 0.5

    def generate_piece_preview(self, piece_data: Dict[str, Any], size: Tuple[int, int] = (100, 100)) -> np.ndarray:
        """Generate a preview image of the puzzle piece"""
        width, height = size
        preview = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Scale shape points to preview size
        original_width = piece_data['geometry']['width']
        original_height = piece_data['geometry']['height']
        
        scale_x = width / original_width
        scale_y = height / original_height
        
        scaled_points = []
        for x, y in piece_data['geometry']['shape_points']:
            scaled_x = int(x * scale_x)
            scaled_y = int(y * scale_y)
            scaled_points.append((scaled_x, scaled_y))
        
        # Draw piece outline
        cv2.fillPoly(preview, [np.array(scaled_points)], (200, 200, 200))
        cv2.polylines(preview, [np.array(scaled_points)], True, (0, 0, 0), 2)
        
        # Add edge type indicators
        edge_colors = {
            'flat': (100, 100, 100),
            'tab': (0, 255, 0),
            'blank': (255, 0, 0),
            'curved_tab': (0, 255, 255),
            'curved_blank': (255, 0, 255)
        }
        
        for position, edge_info in piece_data['edges'].items():
            color = edge_colors.get(edge_info['type'], (128, 128, 128))
            
            # Draw edge indicator
            if position == 'top':
                cv2.circle(preview, (width // 2, 5), 3, color, -1)
            elif position == 'right':
                cv2.circle(preview, (width - 5, height // 2), 3, color, -1)
            elif position == 'bottom':
                cv2.circle(preview, (width // 2, height - 5), 3, color, -1)
            elif position == 'left':
                cv2.circle(preview, (5, height // 2), 3, color, -1)
        
        return preview