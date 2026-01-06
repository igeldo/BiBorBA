import { useState } from 'react'
import { apiService } from '../services/api'
import type { QueryRequest, QueryResponse } from '../types'
import { GraphType } from '../types'

export interface UseQueryOptions {
  initialSessionId?: string
}

export interface UseQueryReturn {
  question: string
  setQuestion: (q: string) => void
  sessionId: string
  setSessionId: (id: string) => void
  selectedGraphType: GraphType
  setSelectedGraphType: (type: GraphType) => void
  temperature: number
  setTemperature: (temp: number) => void
  loading: boolean
  error: string | null
  setError: (err: string | null) => void
  result: QueryResponse | null
  handleSubmit: (e: React.FormEvent, selectedCollections: number[]) => Promise<void>
  resetResult: () => void
}

export const useQuery = (options: UseQueryOptions = {}): UseQueryReturn => {
  const [question, setQuestion] = useState('')
  const [sessionId, setSessionId] = useState(
    () => options.initialSessionId || `session_${Date.now()}`
  )
  const [selectedGraphType, setSelectedGraphType] = useState<GraphType>(GraphType.ADAPTIVE_RAG)
  const [temperature, setTemperature] = useState(0.1)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<QueryResponse | null>(null)

  const resetResult = () => {
    setResult(null)
    setError(null)
  }

  const handleSubmit = async (e: React.FormEvent, selectedCollections: number[]) => {
    e.preventDefault()

    if (!question.trim()) {
      setError('Please enter a question')
      return
    }

    setLoading(true)
    setError(null)
    setResult(null)

    try {
      let response: QueryResponse

      if (selectedCollections.length > 0) {
        response = await apiService.queryCollections({
          question: question.trim(),
          session_id: sessionId,
          collection_ids: selectedCollections,
          graph_type: selectedGraphType,
          llm_config: { temperature }
        })
      } else {
        const request: QueryRequest = {
          question: question.trim(),
          session_id: sessionId,
          include_stackoverflow: false,
          graph_type: selectedGraphType,
          llm_config: { temperature }
        }
        response = await apiService.query(request)
      }

      setResult(response)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    } finally {
      setLoading(false)
    }
  }

  return {
    question,
    setQuestion,
    sessionId,
    setSessionId,
    selectedGraphType,
    setSelectedGraphType,
    temperature,
    setTemperature,
    loading,
    error,
    setError,
    result,
    handleSubmit,
    resetResult
  }
}
