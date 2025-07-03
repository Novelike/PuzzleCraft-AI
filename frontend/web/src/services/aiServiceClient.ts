/**
 * PuzzleCraft AI - AI 서비스 클라이언트
 * 백엔드 AI 서비스와의 통신을 담당하는 클라이언트
 */

interface APIResponse<T = any> {
  success: boolean
  data?: T
  error?: string
  message?: string
}

interface ComplexityAnalysisResult {
  file_id: string
  filename: string
  analysis: {
    overall_score: number
    edge_density: number
    color_variance: number
    texture_complexity: number
    pattern_frequency: number
    contrast_ratio: number
    detail_level: number
    dominant_colors: [number, number, number][]
    recommendations: {
      suggested_difficulty: string
      optimization_tips: string[]
      piece_count_range: [number, number]
      special_considerations: string[]
    }
  }
  timestamp: string
}

interface DifficultyProfile {
  difficulty_score: number
  recommended_piece_count: number
  estimated_solve_time: number
  skill_level: string
  challenge_factors: string[]
  accessibility_score: number
  adaptive_hints: string[]
  timestamp: string
}

interface PuzzleGenerationRequest {
  puzzle_type?: string
  difficulty?: string
  piece_count?: number
  piece_shape?: string
  target_audience?: string
  accessibility_requirements?: string[]
  style_type?: string
  styled_image_url?: string
  enable_ai_optimization?: boolean
  custom_settings?: Record<string, any>
}

interface PuzzleTaskStatus {
  task_id: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress: number
  current_step: string
  estimated_time_remaining?: number
  created_at: string
  updated_at: string
  error_message?: string
}

interface PuzzleGenerationResult {
  puzzle_id: string
  filename: string
  puzzle_data: any
  complexity_analysis: any
  difficulty_profile: any
  generation_config: any
  created_at: string
}

interface UserProfile {
  skill_level: string
  preferences: Record<string, any>
  accessibility_needs: string[]
  puzzle_history: any[]
}

class AIServiceClient {
  private baseURL: string
  private apiKey?: string

  constructor() {
    // 환경변수에서 API 설정 로드
    this.baseURL = import.meta.env.VITE_PUZZLE_GENERATOR_URL || 'http://localhost:8004'
    this.apiKey = import.meta.env.VITE_API_KEY
  }

