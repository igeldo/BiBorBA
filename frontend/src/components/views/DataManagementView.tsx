import React, { useState, useEffect } from 'react'
import { apiService } from '../../services/api'
import type { ScrapeParams, ScrapeJobStatus, ScraperStats, PaginatedQuestionsResponse } from '../../types'

export const DataManagementView: React.FC = () => {
  const [scrapeParams, setScrapeParams] = useState<ScrapeParams>({
    count: 50,
    days_back: 365,
    tags: ['sql'],
    min_score: 1,
    only_accepted_answers: false,
    start_page: 1
  })
  const [scrapeJobStatus, setScrapeJobStatus] = useState<ScrapeJobStatus | null>(null)
  const [scraperStats, setScraperStats] = useState<ScraperStats | null>(null)
  const [paginatedQuestions, setPaginatedQuestions] = useState<PaginatedQuestionsResponse | null>(null)
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [tagFilter, setTagFilter] = useState('')
  const [minScoreFilter, setMinScoreFilter] = useState<number | undefined>(undefined)
  const [sortBy, setSortBy] = useState('creation_date')
  const [sortOrder, setSortOrder] = useState('desc')
  const [dataLoading, setDataLoading] = useState(false)
  const [apiTestResult, setApiTestResult] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)

  const handleStartScraping = async () => {
    setDataLoading(true)
    setError(null)
    try {
      const result = await apiService.startScraping(scrapeParams)
      setScrapeJobStatus(result)

      const pollInterval = setInterval(async () => {
        try {
          const status = await apiService.getScrapeJobStatus(result.job_id)
          setScrapeJobStatus(status)

          if (status.status === 'completed' || status.status === 'failed') {
            clearInterval(pollInterval)
            setDataLoading(false)

            if (status.status === 'completed') {
              await loadScraperStats()
              await loadPaginatedQuestions()
            }
          }
        } catch (err) {
          console.error('Error polling job status:', err)
          clearInterval(pollInterval)
          setDataLoading(false)
        }
      }, 2000)

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start scraping')
      setDataLoading(false)
    }
  }

  const loadScraperStats = async () => {
    try {
      const stats = await apiService.getScraperStats()
      setScraperStats(stats)
    } catch (err) {
      console.error('Error loading stats:', err)
    }
  }

  const loadPaginatedQuestions = async () => {
    setDataLoading(true)
    try {
      const result = await apiService.getQuestionsPaginated({
        page: currentPage,
        page_size: pageSize,
        tags: tagFilter || undefined,
        min_score: minScoreFilter,
        sort_by: sortBy,
        sort_order: sortOrder
      })
      setPaginatedQuestions(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load questions')
    } finally {
      setDataLoading(false)
    }
  }

  const handleTestApi = async () => {
    setDataLoading(true)
    try {
      const result = await apiService.testStackoverflowApi()
      setApiTestResult(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'API test failed')
    } finally {
      setDataLoading(false)
    }
  }

  useEffect(() => {
    loadScraperStats()
    loadPaginatedQuestions()
  }, [])

  useEffect(() => {
    if (paginatedQuestions !== null) {
      loadPaginatedQuestions()
    }
  }, [currentPage, pageSize, tagFilter, minScoreFilter, sortBy, sortOrder])

  return (
    <div className="data-management-view">
      {/* API Test & Stats Section */}
      <div className="query-section">
        <h2>📊 Stackoverflow Data Management</h2>
        <p>Scrape, manage and explore Stackoverflow questions in the database</p>

        <div style={{ display: 'flex', gap: '15px', marginTop: '20px', flexWrap: 'wrap' }}>
          <button
            onClick={handleTestApi}
            disabled={dataLoading}
            style={{ background: '#28a745' }}
          >
            Test API Connection
          </button>
          <button
            onClick={loadScraperStats}
            disabled={dataLoading}
          >
            Refresh Statistics
          </button>
        </div>

        {apiTestResult && (
          <div style={{
            marginTop: '15px',
            padding: '15px',
            background: apiTestResult.api_available ? '#d4edda' : '#f8d7da',
            borderRadius: '8px',
            border: `2px solid ${apiTestResult.api_available ? '#28a745' : '#dc3545'}`
          }}>
            <strong>API Status:</strong> {apiTestResult.api_available ? '✓ Connected' : '✗ Not available'}<br />
            <strong>Quota Remaining:</strong> {apiTestResult.quota_remaining || 'N/A'}
          </div>
        )}

        {scraperStats && (
          <div className="stats-grid" style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: '15px',
            marginTop: '20px'
          }}>
            <div className="stat-card">
              <div className="stat-label">Total Questions</div>
              <div className="stat-value">{scraperStats.total_questions}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Total Answers</div>
              <div className="stat-value">{scraperStats.total_answers}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Accepted Answers</div>
              <div className="stat-value">{scraperStats.accepted_answers}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Avg Question Score</div>
              <div className="stat-value">{scraperStats.avg_question_score?.toFixed(1)}</div>
            </div>
          </div>
        )}
      </div>

      {/* Scraping Section */}
      <div className="query-section" style={{ marginTop: '20px' }}>
        <h3>🔍 Scrape New Data</h3>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px', marginTop: '15px' }}>
          <div className="form-group">
            <label>Count (1-1000):</label>
            <input
              type="number"
              min="1"
              max="1000"
              value={scrapeParams.count}
              onChange={(e) => setScrapeParams({...scrapeParams, count: parseInt(e.target.value)})}
              disabled={dataLoading}
            />
          </div>

          <div className="form-group">
            <label>Days Back (1-3650):</label>
            <input
              type="number"
              min="1"
              max="3650"
              value={scrapeParams.days_back}
              onChange={(e) => setScrapeParams({...scrapeParams, days_back: parseInt(e.target.value)})}
              disabled={dataLoading}
            />
          </div>

          <div className="form-group">
            <label>Min Score:</label>
            <input
              type="number"
              min="0"
              value={scrapeParams.min_score}
              onChange={(e) => setScrapeParams({...scrapeParams, min_score: parseInt(e.target.value)})}
              disabled={dataLoading}
            />
          </div>
        </div>

        <div className="form-group" style={{ marginTop: '15px' }}>
          <label>Tags (comma-separated):</label>
          <input
            type="text"
            value={scrapeParams.tags.join(', ')}
            onChange={(e) => setScrapeParams({...scrapeParams, tags: e.target.value.split(',').map(t => t.trim())})}
            placeholder="sql"
            disabled={dataLoading}
          />
        </div>

        <div className="form-group" style={{ marginTop: '15px' }}>
          <label>Start Page (for continuation):</label>
          <input
            type="number"
            min="1"
            value={scrapeParams.start_page}
            onChange={(e) => setScrapeParams({...scrapeParams, start_page: parseInt(e.target.value)})}
            disabled={dataLoading}
          />
          <small style={{ display: 'block', color: '#666', marginTop: '5px' }}>
            Start at page X to continue from previous batch (100 questions per page)
          </small>
        </div>

        <div className="form-group checkbox-group">
          <input
            type="checkbox"
            id="onlyAccepted"
            checked={scrapeParams.only_accepted_answers}
            onChange={(e) => setScrapeParams({...scrapeParams, only_accepted_answers: e.target.checked})}
            disabled={dataLoading}
          />
          <label htmlFor="onlyAccepted">Only questions with accepted answers (⚠️ may result in 0 results)</label>
        </div>

        <button
          onClick={handleStartScraping}
          disabled={dataLoading}
          style={{ marginTop: '15px', background: '#f48024' }}
        >
          {dataLoading && <span className="loading"></span>}
          {dataLoading ? 'Scraping...' : 'Start Scraping'}
        </button>

        {scrapeJobStatus && (
          <div style={{
            marginTop: '20px',
            padding: '20px',
            background: '#f8f9fa',
            borderRadius: '8px',
            border: '2px solid #007bff'
          }}>
            <h4>Job Status: {scrapeJobStatus.status}</h4>
            {scrapeJobStatus.progress && (
              <div style={{ marginTop: '10px' }}>
                <p><strong>Questions:</strong> {scrapeJobStatus.progress.questions_fetched} fetched, {scrapeJobStatus.progress.questions_stored} stored</p>
                <p><strong>Answers:</strong> {scrapeJobStatus.progress.answers_fetched} fetched, {scrapeJobStatus.progress.answers_stored} stored</p>
                {scrapeJobStatus.progress.errors > 0 && (
                  <p style={{ color: '#dc3545' }}><strong>Errors:</strong> {scrapeJobStatus.progress.errors}</p>
                )}
              </div>
            )}
            {scrapeJobStatus.result && (
              <div style={{ marginTop: '10px', padding: '10px', background: '#d4edda', borderRadius: '4px' }}>
                <strong>✓ Completed:</strong> {scrapeJobStatus.result.questions_stored} questions and {scrapeJobStatus.result.answers_stored} answers stored
              </div>
            )}
          </div>
        )}
      </div>

      {/* Questions Browse Section */}
      <div className="query-section" style={{ marginTop: '20px' }}>
        <h3>📋 Browse Questions</h3>

        {/* Filters */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px', marginTop: '15px' }}>
          <div className="form-group">
            <label>Filter by Tags:</label>
            <input
              type="text"
              value={tagFilter}
              onChange={(e) => setTagFilter(e.target.value)}
              placeholder="e.g., mysql"
            />
          </div>

          <div className="form-group">
            <label>Min Score:</label>
            <input
              type="number"
              min="0"
              value={minScoreFilter || ''}
              onChange={(e) => setMinScoreFilter(e.target.value ? parseInt(e.target.value) : undefined)}
            />
          </div>

          <div className="form-group">
            <label>Sort By:</label>
            <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
              <option value="creation_date">Creation Date</option>
              <option value="score">Score</option>
              <option value="view_count">View Count</option>
            </select>
          </div>

          <div className="form-group">
            <label>Order:</label>
            <select value={sortOrder} onChange={(e) => setSortOrder(e.target.value)}>
              <option value="desc">Descending</option>
              <option value="asc">Ascending</option>
            </select>
          </div>
        </div>

        {/* Questions Table */}
        {paginatedQuestions && (
          <>
            <div style={{ marginTop: '20px', overflowX: 'auto' }}>
              <table style={{
                width: '100%',
                borderCollapse: 'collapse',
                background: 'white',
                borderRadius: '8px',
                overflow: 'hidden',
                boxShadow: '0 2px 10px rgba(0,0,0,0.1)'
              }}>
                <thead>
                  <tr style={{ background: '#f8f9fa', borderBottom: '2px solid #dee2e6' }}>
                    <th style={{ padding: '12px', textAlign: 'left' }}>Title</th>
                    <th style={{ padding: '12px', textAlign: 'left' }}>Tags</th>
                    <th style={{ padding: '12px', textAlign: 'center' }}>Score</th>
                    <th style={{ padding: '12px', textAlign: 'center' }}>Views</th>
                    <th style={{ padding: '12px', textAlign: 'center' }}>Answers</th>
                    <th style={{ padding: '12px', textAlign: 'center' }}>Created</th>
                  </tr>
                </thead>
                <tbody>
                  {paginatedQuestions.items.map((q) => (
                    <tr key={q.id} style={{ borderBottom: '1px solid #f0f0f0' }}>
                      <td style={{ padding: '12px' }}>
                        <a href={`https://stackoverflow.com/questions/${q.stack_overflow_id}`} target="_blank" rel="noopener noreferrer" style={{ color: '#007bff', textDecoration: 'none' }}>
                          {q.title}
                        </a>
                      </td>
                      <td style={{ padding: '12px' }}>
                        <div style={{ display: 'flex', gap: '5px', flexWrap: 'wrap' }}>
                          {q.tags.slice(0, 3).map((tag, idx) => (
                            <span key={idx} className="tag">{tag}</span>
                          ))}
                        </div>
                      </td>
                      <td style={{ padding: '12px', textAlign: 'center', fontWeight: 'bold', color: q.score > 5 ? '#28a745' : '#666' }}>
                        {q.score}
                      </td>
                      <td style={{ padding: '12px', textAlign: 'center' }}>{q.view_count}</td>
                      <td style={{ padding: '12px', textAlign: 'center' }}>{q.answer_count}</td>
                      <td style={{ padding: '12px', textAlign: 'center', fontSize: '12px', color: '#666' }}>
                        {new Date(q.creation_date).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination Controls */}
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginTop: '20px',
              padding: '15px',
              background: '#f8f9fa',
              borderRadius: '8px'
            }}>
              <div>
                Showing {paginatedQuestions.items.length} of {paginatedQuestions.total} questions
                (Page {paginatedQuestions.page} of {paginatedQuestions.total_pages})
              </div>

              <div style={{ display: 'flex', gap: '10px' }}>
                <button
                  onClick={() => setCurrentPage(currentPage - 1)}
                  disabled={!paginatedQuestions.has_prev || dataLoading}
                  style={{ padding: '8px 16px' }}
                >
                  ← Previous
                </button>

                <select
                  value={pageSize}
                  onChange={(e) => {
                    setPageSize(parseInt(e.target.value))
                    setCurrentPage(1)
                  }}
                  style={{ padding: '8px' }}
                >
                  <option value="10">10 per page</option>
                  <option value="20">20 per page</option>
                  <option value="50">50 per page</option>
                  <option value="100">100 per page</option>
                </select>

                <button
                  onClick={() => setCurrentPage(currentPage + 1)}
                  disabled={!paginatedQuestions.has_next || dataLoading}
                  style={{ padding: '8px 16px' }}
                >
                  Next →
                </button>
              </div>
            </div>
          </>
        )}

        {dataLoading && !paginatedQuestions && (
          <div style={{ textAlign: 'center', padding: '40px' }}>
            <span className="loading"></span>
            <p>Loading questions...</p>
          </div>
        )}
      </div>

      {error && (
        <div className="error" style={{ marginTop: '20px' }}>
          <strong>Error:</strong> {error}
          <button
            onClick={() => setError(null)}
            style={{ marginLeft: '10px', background: 'none', border: 'none', fontSize: '18px', cursor: 'pointer' }}
          >
            ×
          </button>
        </div>
      )}
    </div>
  )
}
