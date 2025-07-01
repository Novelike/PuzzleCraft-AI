"""
PuzzleCraft AI - 난이도 분석 시스템
지능형 퍼즐 난이도 분석 및 자동 조정 시스템
"""

import numpy as np
import cv2
from PIL import Image
import math
import logging
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ComplexityMetric(Enum):
    """복잡도 측정 지표"""
    EDGE_DENSITY = "edge_density"
    COLOR_VARIANCE = "color_variance"
    TEXTURE_COMPLEXITY = "texture_complexity"
    PATTERN_FREQUENCY = "pattern_frequency"
    CONTRAST_RATIO = "contrast_ratio"
    DETAIL_LEVEL = "detail_level"


class DifficultyFactor(Enum):
    """난이도 영향 요소"""
    PIECE_COUNT = "piece_count"
    PIECE_SHAPE = "piece_shape"
    COLOR_SIMILARITY = "color_similarity"
    EDGE_COMPLEXITY = "edge_complexity"
    PATTERN_REPETITION = "pattern_repetition"
    SIZE_VARIATION = "size_variation"


@dataclass
class ComplexityAnalysis:
    """이미지 복잡도 분석 결과"""
    overall_score: float
    edge_density: float
    color_variance: float
    texture_complexity: float
    pattern_frequency: float
    contrast_ratio: float
    detail_level: float
    dominant_colors: List[Tuple[int, int, int]]
    complexity_map: np.ndarray
    recommendations: Dict[str, Any]


@dataclass
class DifficultyProfile:
    """퍼즐 난이도 프로필"""
    difficulty_score: float
    recommended_piece_count: int
    estimated_solve_time: int  # minutes
    skill_level: str  # beginner, intermediate, advanced, expert
    challenge_factors: List[str]
    accessibility_score: float
    adaptive_hints: List[str]