  private async makeRequest<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<APIResponse<T>> {
    try {
      const url = `${this.baseURL}${endpoint}`
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        ...(options.headers as Record<string, string>),
      }

      if (this.apiKey) {
        headers['Authorization'] = `Bearer ${this.apiKey}`
      }

      const response = await fetch(url, {
        ...options,
        headers,
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`)
      }

      const data = await response.json()
      return {
        success: true,
        data,
      }
    } catch (error) {
      console.error(`API 요청 실패 [${endpoint}]:`, error)
      return {
        success: false,
        error: error instanceof Error ? error.message : '알 수 없는 오류가 발생했습니다',
      }
    }
  }

  private async makeFormRequest<T>(
    endpoint: string,
    formData: FormData,
    options: RequestInit = {}
  ): Promise<APIResponse<T>> {
    try {
      const url = `${this.baseURL}${endpoint}`
      const headers: Record<string, string> = {
        ...(options.headers as Record<string, string>),
      }

      if (this.apiKey) {
        headers['Authorization'] = `Bearer ${this.apiKey}`
      }

      const response = await fetch(url, {
        method: 'POST',
        ...options,
        headers,
        body: formData,
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`)
      }

      const data = await response.json()
      return {
        success: true,
        data,
      }
    } catch (error) {
      console.error(`API 요청 실패 [${endpoint}]:`, error)
      return {
        success: false,
        error: error instanceof Error ? error.message : '알 수 없는 오류가 발생했습니다',
      }
    }
  }

  /**
   * 서비스 상태 확인
   */
  async healthCheck(): Promise<APIResponse<any>> {
    return this.makeRequest('/health')
  }

  /**
   * 이미지 복잡도 분석
   */
  async analyzeImageComplexity(file: File): Promise<APIResponse<ComplexityAnalysisResult>> {
    const formData = new FormData()
    formData.append('file', file)

    return this.makeFormRequest('/analyze/complexity', formData)
  }

  /**
   * 난이도 프로필 생성
   */
  async generateDifficultyProfile(
    complexityAnalysis: any,
    targetAudience: string = 'general',
    accessibilityRequirements: string[] = []
  ): Promise<APIResponse<DifficultyProfile>> {
    return this.makeRequest('/analyze/difficulty-profile', {
      method: 'POST',
      body: JSON.stringify({
        complexity_analysis: complexityAnalysis,
        target_audience: targetAudience,
        accessibility_requirements: accessibilityRequirements,
      }),
    })
  }

  /**
   * 지능형 퍼즐 생성 (비동기)
   */
  async generateIntelligentPuzzle(
    file: File,
    request: PuzzleGenerationRequest = {}
  ): Promise<APIResponse<{ task_id: string; status: string; message: string; check_status_url: string }>> {
    const formData = new FormData()
    formData.append('file', file)

    if (Object.keys(request).length > 0) {
      formData.append('request', JSON.stringify(request))
    }

    return this.makeFormRequest('/generate-intelligent-puzzle', formData)
  }

  /**
   * 퍼즐 생성 상태 확인
   */
  async getPuzzleStatus(taskId: string): Promise<APIResponse<PuzzleTaskStatus>> {
    return this.makeRequest(`/status/${taskId}`)
  }

  /**
   * 퍼즐 생성 결과 조회
   */
  async getPuzzleResult(taskId: string): Promise<APIResponse<PuzzleGenerationResult>> {
    return this.makeRequest(`/result/${taskId}`)
  }

  /**
   * 퍼즐 미리보기 생성
   */
  async generatePuzzlePreview(
    file: File,
    pieceCount: number = 50,
    pieceShape: string = 'classic'
  ): Promise<APIResponse<any>> {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('piece_count', pieceCount.toString())
    formData.append('piece_shape', pieceShape)

    return this.makeFormRequest('/preview', formData)
  }

  /**
   * 사용자 맞춤 최적화
   */
  async optimizePuzzleForUser(
    complexityAnalysis: any,
    userProfile: UserProfile
  ): Promise<APIResponse<any>> {
    return this.makeRequest('/optimize-for-user', {
      method: 'POST',
      body: JSON.stringify({
        complexity_analysis: complexityAnalysis,
        user_profile: userProfile,
      }),
    })
  }

  /**
   * AI 서비스 상태 확인
   */
  async getAIServicesStatus(): Promise<APIResponse<any>> {
    return this.makeRequest('/ai-services/status')
  }

  /**
   * 서비스 기능 정보
   */
  async getServiceCapabilities(): Promise<APIResponse<any>> {
    return this.makeRequest('/info/capabilities')
  }

  /**
   * 난이도 분석 통계
   */
  async getDifficultyStatistics(): Promise<APIResponse<any>> {
    return this.makeRequest('/stats/difficulty')
  }

  /**
   * 실시간 상태 업데이트를 위한 폴링
   */
  async pollTaskStatus(
    taskId: string,
    onUpdate: (status: PuzzleTaskStatus) => void,
    onComplete: (result: PuzzleGenerationResult) => void,
    onError: (error: string) => void,
    interval: number = 2000
  ): Promise<() => void> {
    let isPolling = true

    const poll = async () => {
      if (!isPolling) return

      try {
        const statusResponse = await this.getPuzzleStatus(taskId)

        if (!statusResponse.success) {
          onError(statusResponse.error || '상태 확인 실패')
          return
        }

        const status = statusResponse.data!
        onUpdate(status)

        if (status.status === 'completed') {
          isPolling = false

          // 결과 조회
          const resultResponse = await this.getPuzzleResult(taskId)
          if (resultResponse.success) {
            onComplete(resultResponse.data!)
          } else {
            onError(resultResponse.error || '결과 조회 실패')
          }
        } else if (status.status === 'failed') {
          isPolling = false
          onError(status.error_message || '퍼즐 생성 실패')
        } else {
          // 계속 폴링
          setTimeout(poll, interval)
        }
      } catch (error) {
        onError(error instanceof Error ? error.message : '알 수 없는 오류')
      }
    }

    // 첫 번째 폴링 시작
    poll()

    // 폴링 중단 함수 반환
    return () => {
      isPolling = false
    }
  }

  /**
   * 배치 처리를 위한 여러 파일 업로드
   */
  async batchAnalyzeImages(files: File[]): Promise<APIResponse<ComplexityAnalysisResult[]>> {
    try {
      const results = await Promise.all(
        files.map(file => this.analyzeImageComplexity(file))
      )

      const successResults = results
        .filter(result => result.success)
        .map(result => result.data!)

      const errors = results
        .filter(result => !result.success)
        .map(result => result.error)

      if (errors.length > 0) {
        console.warn('일부 이미지 분석 실패:', errors)
      }

      return {
        success: true,
        data: successResults,
      }
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : '배치 처리 실패',
      }
    }
  }

  /**
   * 캐시된 결과 조회 (향후 Redis 연동용)
   */
  async getCachedResult(cacheKey: string): Promise<APIResponse<any>> {
    // 현재는 로컬 스토리지 사용, 향후 Redis로 변경
    try {
      const cached = localStorage.getItem(`puzzle_cache_${cacheKey}`)
      if (cached) {
        const data = JSON.parse(cached)
        const now = Date.now()

        // 1시간 캐시
        if (now - data.timestamp < 3600000) {
          return {
            success: true,
            data: data.result,
          }
        } else {
          localStorage.removeItem(`puzzle_cache_${cacheKey}`)
        }
      }

      return {
        success: false,
        error: '캐시된 결과 없음',
      }
    } catch (error) {
      return {
        success: false,
        error: '캐시 조회 실패',
      }
    }
  }

  /**
   * 결과 캐시 저장
   */
  setCachedResult(cacheKey: string, result: any): void {
    try {
      const cacheData = {
        result,
        timestamp: Date.now(),
      }
      localStorage.setItem(`puzzle_cache_${cacheKey}`, JSON.stringify(cacheData))
    } catch (error) {
      console.warn('캐시 저장 실패:', error)
    }
  }
}

// 싱글톤 인스턴스 생성
export const aiServiceClient = new AIServiceClient()

// 타입 내보내기
export type {
  APIResponse,
  ComplexityAnalysisResult,
  DifficultyProfile,
  PuzzleGenerationRequest,
  PuzzleTaskStatus,
  PuzzleGenerationResult,
  UserProfile,
}
