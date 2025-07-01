import React, { useState, useEffect } from 'react'
import { 
  Palette, 
  Eye, 
  Sparkles, 
  RefreshCw, 
  Download,
  Zap,
  Brush,
  Image as ImageIcon
} from 'lucide-react'

interface StyleOption {
  id: string
  name: string
  description: string
  previewUrl?: string
  category: 'artistic' | 'photographic' | 'abstract' | 'vintage'
  intensity: 'light' | 'medium' | 'strong'
  processingTime: number // seconds
}

interface StyleSelectorProps {
  selectedStyle: string | null
  onStyleSelect: (styleId: string) => void
  onPreviewRequest: (styleId: string) => void
  onApplyStyle: (styleId: string) => void
  isGeneratingPreview: boolean
  isApplyingStyle: boolean
  previewResults: Record<string, string> // styleId -> preview image URL
  originalImageUrl?: string
}

const STYLE_OPTIONS: StyleOption[] = [
  {
    id: 'original',
    name: '원본',
    description: '스타일 변환 없이 원본 이미지 사용',
    category: 'photographic',
    intensity: 'light',
    processingTime: 0
  },
  {
    id: 'watercolor',
    name: '수채화',
    description: '부드럽고 투명한 수채화 스타일',
    category: 'artistic',
    intensity: 'medium',
    processingTime: 15
  },
  {
    id: 'oil_painting',
    name: '유화',
    description: '진한 색감의 클래식 유화 스타일',
    category: 'artistic',
    intensity: 'strong',
    processingTime: 20
  },
  {
    id: 'sketch',
    name: '스케치',
    description: '연필로 그린 듯한 스케치 스타일',
    category: 'artistic',
    intensity: 'light',
    processingTime: 10
  },
  {
    id: 'cartoon',
    name: '만화',
    description: '밝고 선명한 만화 스타일',
    category: 'artistic',
    intensity: 'medium',
    processingTime: 18
  },
  {
    id: 'pixel_art',
    name: '픽셀 아트',
    description: '레트로 게임 스타일의 픽셀 아트',
    category: 'abstract',
    intensity: 'strong',
    processingTime: 12
  },
  {
    id: 'impressionist',
    name: '인상파',
    description: '모네 스타일의 인상주의 화풍',
    category: 'artistic',
    intensity: 'medium',
    processingTime: 22
  },
  {
    id: 'pop_art',
    name: '팝 아트',
    description: '앤디 워홀 스타일의 팝 아트',
    category: 'abstract',
    intensity: 'strong',
    processingTime: 16
  },
  {
    id: 'vintage',
    name: '빈티지',
    description: '오래된 사진 느낌의 빈티지 스타일',
    category: 'vintage',
    intensity: 'light',
    processingTime: 8
  },
  {
    id: 'cyberpunk',
    name: '사이버펑크',
    description: '네온과 미래적 느낌의 사이버펑크',
    category: 'abstract',
    intensity: 'strong',
    processingTime: 25
  }
]

