import { useState, useCallback } from 'react'
import { styleClient, StylePreviewResponse, StyleApplyResponse } from '../services/styleClient'

interface UseStyleTransferOptions {
  onPreviewComplete?: (result: StylePreviewResponse) => void
  onApplyComplete?: (result: StyleApplyResponse) => void
  onError?: (error: Error) => void
}

export const useStyleTransfer = (options: UseStyleTransferOptions = {}) => {
  const [isGeneratingPreview, setIsGeneratingPreview] = useState(false)
  const [isApplyingStyle, setIsApplyingStyle] = useState(false)
  const [previewResults, setPreviewResults] = useState<Record<string, string>>({})
  const [appliedStyleUrl, setAppliedStyleUrl] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const generatePreview = useCallback(async (file: File, styleType: string) => {
    setIsGeneratingPreview(true)
    setError(null)
    
    try {
      const validation = styleClient.validateImageFile(file)
      if (!validation.isValid) {
        throw new Error(validation.error)
      }

      // 이미지 리사이즈 (미리보기용)
      const resizedFile = await styleClient.resizeImage(file, 512, 512)
      const result = await styleClient.generatePreview(resizedFile, styleType)
      
      setPreviewResults(prev => ({
        ...prev,
        [styleType]: result.preview_url
      }))
      
      options.onPreviewComplete?.(result)
    } catch (err) {
      const error = err as Error
      setError(error.message)
      options.onError?.(error)
    } finally {
      setIsGeneratingPreview(false)
    }
  }, [options])

  const applyStyle = useCallback(async (file: File, styleType: string, iterations: number = 300) => {
    setIsApplyingStyle(true)
    setError(null)
    
    try {
      const validation = styleClient.validateImageFile(file)
      if (!validation.isValid) {
        throw new Error(validation.error)
      }

      const result = await styleClient.applyStyle(file, styleType, iterations)
      setAppliedStyleUrl(result.styled_image_url)
      
      options.onApplyComplete?.(result)
      return result
    } catch (err) {
      const error = err as Error
      setError(error.message)
      options.onError?.(error)
      throw error
    } finally {
      setIsApplyingStyle(false)
    }
  }, [options])

  const clearResults = useCallback(() => {
    setPreviewResults({})
    setAppliedStyleUrl(null)
    setError(null)
  }, [])

  return {
    generatePreview,
    applyStyle,
    clearResults,
    isGeneratingPreview,
    isApplyingStyle,
    previewResults,
    appliedStyleUrl,
    error
  }
}