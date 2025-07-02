import { useState, useCallback, useRef, useEffect } from 'react'
import { 
  aiServiceClient, 
  ComplexityAnalysisResult, 
  DifficultyProfile, 
  PuzzleGenerationRequest,
  PuzzleTaskStatus,
  PuzzleGenerationResult,
  UserProfile
} from '../services/aiServiceClient'

interface AIProcessingStep {
  id: string
  name: string
  description: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress: number
  estimatedTime?: number
  result?: any
  error?: string
}

interface PuzzleGeneratorState {
  // 파일 관련
  selectedFile: File | null
  imageUrl: string | null

  // 분석 결과
  complexityAnalysis: ComplexityAnalysisResult | null
  difficultyProfile: DifficultyProfile | null

  // 생성 설정
  puzzleSettings: PuzzleGenerationRequest

  // 처리 상태
  isAnalyzing: boolean
  isGenerating: boolean
  isGeneratingPreview: boolean

  // 진행 상황
  currentTaskId: string | null
  taskStatus: PuzzleTaskStatus | null
  processingSteps: AIProcessingStep[]
  currentStep: string
  progress: number
  estimatedTimeRemaining?: number

  // 결과
  generationResult: PuzzleGenerationResult | null
  previewData: any

  // 에러
  error: string | null
}

interface UsePuzzleGeneratorOptions {
  userProfile?: UserProfile
  enableCaching?: boolean
  pollingInterval?: number
  onComplete?: (result: PuzzleGenerationResult) => void
  onError?: (error: string) => void
  onProgress?: (progress: number, step: string) => void
}