class IntelligentDifficultyAnalyzer:
    """지능형 난이도 분석기"""
    
    def __init__(self):
        """초기화"""
        self.complexity_weights = {
            ComplexityMetric.EDGE_DENSITY: 0.20,
            ComplexityMetric.COLOR_VARIANCE: 0.15,
            ComplexityMetric.TEXTURE_COMPLEXITY: 0.20,
            ComplexityMetric.PATTERN_FREQUENCY: 0.15,
            ComplexityMetric.CONTRAST_RATIO: 0.15,
            ComplexityMetric.DETAIL_LEVEL: 0.15
        }
        
        self.difficulty_thresholds = {
            'beginner': (0.0, 0.3),
            'intermediate': (0.3, 0.6),
            'advanced': (0.6, 0.8),
            'expert': (0.8, 1.0)
        }
        
        self.piece_count_ranges = {
            'beginner': (12, 50),
            'intermediate': (50, 150),
            'advanced': (150, 500),
            'expert': (500, 2000)
        }
        
        logger.info("지능형 난이도 분석기 초기화 완료")

    async def analyze_image_complexity(self, image_path: str) -> ComplexityAnalysis:
        """이미지 복잡도 종합 분석"""
        try:
            # 이미지 로드
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"이미지를 로드할 수 없습니다: {image_path}")
            
            # 각 복잡도 지표 계산
            edge_density = self._calculate_edge_density(image)
            color_variance = self._calculate_color_variance(image)
            texture_complexity = self._calculate_texture_complexity(image)
            pattern_frequency = self._calculate_pattern_frequency(image)
            contrast_ratio = self._calculate_contrast_ratio(image)
            detail_level = self._calculate_detail_level(image)
            
            # 전체 복잡도 점수 계산
            overall_score = (
                edge_density * self.complexity_weights[ComplexityMetric.EDGE_DENSITY] +
                color_variance * self.complexity_weights[ComplexityMetric.COLOR_VARIANCE] +
                texture_complexity * self.complexity_weights[ComplexityMetric.TEXTURE_COMPLEXITY] +
                pattern_frequency * self.complexity_weights[ComplexityMetric.PATTERN_FREQUENCY] +
                contrast_ratio * self.complexity_weights[ComplexityMetric.CONTRAST_RATIO] +
                detail_level * self.complexity_weights[ComplexityMetric.DETAIL_LEVEL]
            )
            
            # 주요 색상 추출
            dominant_colors = self._extract_dominant_colors(image)
            
            # 복잡도 맵 생성
            complexity_map = self._generate_complexity_map(image)
            
            # 추천사항 생성
            recommendations = self._generate_complexity_recommendations(
                overall_score, edge_density, color_variance, texture_complexity
            )
            
            return ComplexityAnalysis(
                overall_score=overall_score,
                edge_density=edge_density,
                color_variance=color_variance,
                texture_complexity=texture_complexity,
                pattern_frequency=pattern_frequency,
                contrast_ratio=contrast_ratio,
                detail_level=detail_level,
                dominant_colors=dominant_colors,
                complexity_map=complexity_map,
                recommendations=recommendations
            )
            
        except Exception as e:
            logger.error(f"이미지 복잡도 분석 실패: {str(e)}")
            raise

    def _calculate_edge_density(self, image: np.ndarray) -> float:
        """엣지 밀도 계산"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        edge_pixels = np.sum(edges > 0)
        total_pixels = edges.shape[0] * edges.shape[1]
        return edge_pixels / total_pixels

    def _calculate_color_variance(self, image: np.ndarray) -> float:
        """색상 분산 계산"""
        # LAB 색공간으로 변환하여 더 정확한 색상 분석
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        
        # 각 채널의 분산 계산
        l_var = np.var(lab[:, :, 0])
        a_var = np.var(lab[:, :, 1])
        b_var = np.var(lab[:, :, 2])
        
        # 정규화된 색상 분산
        total_variance = (l_var + a_var + b_var) / 3
        return min(total_variance / 10000, 1.0)  # 0-1 범위로 정규화

    def _calculate_texture_complexity(self, image: np.ndarray) -> float:
        """텍스처 복잡도 계산 (LBP 기반)"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Local Binary Pattern 계산
        def lbp(image, radius=1, n_points=8):
            h, w = image.shape
            lbp_image = np.zeros((h, w), dtype=np.uint8)
            
            for i in range(radius, h - radius):
                for j in range(radius, w - radius):
                    center = image[i, j]
                    binary_string = ""
                    
                    for k in range(n_points):
                        angle = 2 * np.pi * k / n_points
                        x = int(i + radius * np.cos(angle))
                        y = int(j + radius * np.sin(angle))
                        
                        if 0 <= x < h and 0 <= y < w:
                            binary_string += "1" if image[x, y] >= center else "0"
                    
                    lbp_image[i, j] = int(binary_string, 2) if binary_string else 0
            
            return lbp_image
        
        lbp_image = lbp(gray)
        texture_variance = np.var(lbp_image)
        return min(texture_variance / 10000, 1.0)

    def _calculate_pattern_frequency(self, image: np.ndarray) -> float:
        """패턴 빈도 계산 (FFT 기반)"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # FFT 변환
        f_transform = np.fft.fft2(gray)
        f_shift = np.fft.fftshift(f_transform)
        magnitude_spectrum = np.log(np.abs(f_shift) + 1)
        
        # 고주파 성분 비율 계산
        h, w = magnitude_spectrum.shape
        center_h, center_w = h // 2, w // 2
        
        # 중심에서 거리별 주파수 성분 분석
        high_freq_mask = np.zeros((h, w))
        for i in range(h):
            for j in range(w):
                distance = np.sqrt((i - center_h)**2 + (j - center_w)**2)
                if distance > min(h, w) * 0.3:  # 고주파 영역
                    high_freq_mask[i, j] = 1
        
        high_freq_energy = np.sum(magnitude_spectrum * high_freq_mask)
        total_energy = np.sum(magnitude_spectrum)
        
        return high_freq_energy / total_energy if total_energy > 0 else 0

    def _calculate_contrast_ratio(self, image: np.ndarray) -> float:
        """대비 비율 계산"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # RMS 대비 계산
        mean_intensity = np.mean(gray)
        rms_contrast = np.sqrt(np.mean((gray - mean_intensity) ** 2))
        
        # 0-1 범위로 정규화
        return min(rms_contrast / 128, 1.0)

    def _calculate_detail_level(self, image: np.ndarray) -> float:
        """세부사항 수준 계산"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 라플라시안 필터로 세부사항 검출
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        detail_variance = np.var(laplacian)
        
        return min(detail_variance / 100000, 1.0)

    def _extract_dominant_colors(self, image: np.ndarray, k: int = 5) -> List[Tuple[int, int, int]]:
        """주요 색상 추출"""
        # 이미지를 1차원 배열로 변환
        data = image.reshape((-1, 3))
        data = np.float32(data)
        
        # K-means 클러스터링
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
        _, labels, centers = cv2.kmeans(data, k, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
        
        # BGR을 RGB로 변환하고 정수로 변환
        centers = np.uint8(centers)
        dominant_colors = [(int(c[2]), int(c[1]), int(c[0])) for c in centers]
        
        return dominant_colors

    def _generate_complexity_map(self, image: np.ndarray) -> np.ndarray:
        """복잡도 맵 생성"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 여러 복잡도 지표를 결합한 맵 생성
        edges = cv2.Canny(gray, 50, 150)
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        
        # 정규화 및 결합
        edges_norm = edges / 255.0
        laplacian_norm = np.abs(laplacian) / np.max(np.abs(laplacian))
        
        complexity_map = (edges_norm + laplacian_norm) / 2
        return complexity_map

    def _generate_complexity_recommendations(self, overall_score: float, edge_density: float, 
                                           color_variance: float, texture_complexity: float) -> Dict[str, Any]:
        """복잡도 기반 추천사항 생성"""
        recommendations = {
            "suggested_difficulty": self._get_difficulty_level(overall_score),
            "optimization_tips": [],
            "piece_count_range": self._get_recommended_piece_range(overall_score),
            "special_considerations": []
        }
        
        # 구체적인 추천사항 생성
        if edge_density > 0.7:
            recommendations["optimization_tips"].append("높은 엣지 밀도로 인해 조각 경계 구분이 어려울 수 있습니다")
            recommendations["special_considerations"].append("edge_enhancement")
        
        if color_variance < 0.3:
            recommendations["optimization_tips"].append("색상 변화가 적어 단조로울 수 있습니다")
            recommendations["special_considerations"].append("color_enhancement")
        
        if texture_complexity > 0.8:
            recommendations["optimization_tips"].append("복잡한 텍스처로 인해 난이도가 높습니다")
            recommendations["special_considerations"].append("texture_simplification")
        
        return recommendations

    def _get_difficulty_level(self, score: float) -> str:
        """점수 기반 난이도 레벨 결정"""
        for level, (min_score, max_score) in self.difficulty_thresholds.items():
            if min_score <= score < max_score:
                return level
        return 'expert'

    def _get_recommended_piece_range(self, score: float) -> Tuple[int, int]:
        """복잡도 기반 추천 조각 수 범위"""
        difficulty_level = self._get_difficulty_level(score)
        return self.piece_count_ranges[difficulty_level]

    async def generate_difficulty_profile(self, complexity_analysis: ComplexityAnalysis, 
                                        target_audience: str = "general",
                                        accessibility_requirements: List[str] = None) -> DifficultyProfile:
        """난이도 프로필 생성"""
        try:
            # 기본 난이도 점수 계산
            base_difficulty = complexity_analysis.overall_score
            
            # 타겟 오디언스에 따른 조정
            audience_modifier = self._get_audience_modifier(target_audience)
            adjusted_difficulty = min(base_difficulty * audience_modifier, 1.0)
            
            # 추천 조각 수 계산
            recommended_pieces = self._calculate_optimal_piece_count(
                adjusted_difficulty, complexity_analysis
            )
            
            # 예상 해결 시간 계산
            estimated_time = self._estimate_solve_time(
                recommended_pieces, adjusted_difficulty, complexity_analysis
            )
            
            # 스킬 레벨 결정
            skill_level = self._get_difficulty_level(adjusted_difficulty)
            
            # 도전 요소 식별
            challenge_factors = self._identify_challenge_factors(complexity_analysis)
            
            # 접근성 점수 계산
            accessibility_score = self._calculate_accessibility_score(
                complexity_analysis, accessibility_requirements or []
            )
            
            # 적응형 힌트 생성
            adaptive_hints = self._generate_adaptive_hints(
                complexity_analysis, skill_level
            )
            
            return DifficultyProfile(
                difficulty_score=adjusted_difficulty,
                recommended_piece_count=recommended_pieces,
                estimated_solve_time=estimated_time,
                skill_level=skill_level,
                challenge_factors=challenge_factors,
                accessibility_score=accessibility_score,
                adaptive_hints=adaptive_hints
            )
            
        except Exception as e:
            logger.error(f"난이도 프로필 생성 실패: {str(e)}")
            raise

    def _get_audience_modifier(self, target_audience: str) -> float:
        """타겟 오디언스별 난이도 조정 계수"""
        modifiers = {
            "children": 0.6,
            "elderly": 0.7,
            "general": 1.0,
            "enthusiast": 1.2,
            "expert": 1.4
        }
        return modifiers.get(target_audience, 1.0)

    def _calculate_optimal_piece_count(self, difficulty_score: float, 
                                     complexity_analysis: ComplexityAnalysis) -> int:
        """최적 조각 수 계산"""
        base_range = self._get_recommended_piece_range(difficulty_score)
        min_pieces, max_pieces = base_range
        
        # 복잡도 특성에 따른 미세 조정
        adjustment_factor = 1.0
        
        if complexity_analysis.edge_density > 0.7:
            adjustment_factor *= 0.8  # 엣지가 많으면 조각 수 감소
        
        if complexity_analysis.color_variance < 0.3:
            adjustment_factor *= 1.2  # 색상 변화가 적으면 조각 수 증가
        
        if complexity_analysis.texture_complexity > 0.8:
            adjustment_factor *= 0.9  # 텍스처가 복잡하면 조각 수 감소
        
        # 최종 조각 수 계산
        target_pieces = int((min_pieces + max_pieces) / 2 * adjustment_factor)
        return max(min_pieces, min(target_pieces, max_pieces))

    def _estimate_solve_time(self, piece_count: int, difficulty_score: float, 
                           complexity_analysis: ComplexityAnalysis) -> int:
        """예상 해결 시간 계산 (분)"""
        # 기본 시간: 조각당 평균 시간
        base_time_per_piece = {
            'beginner': 2.0,    # 2분/조각
            'intermediate': 1.5, # 1.5분/조각
            'advanced': 1.0,    # 1분/조각
            'expert': 0.8       # 0.8분/조각
        }
        
        skill_level = self._get_difficulty_level(difficulty_score)
        time_per_piece = base_time_per_piece[skill_level]
        
        # 복잡도에 따른 시간 조정
        complexity_multiplier = 1.0 + (difficulty_score * 0.5)
        
        # 특별한 도전 요소에 따른 추가 시간
        if complexity_analysis.edge_density > 0.7:
            complexity_multiplier *= 1.2
        
        if complexity_analysis.color_variance < 0.3:
            complexity_multiplier *= 1.3
        
        total_time = int(piece_count * time_per_piece * complexity_multiplier)
        return max(10, total_time)  # 최소 10분

    def _identify_challenge_factors(self, complexity_analysis: ComplexityAnalysis) -> List[str]:
        """도전 요소 식별"""
        factors = []
        
        if complexity_analysis.edge_density > 0.6:
            factors.append("high_edge_density")
        
        if complexity_analysis.color_variance < 0.4:
            factors.append("low_color_variation")
        
        if complexity_analysis.texture_complexity > 0.7:
            factors.append("complex_texture")
        
        if complexity_analysis.pattern_frequency > 0.6:
            factors.append("repetitive_patterns")
        
        if complexity_analysis.contrast_ratio < 0.3:
            factors.append("low_contrast")
        
        if complexity_analysis.detail_level > 0.8:
            factors.append("high_detail")
        
        return factors

    def _calculate_accessibility_score(self, complexity_analysis: ComplexityAnalysis, 
                                     requirements: List[str]) -> float:
        """접근성 점수 계산"""
        base_score = 1.0
        
        # 시각적 접근성 고려사항
        if "visual_impairment" in requirements:
            if complexity_analysis.contrast_ratio < 0.5:
                base_score *= 0.7  # 낮은 대비는 시각 장애인에게 어려움
            
            if len(complexity_analysis.dominant_colors) < 3:
                base_score *= 0.8  # 색상 다양성 부족
        
        # 인지적 접근성 고려사항
        if "cognitive_accessibility" in requirements:
            if complexity_analysis.pattern_frequency > 0.7:
                base_score *= 0.8  # 복잡한 패턴은 인지 부담 증가
            
            if complexity_analysis.detail_level > 0.8:
                base_score *= 0.7  # 과도한 세부사항
        
        # 운동 능력 접근성 고려사항
        if "motor_accessibility" in requirements:
            # 조각 크기와 관련된 고려사항은 별도 처리
            pass
        
        return max(0.1, base_score)

    def _generate_adaptive_hints(self, complexity_analysis: ComplexityAnalysis, 
                               skill_level: str) -> List[str]:
        """적응형 힌트 생성"""
        hints = []
        
        # 스킬 레벨별 기본 힌트
        if skill_level == "beginner":
            hints.append("모서리 조각부터 시작하세요")
            hints.append("비슷한 색상끼리 그룹화해보세요")
        
        # 복잡도 특성별 특화 힌트
        if complexity_analysis.edge_density > 0.6:
            hints.append("엣지가 복잡하니 색상과 패턴에 집중하세요")
        
        if complexity_analysis.color_variance < 0.4:
            hints.append("색상 변화가 적으니 텍스처와 형태에 주목하세요")
        
        if complexity_analysis.texture_complexity > 0.7:
            hints.append("텍스처 패턴을 활용해 영역을 구분해보세요")
        
        if complexity_analysis.pattern_frequency > 0.6:
            hints.append("반복되는 패턴을 찾아 구조를 파악하세요")
        
        return hints

    async def optimize_difficulty_for_user(self, complexity_analysis: ComplexityAnalysis,
                                         user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """사용자 맞춤 난이도 최적화"""
        try:
            # 사용자 프로필 분석
            skill_level = user_profile.get('skill_level', 'intermediate')
            preferences = user_profile.get('preferences', {})
            accessibility_needs = user_profile.get('accessibility_needs', [])
            
            # 개인화된 난이도 프로필 생성
            difficulty_profile = await self.generate_difficulty_profile(
                complexity_analysis, skill_level, accessibility_needs
            )
            
            # 사용자 선호도에 따른 조정
            optimized_config = {
                'piece_count': difficulty_profile.recommended_piece_count,
                'difficulty_score': difficulty_profile.difficulty_score,
                'estimated_time': difficulty_profile.estimated_solve_time,
                'adaptive_features': []
            }
            
            # 선호도 기반 조정
            if preferences.get('prefer_challenge', False):
                optimized_config['piece_count'] = int(optimized_config['piece_count'] * 1.2)
                optimized_config['adaptive_features'].append('increased_challenge')
            
            if preferences.get('time_limited', False):
                optimized_config['piece_count'] = int(optimized_config['piece_count'] * 0.8)
                optimized_config['adaptive_features'].append('time_optimized')
            
            # 접근성 최적화
            if accessibility_needs:
                optimized_config['accessibility_features'] = self._generate_accessibility_features(
                    accessibility_needs, complexity_analysis
                )
            
            return optimized_config
            
        except Exception as e:
            logger.error(f"사용자 맞춤 난이도 최적화 실패: {str(e)}")
            raise

    def _generate_accessibility_features(self, needs: List[str], 
                                       complexity_analysis: ComplexityAnalysis) -> List[str]:
        """접근성 기능 생성"""
        features = []
        
        if "visual_impairment" in needs:
            features.extend([
                "high_contrast_mode",
                "color_blind_friendly_palette",
                "edge_enhancement"
            ])
            
            if complexity_analysis.contrast_ratio < 0.5:
                features.append("contrast_boost")
        
        if "cognitive_accessibility" in needs:
            features.extend([
                "simplified_interface",
                "progress_indicators",
                "step_by_step_guidance"
            ])
        
        if "motor_accessibility" in needs:
            features.extend([
                "larger_pieces",
                "snap_assistance",
                "gesture_controls"
            ])
        
        return features

    def get_difficulty_statistics(self) -> Dict[str, Any]:
        """난이도 분석 통계 정보"""
        return {
            "complexity_weights": self.complexity_weights,
            "difficulty_thresholds": self.difficulty_thresholds,
            "piece_count_ranges": self.piece_count_ranges,
            "supported_metrics": [metric.value for metric in ComplexityMetric],
            "supported_factors": [factor.value for factor in DifficultyFactor]
        }