export const StyleSelector: React.FC<StyleSelectorProps> = ({
  selectedStyle,
  onStyleSelect,
  onPreviewRequest,
  onApplyStyle,
  isGeneratingPreview,
  isApplyingStyle,
  previewResults,
  originalImageUrl
}) => {
  const [selectedCategory, setSelectedCategory] = useState<string>('all')
  const [previewingStyle, setPreviewingStyle] = useState<string | null>(null)

  const categories = [
    { id: 'all', name: '전체', icon: <Palette className="h-4 w-4" /> },
    { id: 'artistic', name: '예술적', icon: <Brush className="h-4 w-4" /> },
    { id: 'photographic', name: '사진', icon: <ImageIcon className="h-4 w-4" /> },
    { id: 'abstract', name: '추상적', icon: <Sparkles className="h-4 w-4" /> },
    { id: 'vintage', name: '빈티지', icon: <Eye className="h-4 w-4" /> }
  ]

  const filteredStyles = selectedCategory === 'all' 
    ? STYLE_OPTIONS 
    : STYLE_OPTIONS.filter(style => style.category === selectedCategory)

  const handlePreviewRequest = (styleId: string) => {
    setPreviewingStyle(styleId)
    onPreviewRequest(styleId)
  }

  useEffect(() => {
    if (!isGeneratingPreview) {
      setPreviewingStyle(null)
    }
  }, [isGeneratingPreview])

  const getIntensityColor = (intensity: string) => {
    switch (intensity) {
      case 'light': return 'text-green-600 bg-green-100'
      case 'medium': return 'text-yellow-600 bg-yellow-100'
      case 'strong': return 'text-red-600 bg-red-100'
      default: return 'text-gray-600 bg-gray-100'
    }
  }

  const getIntensityText = (intensity: string) => {
    switch (intensity) {
      case 'light': return '약함'
      case 'medium': return '보통'
      case 'strong': return '강함'
      default: return '알 수 없음'
    }
  }

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-purple-100 rounded-lg">
            <Palette className="h-6 w-6 text-purple-600" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900">스타일 선택</h3>
            <p className="text-sm text-gray-600">
              AI 스타일 변환으로 퍼즐에 예술적 효과를 적용하세요
            </p>
          </div>
        </div>

        {selectedStyle && selectedStyle !== 'original' && (
          <button
            onClick={() => onApplyStyle(selectedStyle)}
            disabled={isApplyingStyle}
            className="btn-primary flex items-center space-x-2 disabled:opacity-50"
          >
            {isApplyingStyle ? (
              <>
                <RefreshCw className="h-4 w-4 animate-spin" />
                <span>적용 중...</span>
              </>
            ) : (
              <>
                <Zap className="h-4 w-4" />
                <span>스타일 적용</span>
              </>
            )}
          </button>
        )}
      </div>

      {/* 카테고리 필터 */}
      <div className="flex space-x-2 overflow-x-auto pb-2">
        {categories.map(category => (
          <button
            key={category.id}
            onClick={() => setSelectedCategory(category.id)}
            className={`
              flex items-center space-x-2 px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-colors
              ${selectedCategory === category.id
                ? 'bg-purple-100 text-purple-700 border border-purple-200'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }
            `}
          >
            {category.icon}
            <span>{category.name}</span>
          </button>
        ))}
      </div>

      {/* 스타일 그리드 */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {filteredStyles.map(style => (
          <div
            key={style.id}
            className={`
              relative border-2 rounded-lg overflow-hidden cursor-pointer transition-all duration-200
              ${selectedStyle === style.id
                ? 'border-purple-500 ring-2 ring-purple-200'
                : 'border-gray-200 hover:border-gray-300'
              }
            `}
            onClick={() => onStyleSelect(style.id)}
          >
            {/* 미리보기 이미지 */}
            <div className="aspect-square bg-gray-100 relative">
              {previewResults[style.id] ? (
                <img
                  src={previewResults[style.id]}
                  alt={style.name}
                  className="w-full h-full object-cover"
                />
              ) : originalImageUrl && style.id !== 'original' ? (
                <div className="w-full h-full flex items-center justify-center bg-gray-50">
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      handlePreviewRequest(style.id)
                    }}
                    disabled={isGeneratingPreview}
                    className="btn-secondary text-xs flex items-center space-x-1 disabled:opacity-50"
                  >
                    {previewingStyle === style.id ? (
                      <>
                        <RefreshCw className="h-3 w-3 animate-spin" />
                        <span>생성 중</span>
                      </>
                    ) : (
                      <>
                        <Eye className="h-3 w-3" />
                        <span>미리보기</span>
                      </>
                    )}
                  </button>
                </div>
              ) : style.id === 'original' && originalImageUrl ? (
                <img
                  src={originalImageUrl}
                  alt="원본"
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center">
                  <Palette className="h-8 w-8 text-gray-400" />
                </div>
              )}

              {/* 선택 표시 */}
              {selectedStyle === style.id && (
                <div className="absolute top-2 right-2 bg-purple-500 text-white rounded-full p-1">
                  <Sparkles className="h-3 w-3" />
                </div>
              )}

              {/* 처리 시간 표시 */}
              {style.processingTime > 0 && (
                <div className="absolute bottom-2 left-2 bg-black bg-opacity-60 text-white text-xs px-2 py-1 rounded">
                  ~{style.processingTime}초
                </div>
              )}
            </div>

            {/* 스타일 정보 */}
            <div className="p-3">
              <div className="flex items-center justify-between mb-1">
                <h4 className="font-medium text-gray-900 text-sm">{style.name}</h4>
                <span className={`text-xs px-2 py-1 rounded-full ${getIntensityColor(style.intensity)}`}>
                  {getIntensityText(style.intensity)}
                </span>
              </div>
              <p className="text-xs text-gray-600 line-clamp-2">{style.description}</p>
            </div>
          </div>
        ))}
      </div>

      {/* 선택된 스타일 정보 */}
      {selectedStyle && (
        <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
          <div className="flex items-start space-x-3">
            <Sparkles className="h-5 w-5 text-purple-600 mt-0.5" />
            <div className="flex-1">
              <h4 className="font-medium text-purple-900 mb-1">
                선택된 스타일: {STYLE_OPTIONS.find(s => s.id === selectedStyle)?.name}
              </h4>
              <p className="text-sm text-purple-700 mb-3">
                {STYLE_OPTIONS.find(s => s.id === selectedStyle)?.description}
              </p>
              
              <div className="flex items-center space-x-4 text-xs text-purple-600">
                <div className="flex items-center space-x-1">
                  <span>강도:</span>
                  <span className="font-medium">
                    {getIntensityText(STYLE_OPTIONS.find(s => s.id === selectedStyle)?.intensity || 'light')}
                  </span>
                </div>
                <div className="flex items-center space-x-1">
                  <span>예상 처리 시간:</span>
                  <span className="font-medium">
                    {STYLE_OPTIONS.find(s => s.id === selectedStyle)?.processingTime || 0}초
                  </span>
                </div>
              </div>

              {/* 미리보기 다운로드 */}
              {previewResults[selectedStyle] && (
                <div className="mt-3">
                  <a
                    href={previewResults[selectedStyle]}
                    download={`preview_${selectedStyle}.jpg`}
                    className="btn-outline text-xs flex items-center space-x-1 w-fit"
                  >
                    <Download className="h-3 w-3" />
                    <span>미리보기 다운로드</span>
                  </a>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* 도움말 */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-start space-x-3">
          <Eye className="h-5 w-5 text-blue-600 mt-0.5" />
          <div>
            <h4 className="font-medium text-blue-900 mb-1">스타일 변환 팁</h4>
            <ul className="text-sm text-blue-700 space-y-1">
              <li>• 미리보기를 통해 스타일 효과를 확인한 후 적용하세요</li>
              <li>• 복잡한 이미지일수록 스타일 변환 시간이 더 오래 걸립니다</li>
              <li>• 원본 이미지의 해상도가 높을수록 더 좋은 결과를 얻을 수 있습니다</li>
              <li>• 강도가 높은 스타일은 퍼즐 난이도에 영향을 줄 수 있습니다</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}