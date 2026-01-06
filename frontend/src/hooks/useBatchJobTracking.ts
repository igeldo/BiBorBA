import { useState, useEffect, useCallback } from 'react'
import { apiService } from '../services/api'
import type { ViewType } from '../types'

const BATCH_JOB_STORAGE_KEY = 'current_batch_job_id'

export interface UseBatchJobTrackingReturn {
  batchJobId: string | null
  setBatchJobId: (id: string | null) => void
  hasRunningJob: boolean
  checkForRunningJob: () => Promise<boolean>
  clearBatchJob: () => void
}

export const useBatchJobTracking = (
  currentView: ViewType,
  setCurrentView: (view: ViewType) => void
): UseBatchJobTrackingReturn => {
  const [batchJobId, setBatchJobId] = useState<string | null>(null)
  const [hasRunningJob, setHasRunningJob] = useState(false)

  const clearBatchJob = useCallback(() => {
    setBatchJobId(null)
    localStorage.removeItem(BATCH_JOB_STORAGE_KEY)
  }, [])

  const checkForRunningJob = useCallback(async (): Promise<boolean> => {
    try {
      const runningJobs = await apiService.listBatchQueryJobs('running', 1)

      if (runningJobs.length > 0) {
        const runningJob = runningJobs[0]
        setBatchJobId(runningJob.job_id)
        localStorage.setItem(BATCH_JOB_STORAGE_KEY, runningJob.job_id)
        setHasRunningJob(true)
        setCurrentView('batch-progress')
        return true
      }

      // No running job - validate localStorage
      const storedJobId = localStorage.getItem(BATCH_JOB_STORAGE_KEY)
      if (storedJobId) {
        try {
          const jobStatus = await apiService.getBatchQueryStatus(storedJobId)
          if (jobStatus.status === 'running') {
            setBatchJobId(storedJobId)
            setHasRunningJob(true)
            setCurrentView('batch-progress')
            return true
          } else {
            clearBatchJob()
            setHasRunningJob(false)
          }
        } catch {
          clearBatchJob()
          setHasRunningJob(false)
        }
      }

      setHasRunningJob(false)
      return false
    } catch (error) {
      console.error('Failed to check for running jobs:', error)
      setHasRunningJob(false)
      return false
    }
  }, [setCurrentView, clearBatchJob])

  // Listen for batch-started events
  useEffect(() => {
    const handleBatchStarted = (event: CustomEvent<{ jobId: string }>) => {
      const jobId = event.detail.jobId
      setBatchJobId(jobId)
      localStorage.setItem(BATCH_JOB_STORAGE_KEY, jobId)
      setHasRunningJob(true)
      setCurrentView('batch-progress')
    }

    window.addEventListener('batch-started', handleBatchStarted as EventListener)

    // Validate existing job on mount
    const existingJobId = localStorage.getItem(BATCH_JOB_STORAGE_KEY)
    if (existingJobId) {
      apiService.getBatchQueryStatus(existingJobId)
        .then(jobStatus => {
          if (jobStatus.status === 'running') {
            setBatchJobId(existingJobId)
            setHasRunningJob(true)
            setCurrentView('batch-progress')
          } else {
            clearBatchJob()
          }
        })
        .catch(() => {
          clearBatchJob()
        })
    }

    return () => {
      window.removeEventListener('batch-started', handleBatchStarted as EventListener)
    }
  }, [setCurrentView, clearBatchJob])

  // Auto-redirect when switching to batch-queries view
  useEffect(() => {
    if (currentView === 'batch-queries') {
      checkForRunningJob()
    }
  }, [currentView, checkForRunningJob])

  return {
    batchJobId,
    setBatchJobId,
    hasRunningJob,
    checkForRunningJob,
    clearBatchJob
  }
}