export const usePuzzleGenerator = (options: UsePuzzleGeneratorOptions = {}) => {
  const {
    userProfile,
    enableCaching = true,
    pollingInterval = 2000,
    onComplete,
    onError,
    onProgress
  } = options

  const [state, setState] = useState<PuzzleGeneratorState>({
    selectedFile: null,
    imageUrl: null,
    complexityAnalysis: null,
    difficultyProfile: null,
    puzzleSettings: {
      puzzle_type: 'classic',
      difficulty: 'medium',
      piece_shape: 'classic',
      target_audience: 'general',
      enable_ai_optimization: true,
    },
    isAnalyzing: false,
    isGenerating: false,
    isGeneratingPreview: false,
    currentTaskId: null,
    taskStatus: null,
    processingSteps: [],
    currentStep: '',
    progress: 0,
    generationResult: null,
    previewData: null,
    error: null,
  })

  const stopPollingRef = useRef<(() => void) | null>(null)

  // 컴포넌트 언마운트 시 폴링 중단
  useEffect(() => {
    return () => {
      if (stopPollingRef.current) {
        stopPollingRef.current()
      }
    }
  }, [])

  // 상태 업데이트 헬퍼
  const updateState = useCallback((updates: Partial<PuzzleGeneratorState>) => {
    setState(prev => ({ ...prev, ...updates }))
  }, [])

  // 에러 처리
  const handleError = useCallback((error: string) => {
    updateState({ error, isAnalyzing: false, isGenerating: false, isGeneratingPreview: false })
    onError?.(error)
  }, [updateState, onError])

  // 파일 선택
  const selectFile = useCallback((file: File | null) => {
    if (file) {
      const imageUrl = URL.createObjectURL(file)
      updateState({
        selectedFile: file,
        imageUrl,
        complexityAnalysis: null,
        difficultyProfile: null,
        generationResult: null,
        previewData: null,
        error: null,
      })
    } else {
      if (state.imageUrl) {
        URL.revokeObjectURL(state.imageUrl)
      }
      updateState({
        selectedFile: null,
        imageUrl: null,
        complexityAnalysis: null,
        difficultyProfile: null,
        generationResult: null,
        previewData: null,
        error: null,
      })
    }
  }, [state.imageUrl, updateState])

  // 이미지 복잡도 분석
  const analyzeComplexity = useCallback(async (file?: File) => {
    const targetFile = file || state.selectedFile
    if (!targetFile) {
      handleError('분석할 파일이 선택되지 않았습니다')
      return
    }

    updateState({ isAnalyzing: true, error: null })

    try {
      // 캐시 확인
      if (enableCaching) {
        const cacheKey = `complexity_${targetFile.name}_${targetFile.size}_${targetFile.lastModified}`
        const cachedResult = await aiServiceClient.getCachedResult(cacheKey)

        if (cachedResult.success) {
          updateState({
            complexityAnalysis: cachedResult.data,
            isAnalyzing: false,
          })
          return cachedResult.data
        }
      }

      const response = await aiServiceClient.analyzeImageComplexity(targetFile)

      if (response.success) {
        const result = response.data!
        updateState({
          complexityAnalysis: result,
          isAnalyzing: false,
        })

        // 캐시 저장
        if (enableCaching) {
          const cacheKey = `complexity_${targetFile.name}_${targetFile.size}_${targetFile.lastModified}`
          aiServiceClient.setCachedResult(cacheKey, result)
        }

        return result
      } else {
        handleError(response.error || '복잡도 분석 실패')
      }
    } catch (error) {
      handleError(error instanceof Error ? error.message : '복잡도 분석 중 오류 발생')
    }
  }, [state.selectedFile, enableCaching, updateState, handleError])

  // 난이도 프로필 생성
  const generateDifficultyProfile = useCallback(async (
    complexityAnalysis?: ComplexityAnalysisResult,
    targetAudience?: string,
    accessibilityRequirements?: string[]
  ) => {
    const analysis = complexityAnalysis || state.complexityAnalysis
    if (!analysis) {
      handleError('복잡도 분석 결과가 필요합니다')
      return
    }

    try {
      const response = await aiServiceClient.generateDifficultyProfile(
        analysis.analysis,
        targetAudience || state.puzzleSettings.target_audience || 'general',
        accessibilityRequirements || state.puzzleSettings.accessibility_requirements || []
      )

      if (response.success) {
        const profile = response.data!
        updateState({ difficultyProfile: profile })
        return profile
      } else {
        handleError(response.error || '난이도 프로필 생성 실패')
      }
    } catch (error) {
      handleError(error instanceof Error ? error.message : '난이도 프로필 생성 중 오류 발생')
    }
  }, [state.complexityAnalysis, state.puzzleSettings, updateState, handleError])

  // 퍼즐 설정 업데이트
  const updatePuzzleSettings = useCallback((settings: Partial<PuzzleGenerationRequest>) => {
    updateState({
      puzzleSettings: { ...state.puzzleSettings, ...settings }
    })
  }, [state.puzzleSettings, updateState])

  // 처리 단계 초기화
  const initializeProcessingSteps = useCallback(() => {
    const steps: AIProcessingStep[] = [
      {
        id: 'complexity_analysis',
        name: '이미지 복잡도 분석',
        description: '이미지의 복잡도와 특성을 분석합니다',
        status: 'pending',
        progress: 0,
        estimatedTime: 30,
      },
      {
        id: 'difficulty_profile',
        name: '난이도 프로필 생성',
        description: '최적의 퍼즐 난이도를 계산합니다',
        status: 'pending',
        progress: 0,
        estimatedTime: 15,
      },
    ]

    if (state.puzzleSettings.enable_ai_optimization) {
      if (state.puzzleSettings.puzzle_type === 'text' || state.puzzleSettings.puzzle_type === 'hybrid') {
        steps.push({
          id: 'ocr_processing',
          name: 'OCR 텍스트 인식',
          description: '이미지에서 텍스트를 추출합니다',
          status: 'pending',
          progress: 0,
          estimatedTime: 45,
        })
      }

      if (state.puzzleSettings.puzzle_type === 'segmentation' || state.puzzleSettings.puzzle_type === 'hybrid') {
        steps.push({
          id: 'segmentation',
          name: '이미지 분할',
          description: '이미지를 의미있는 영역으로 분할합니다',
          status: 'pending',
          progress: 0,
          estimatedTime: 60,
        })
      }

      if (state.puzzleSettings.style_type && state.puzzleSettings.style_type !== 'original') {
        steps.push({
          id: 'style_transfer',
          name: '스타일 변환',
          description: '선택한 스타일로 이미지를 변환합니다',
          status: 'pending',
          progress: 0,
          estimatedTime: 90,
        })
      }
    }

    steps.push({
      id: 'puzzle_generation',
      name: '퍼즐 생성',
      description: '최종 퍼즐 조각을 생성합니다',
      status: 'pending',
      progress: 0,
      estimatedTime: 120,
    })

    updateState({ processingSteps: steps })
    return steps
  }, [state.puzzleSettings, updateState])

  // 퍼즐 생성 시작
  const generatePuzzle = useCallback(async () => {
    if (!state.selectedFile) {
      handleError('파일이 선택되지 않았습니다')
      return
    }

    // 기존 폴링 중단
    if (stopPollingRef.current) {
      stopPollingRef.current()
    }

    updateState({
      isGenerating: true,
      error: null,
      progress: 0,
      currentStep: '퍼즐 생성 시작',
    })

    // 처리 단계 초기화
    const steps = initializeProcessingSteps()

    try {
      // 퍼즐 생성 요청
      const response = await aiServiceClient.generateIntelligentPuzzle(
        state.selectedFile,
        state.puzzleSettings
      )

      if (response.success) {
        const { task_id } = response.data!
        updateState({ currentTaskId: task_id })

        // 실시간 상태 폴링 시작
        const stopPolling = await aiServiceClient.pollTaskStatus(
          task_id,
          (status) => {
            updateState({
              taskStatus: status,
              progress: status.progress,
              currentStep: status.current_step,
              estimatedTimeRemaining: status.estimated_time_remaining,
            })

            // 처리 단계 업데이트
            const updatedSteps = steps.map(step => {
              if (status.current_step.includes(step.name)) {
                return { ...step, status: 'processing' as const, progress: status.progress }
              } else if (status.progress > 0.8 && step.id === 'puzzle_generation') {
                return { ...step, status: 'processing' as const, progress: status.progress }
              }
              return step
            })
            updateState({ processingSteps: updatedSteps })

            onProgress?.(status.progress, status.current_step)
          },
          (result) => {
            updateState({
              generationResult: result,
              isGenerating: false,
              progress: 1,
              currentStep: '완료',
            })

            // 모든 단계 완료 처리
            const completedSteps = steps.map(step => ({
              ...step,
              status: 'completed' as const,
              progress: 1,
            }))
            updateState({ processingSteps: completedSteps })

            onComplete?.(result)
          },
          (error) => {
            handleError(error)

            // 실패한 단계 표시
            const failedSteps = steps.map(step => {
              if (step.status === 'processing') {
                return { ...step, status: 'failed' as const, error }
              }
              return step
            })
            updateState({ processingSteps: failedSteps })
          },
          pollingInterval
        )

        stopPollingRef.current = stopPolling
      } else {
        handleError(response.error || '퍼즐 생성 요청 실패')
      }
    } catch (error) {
      handleError(error instanceof Error ? error.message : '퍼즐 생성 중 오류 발생')
    }
  }, [
    state.selectedFile,
    state.puzzleSettings,
    pollingInterval,
    updateState,
    handleError,
    initializeProcessingSteps,
    onProgress,
    onComplete,
  ])

  // 퍼즐 미리보기 생성
  const generatePreview = useCallback(async (
    pieceCount?: number,
    pieceShape?: string
  ) => {
    if (!state.selectedFile) {
      handleError('파일이 선택되지 않았습니다')
      return
    }

    updateState({ isGeneratingPreview: true, error: null })

    try {
      const response = await aiServiceClient.generatePuzzlePreview(
        state.selectedFile,
        pieceCount || state.puzzleSettings.piece_count || 50,
        pieceShape || state.puzzleSettings.piece_shape || 'classic'
      )

      if (response.success) {
        updateState({
          previewData: response.data,
          isGeneratingPreview: false,
        })
        return response.data
      } else {
        handleError(response.error || '미리보기 생성 실패')
      }
    } catch (error) {
      handleError(error instanceof Error ? error.message : '미리보기 생성 중 오류 발생')
    }
  }, [state.selectedFile, state.puzzleSettings, updateState, handleError])

  // 사용자 맞춤 최적화
  const optimizeForUser = useCallback(async (profile?: UserProfile) => {
    if (!state.complexityAnalysis) {
      handleError('복잡도 분석 결과가 필요합니다')
      return
    }

    const targetProfile = profile || userProfile
    if (!targetProfile) {
      handleError('사용자 프로필이 필요합니다')
      return
    }

    try {
      const response = await aiServiceClient.optimizePuzzleForUser(
        state.complexityAnalysis.analysis,
        targetProfile
      )

      if (response.success) {
        const optimizedConfig = response.data.optimized_config

        // 최적화된 설정 적용
        updatePuzzleSettings({
          piece_count: optimizedConfig.piece_count,
          difficulty: optimizedConfig.difficulty_score > 0.7 ? 'hard' : 
                     optimizedConfig.difficulty_score > 0.4 ? 'medium' : 'easy',
          accessibility_requirements: optimizedConfig.accessibility_features || [],
        })

        return optimizedConfig
      } else {
        handleError(response.error || '사용자 맞춤 최적화 실패')
      }
    } catch (error) {
      handleError(error instanceof Error ? error.message : '최적화 중 오류 발생')
    }
  }, [state.complexityAnalysis, userProfile, updateState, updatePuzzleSettings, handleError])

  // 생성 취소
  const cancelGeneration = useCallback(() => {
    if (stopPollingRef.current) {
      stopPollingRef.current()
      stopPollingRef.current = null
    }

    updateState({
      isGenerating: false,
      currentTaskId: null,
      taskStatus: null,
      progress: 0,
      currentStep: '',
      estimatedTimeRemaining: undefined,
    })
  }, [updateState])

  // 상태 초기화
  const reset = useCallback(() => {
    cancelGeneration()

    if (state.imageUrl) {
      URL.revokeObjectURL(state.imageUrl)
    }

    setState({
      selectedFile: null,
      imageUrl: null,
      complexityAnalysis: null,
      difficultyProfile: null,
      puzzleSettings: {
        puzzle_type: 'classic',
        difficulty: 'medium',
        piece_shape: 'classic',
        target_audience: 'general',
        enable_ai_optimization: true,
      },
      isAnalyzing: false,
      isGenerating: false,
      isGeneratingPreview: false,
      currentTaskId: null,
      taskStatus: null,
      processingSteps: [],
      currentStep: '',
      progress: 0,
      generationResult: null,
      previewData: null,
      error: null,
    })
  }, [cancelGeneration, state.imageUrl])

  return {
    // 상태
    ...state,
    currentFile: state.selectedFile, // selectedFile의 별칭

    // 액션
    selectFile,
    analyzeComplexity,
    generateDifficultyProfile,
    updatePuzzleSettings,
    generatePuzzle,
    generatePreview,
    optimizeForUser,
    cancelGeneration,
    reset,

    // 유틸리티
    isReady: !!state.selectedFile,
    canGenerate: !!state.selectedFile && !state.isGenerating,
    hasAnalysis: !!state.complexityAnalysis,
    hasProfile: !!state.difficultyProfile,
    hasResult: !!state.generationResult,
  }
}

export type { PuzzleGeneratorState, AIProcessingStep, UsePuzzleGeneratorOptions }
