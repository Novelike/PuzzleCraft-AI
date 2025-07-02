const API_BASE_URL = import.meta.env.VITE_API_URL

export interface StyleOption {
  id: string
  name: string
  description: string
}

export interface StylePreviewResponse {
  preview_url: string
  style_type: string
  processing_time: number
}

export interface StyleApplyResponse {
  styled_image_url: string
  style_type: string
  processing_time: number
  task_id?: string
}

export class StyleClient {
  async generatePreview(file: File, styleType: string): Promise<StylePreviewResponse> {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('style_type', styleType)

    const token = localStorage.getItem('token')
    const headers: Record<string, string> = {}
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    const response = await fetch(`${API_BASE_URL}/api/v1/style/preview`, {
      method: 'POST',
      headers,
      body: formData
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Style preview generation failed')
    }

    return response.json()
  }

  async applyStyle(file: File, styleType: string, iterations: number = 300): Promise<StyleApplyResponse> {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('style_type', styleType)
    formData.append('iterations', iterations.toString())

    const token = localStorage.getItem('token')
    const headers: Record<string, string> = {}
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    const response = await fetch(`${API_BASE_URL}/api/v1/style/apply`, {
      method: 'POST',
      headers,
      body: formData
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Style application failed')
    }

    return response.json()
  }

  async getAvailableStyles(): Promise<{ styles: StyleOption[] }> {
    const response = await fetch(`${API_BASE_URL}/api/v1/style/styles`)

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Failed to fetch available styles')
    }

    return response.json()
  }

  // 파일 유효성 검사 헬퍼 메서드
  validateImageFile(file: File): { isValid: boolean; error?: string } {
    const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
    const maxSize = 10 * 1024 * 1024 // 10MB

    if (!allowedTypes.includes(file.type)) {
      return {
        isValid: false,
        error: 'Only JPEG, PNG, and WebP images are allowed'
      }
    }

    if (file.size > maxSize) {
      return {
        isValid: false,
        error: 'File size must be less than 10MB'
      }
    }

    return { isValid: true }
  }

  // 이미지 리사이즈 헬퍼 메서드
  async resizeImage(file: File, maxWidth: number = 1024, maxHeight: number = 1024): Promise<File> {
    return new Promise((resolve) => {
      const canvas = document.createElement('canvas')
      const ctx = canvas.getContext('2d')!
      const img = new Image()

      img.onload = () => {
        // 비율 유지하면서 리사이즈
        let { width, height } = img

        if (width > height) {
          if (width > maxWidth) {
            height = (height * maxWidth) / width
            width = maxWidth
          }
        } else {
          if (height > maxHeight) {
            width = (width * maxHeight) / height
            height = maxHeight
          }
        }

        canvas.width = width
        canvas.height = height
        ctx.drawImage(img, 0, 0, width, height)

        canvas.toBlob((blob) => {
          if (blob) {
            const resizedFile = new File([blob], file.name, {
              type: file.type,
              lastModified: Date.now()
            })
            resolve(resizedFile)
          } else {
            resolve(file)
          }
        }, file.type, 0.9)
      }

      img.src = URL.createObjectURL(file)
    })
  }
}

export const styleClient = new StyleClient()
