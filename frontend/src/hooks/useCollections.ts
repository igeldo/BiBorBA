import { useState, useEffect } from 'react'
import { apiService } from '../services/api'
import type { Collection } from '../types'

export interface UseCollectionsReturn {
  selectedCollections: number[]
  setSelectedCollections: (ids: number[]) => void
  toggleCollection: (id: number) => void
  availableCollections: Collection[]
  isLoading: boolean
  error: string | null
  reload: () => Promise<void>
}

export const useCollections = (shouldLoad: boolean = true): UseCollectionsReturn => {
  const [selectedCollections, setSelectedCollections] = useState<number[]>([])
  const [availableCollections, setAvailableCollections] = useState<Collection[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadCollections = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const collections = await apiService.getCollectionsList()
      setAvailableCollections(collections)
    } catch (err) {
      console.error('Failed to load collections:', err)
      setError(err instanceof Error ? err.message : 'Failed to load collections')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    if (shouldLoad) {
      loadCollections()
    }
  }, [shouldLoad])

  const toggleCollection = (id: number) => {
    setSelectedCollections(prev =>
      prev.includes(id)
        ? prev.filter(cid => cid !== id)
        : [...prev, id]
    )
  }

  return {
    selectedCollections,
    setSelectedCollections,
    toggleCollection,
    availableCollections,
    isLoading,
    error,
    reload: loadCollections
  }
}
