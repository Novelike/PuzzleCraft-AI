import { useState, useEffect } from 'react'

interface UserStats {
  total_puzzles_completed: number
  total_play_time: number
  average_completion_time: number
  best_score: number
  current_streak: number
}

export const useUserStats = () => {
  const [stats, setStats] = useState<UserStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const token = localStorage.getItem('auth_token')
        if (!token) {
          throw new Error('No authentication token')
        }

        const response = await fetch(`${import.meta.env.VITE_API_URL}/api/v1/users/stats`, {
          headers: { Authorization: `Bearer ${token}` }
        })

        if (!response.ok) {
          const error = await response.json()
          throw new Error(error.detail || 'Failed to fetch user stats')
        }

        const statsData = await response.json()
        setStats(statsData)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error')
      } finally {
        setLoading(false)
      }
    }

    fetchStats()
  }, [])

  const refetch = async () => {
    setLoading(true)
    setError(null)
    
    try {
      const token = localStorage.getItem('auth_token')
      if (!token) {
        throw new Error('No authentication token')
      }

      const response = await fetch(`${import.meta.env.VITE_API_URL}/api/v1/users/stats`, {
        headers: { Authorization: `Bearer ${token}` }
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to fetch user stats')
      }

      const statsData = await response.json()
      setStats(statsData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  return { stats, loading, error, refetch }
}