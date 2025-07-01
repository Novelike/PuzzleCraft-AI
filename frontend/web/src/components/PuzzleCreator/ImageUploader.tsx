import React, { useState, useCallback } from 'react'
import { Upload, X, Eye, Sparkles, AlertCircle } from 'lucide-react'

interface ImageUploaderProps {
  onFileSelect: (file: File) => void
  onAnalysisRequest: (file: File) => void
  selectedFile: File | null
  isAnalyzing: boolean
  analysisResult?: any
}

export const ImageUploader: React.FC<ImageUploaderProps> = ({
  onFileSelect,
  onAnalysisRequest,
  selectedFile,
  isAnalyzing,
  analysisResult
}) => {
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [dragActive, setDragActive] = useState(false)

  const handleFileSelect = useCallback((file: File) => {
    if (file && file.type.startsWith('image/')) {
      onFileSelect(file)
      const url = URL.createObjectURL(file)
      setPreviewUrl(url)
    }
  }, [onFileSelect])

  const handleDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setDragActive(false)
    
    const file = e.dataTransfer.files[0]
    if (file) {
      handleFileSelect(file)
    }
  }, [handleFileSelect])

  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setDragActive(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setDragActive(false)
  }, [])

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      handleFileSelect(file)
    }
  }, [handleFileSelect])

  const clearFile = useCallback(() => {
    onFileSelect(null as any)
    setPreviewUrl(null)
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl)
    }
  }, [onFileSelect, previewUrl])

  const requestAnalysis = useCallback(() => {
    if (selectedFile) {
      onAnalysisRequest(selectedFile)
    }
  }, [selectedFile, onAnalysisRequest])

  return (
    <div className="space-y-4">
      {/* 업로드 영역 */}
      <div
        className={`
          border-2 border-dashed rounded-lg p-8 text-center transition-all duration-200
          ${dragActive 
            ? 'border-blue-400 bg-blue-50' 
            : selectedFile 
              ? 'border-green-300 bg-green-50' 
              : 'border-gray-300 hover:border-gray-400'
          }
        `}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
      >
        {previewUrl ? (
          <div className="space-y-4">
            <div className="relative inline-block">
              <img
                src={previewUrl}
                alt="Preview"
                className="max-w-full max-h-64 mx-auto rounded-lg shadow-sm"
              />
              <button
                onClick={clearFile}
                className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full p-1 hover:bg-red-600 transition-colors"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            
            <div className="space-y-2">
              <p className="text-sm font-medium text-gray-700">{selectedFile?.name}</p>
              <p className="text-xs text-gray-500">
                크기: {selectedFile ? (selectedFile.size / 1024 / 1024).toFixed(2) : 0}MB
              </p>
            </div>

            {/* AI 분석 버튼 */}
            <div className="flex justify-center space-x-3">
              <button
                onClick={requestAnalysis}
                disabled={isAnalyzing}
                className="btn-secondary flex items-center space-x-2 disabled:opacity-50"
              >
                {isAnalyzing ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                    <span>분석 중...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="h-4 w-4" />
                    <span>AI 분석</span>
                  </>
                )}
              </button>
              
              <button
                onClick={clearFile}
                className="btn-outline flex items-center space-x-2"
              >
                <Upload className="h-4 w-4" />
                <span>다른 이미지</span>
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <Upload className={`h-12 w-12 mx-auto ${dragActive ? 'text-blue-500' : 'text-gray-400'}`} />
            <div>
              <p className="text-lg font-medium text-gray-900">
                {dragActive ? '파일을 놓아주세요' : '이미지를 드래그하거나 클릭하여 업로드'}
              </p>
              <p className="text-sm text-gray-600 mt-1">
                JPG, PNG, GIF, WEBP 파일 지원 (최대 50MB)
              </p>
            </div>
            
            <input
              type="file"
              accept="image/*"
              onChange={handleInputChange}
              className="hidden"
              id="file-upload"
            />
            <label htmlFor="file-upload" className="btn-primary cursor-pointer inline-flex items-center space-x-2">
              <Upload className="h-4 w-4" />
              <span>파일 선택</span>
            </label>
          </div>
        )}
      </div>

      {/* 분석 결과 표시 */}
      {analysisResult && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-start space-x-3">
            <Eye className="h-5 w-5 text-blue-600 mt-0.5" />
            <div className="flex-1">
              <h4 className="font-medium text-blue-900 mb-2">AI 분석 결과</h4>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <span className="text-blue-700">복잡도 점수:</span>
                  <span className="ml-2 font-medium">
                    {(analysisResult.analysis?.overall_score * 100).toFixed(1)}%
                  </span>
                </div>
                <div>
                  <span className="text-blue-700">추천 난이도:</span>
                  <span className="ml-2 font-medium capitalize">
                    {analysisResult.analysis?.recommendations?.suggested_difficulty}
                  </span>
                </div>
                <div>
                  <span className="text-blue-700">엣지 밀도:</span>
                  <span className="ml-2 font-medium">
                    {(analysisResult.analysis?.edge_density * 100).toFixed(1)}%
                  </span>
                </div>
                <div>
                  <span className="text-blue-700">색상 다양성:</span>
                  <span className="ml-2 font-medium">
                    {(analysisResult.analysis?.color_variance * 100).toFixed(1)}%
                  </span>
                </div>
              </div>
              
              {analysisResult.analysis?.recommendations?.optimization_tips?.length > 0 && (
                <div className="mt-3">
                  <p className="text-blue-700 font-medium mb-1">최적화 제안:</p>
                  <ul className="text-xs text-blue-600 space-y-1">
                    {analysisResult.analysis.recommendations.optimization_tips.map((tip: string, index: number) => (
                      <li key={index} className="flex items-start space-x-1">
                        <AlertCircle className="h-3 w-3 mt-0.5 flex-shrink-0" />
                        <span>{tip}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}