import { useState, useEffect } from 'react'
import { apiService } from './services/api'
import { DataManagementView } from './components/views/DataManagementView'
import { CollectionManagementView } from './components/views/CollectionManagementView'
import { BatchQuerySelection } from './components/views/BatchQuerySelection'
import { BatchQueryProgress } from './components/views/BatchQueryProgress'
import { ComparisonView } from './components/views/ComparisonView'
import { QueryView } from './components/query/QueryView'
import { ViewSwitcher } from './components/layout/ViewSwitcher'
import type { ViewType } from './types'

// Main App Component
function App() {
  // View state
  const [currentView, setCurrentView] = useState<ViewType>('query')

  // Batch query state
  const [batchJobId, setBatchJobId] = useState<string | null>(null)

  // Effect to handle batch-started event from BatchQuerySelection
  useEffect(() => {
    const handleBatchStarted = (event: CustomEvent<{ jobId: string }>) => {
      const jobId = event.detail.jobId
      setBatchJobId(jobId)
      localStorage.setItem('current_batch_job_id', jobId)
      setCurrentView('batch-progress')
    }

    window.addEventListener('batch-started', handleBatchStarted as EventListener)

    // Validate existing job on mount
    const existingJobId = localStorage.getItem('current_batch_job_id')
    if (existingJobId) {
      apiService.getBatchQueryStatus(existingJobId)
        .then(jobStatus => {
          if (jobStatus.status === 'running') {
            setBatchJobId(existingJobId)
            setCurrentView('batch-progress')
          } else {
            localStorage.removeItem('current_batch_job_id')
          }
        })
        .catch(() => {
          localStorage.removeItem('current_batch_job_id')
        })
    }

    return () => {
      window.removeEventListener('batch-started', handleBatchStarted as EventListener)
    }
  }, [])

  // Check for running jobs and auto-redirect if needed
  const checkAndRedirectToRunningJob = async () => {
    try {
      const runningJobs = await apiService.listBatchQueryJobs('running', 1)

      if (runningJobs.length > 0) {
        const runningJob = runningJobs[0]
        setBatchJobId(runningJob.job_id)
        localStorage.setItem('current_batch_job_id', runningJob.job_id)
        setCurrentView('batch-progress')
        return true
      }

      // No running job - validate localStorage
      const storedJobId = localStorage.getItem('current_batch_job_id')
      if (storedJobId) {
        try {
          const jobStatus = await apiService.getBatchQueryStatus(storedJobId)
          if (jobStatus.status === 'running') {
            setBatchJobId(storedJobId)
            setCurrentView('batch-progress')
            return true
          } else {
            localStorage.removeItem('current_batch_job_id')
            setBatchJobId(null)
          }
        } catch {
          localStorage.removeItem('current_batch_job_id')
          setBatchJobId(null)
        }
      }

      return false
    } catch (error) {
      console.error('Failed to check for running jobs:', error)
      return false
    }
  }

  // Auto-redirect to running job when switching to batch-queries
  useEffect(() => {
    if (currentView === 'batch-queries') {
      checkAndRedirectToRunningJob()
    }
  }, [currentView])

  return (
    <div className="container">
      {/* Header */}
      <div className="header">
        <h1>🧠 LangGraph RAG System</h1>
        <p>Intelligent Document Retrieval and Question Answering with Multi-Source Support</p>

        {/* View Switcher */}
        <ViewSwitcher
          currentView={currentView}
          onViewChange={setCurrentView}
        />
      </div>

      {/* Query Mode */}
      {currentView === 'query' && <QueryView />}

      {/* Data Management Mode */}
      {currentView === 'data' && <DataManagementView />}

      {/* Collection Management Mode */}
      {currentView === 'collection-management' && (
        <div className="query-section" style={{ height: 'calc(100vh - 200px)' }}>
          <CollectionManagementView />
        </div>
      )}

      {/* Batch Query Selection Mode */}
      {currentView === 'batch-queries' && <BatchQuerySelection />}

      {/* Batch Query Progress Mode */}
      {currentView === 'batch-progress' && batchJobId && (
        <BatchQueryProgress
          jobId={batchJobId}
          onBack={(jobStatus) => {
            if (['completed', 'failed', 'cancelled'].includes(jobStatus)) {
              setBatchJobId(null)
              localStorage.removeItem('current_batch_job_id')
            }
            setCurrentView('batch-queries')
          }}
        />
      )}

      {/* Graph Comparison Mode */}
      {currentView === 'comparison' && <ComparisonView />}

      <style>{`
        .rewritten-question-notice {
          background: #e7f3ff;
          border: 2px solid #2196F3;
          border-radius: 8px;
          padding: 15px;
          margin-bottom: 20px;
        }

        .notice-header {
          display: flex;
          align-items: center;
          gap: 10px;
          margin-bottom: 10px;
          color: #1976d2;
        }

        .notice-icon {
          font-size: 20px;
        }

        .notice-content {
          display: flex;
          flex-direction: column;
          gap: 10px;
          font-size: 14px;
        }

        .original-question, .rewritten-question {
          padding: 8px;
          background: white;
          border-radius: 4px;
        }

        .graph-trace-section {
          background: #f8f9fa;
          padding: 20px;
          border-radius: 8px;
          margin-top: 20px;
          border: 2px solid #e9ecef;
        }

        .graph-trace-section h3 {
          margin: 0 0 10px 0;
          color: #495057;
        }

        .trace-description {
          color: #6c757d;
          margin-bottom: 20px;
          font-size: 14px;
        }

        .graph-trace {
          display: flex;
          flex-wrap: wrap;
          align-items: center;
          gap: 10px;
        }

        .trace-node {
          background: white;
          border: 2px solid #007bff;
          border-radius: 8px;
          padding: 12px;
          display: flex;
          align-items: center;
          gap: 10px;
          flex: 0 0 auto;
          min-width: 200px;
        }

        .trace-node-number {
          background: #007bff;
          color: white;
          width: 28px;
          height: 28px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: bold;
          font-size: 14px;
          flex-shrink: 0;
        }

        .trace-node-content {
          flex: 1;
        }

        .trace-node-name {
          font-weight: bold;
          color: #212529;
          font-size: 14px;
          margin-bottom: 4px;
        }

        .trace-node-description {
          font-size: 12px;
          color: #6c757d;
          line-height: 1.4;
        }

        .trace-arrow {
          font-size: 24px;
          color: #007bff;
          font-weight: bold;
        }

        .source-breakdown-section {
          background: #f8f9fa;
          padding: 20px;
          border-radius: 8px;
          margin-top: 20px;
          border: 2px solid #e9ecef;
        }

        .source-breakdown-section h3 {
          margin: 0 0 15px 0;
          color: #495057;
        }

        .source-breakdown-chart {
          display: flex;
          flex-direction: column;
          gap: 15px;
        }

        .source-bar-container {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .source-bar-label {
          display: flex;
          justify-content: space-between;
          font-size: 14px;
        }

        .source-name {
          font-weight: bold;
          color: #495057;
        }

        .source-count {
          color: #6c757d;
        }

        .source-bar-background {
          background: #e9ecef;
          height: 30px;
          border-radius: 15px;
          overflow: hidden;
          position: relative;
        }

        .source-bar-fill {
          height: 100%;
          border-radius: 15px;
          transition: width 0.3s ease;
          display: flex;
          align-items: center;
          justify-content: center;
          color: white;
          font-weight: bold;
          font-size: 12px;
        }

        .button.active {
          background: #0056b3;
          color: white;
        }

        .collections-view {
          max-width: 1200px;
          margin: 0 auto;
        }

        .collections-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
          gap: 25px;
          margin-top: 20px;
        }

        .collection-card {
          background: white;
          padding: 25px;
          border-radius: 10px;
          box-shadow: 0 2px 10px rgba(0,0,0,0.1);
          border: 1px solid #e1e5e9;
        }

        .collection-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 20px;
          padding-bottom: 15px;
          border-bottom: 2px solid #f5f7fa;
        }

        .collection-header h3 {
          margin: 0;
          font-size: 1.3em;
          color: #2c3e50;
        }

        .collection-stats {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }

        .stat-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 8px 0;
          border-bottom: 1px solid #f5f7fa;
        }

        .stat-label {
          color: #6c757d;
          font-size: 0.9em;
          font-weight: 500;
        }

        .stat-value {
          color: #2c3e50;
          font-weight: 600;
        }

        .rebuild-button {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
        }

        .system-info {
          background: white;
          padding: 20px;
          border-radius: 10px;
        }

        .system-info h4 {
          margin-top: 0;
          margin-bottom: 15px;
          color: #2c3e50;
        }

        .spinner {
          border: 2px solid #f3f3f3;
          border-top: 2px solid #007bff;
          border-radius: 50%;
          width: 14px;
          height: 14px;
          animation: spin 1s linear infinite;
          display: inline-block;
        }

        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }

        /* Data Management Styles */
        .data-management-view {
          max-width: 1400px;
          margin: 0 auto;
        }

        .stat-card {
          background: white;
          padding: 20px;
          border-radius: 8px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
          text-align: center;
        }

        .stat-card .stat-label {
          font-size: 0.9em;
          color: #6c757d;
          margin-bottom: 10px;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }

        .stat-card .stat-value {
          font-size: 2em;
          font-weight: bold;
          color: #007bff;
        }

        table {
          font-size: 14px;
        }

        table th {
          font-weight: 600;
          color: #495057;
          text-transform: uppercase;
          font-size: 12px;
          letter-spacing: 0.5px;
        }

        table tr:hover {
          background-color: #f8f9fa;
        }

        table a:hover {
          text-decoration: underline;
        }
      `}</style>
    </div>
  )
}

export default App
