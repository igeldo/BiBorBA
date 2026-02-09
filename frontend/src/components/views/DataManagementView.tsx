import React, { useState, useEffect } from 'react'
import { apiService } from '../../services/api'
import type { ScrapeParams, ScrapeJobStatus, ScraperStats, PaginatedQuestionsResponse } from '../../types'
import { SortableHeader, HeaderCell, TablePagination, StackOverflowLink, TagList } from '../table'
import { TABLE_PAGE_SIZES, DEFAULT_PAGE_SIZE, TABLE_COLORS, getScoreDisplayColor } from '../../theme/tableConstants'

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
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE)
  const [tagFilter, setTagFilter] = useState('')
  const [minScoreFilter, setMinScoreFilter] = useState<number | undefined>(undefined)
  const [sortBy, setSortBy] = useState('creation_date')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')
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
        <h2>📊 Stackoverflow-Datenverwaltung</h2>
        <p>Durchsuchen, verwalten und erkunden Sie Stackoverflow-Fragen in der Datenbank</p>

        <div style={{ display: 'flex', gap: '15px', marginTop: '20px', flexWrap: 'wrap' }}>
          <button
            onClick={handleTestApi}
            disabled={dataLoading}
            style={{ background: '#28a745' }}
          >
            API-Verbindung testen
          </button>
          <button
            onClick={loadScraperStats}
            disabled={dataLoading}
          >
            Statistiken aktualisieren
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
            <strong>API-Status:</strong> {apiTestResult.api_available ? '✓ Verbunden' : '✗ Nicht verfügbar'}<br />
            <strong>Verbleibendes Kontingent:</strong> {apiTestResult.quota_remaining || 'N/A'}
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
              <div className="stat-label">Gesamt-Fragen</div>
              <div className="stat-value">{scraperStats.total_questions}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Gesamt-Antworten</div>
              <div className="stat-value">{scraperStats.total_answers}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Akzeptierte Antworten</div>
              <div className="stat-value">{scraperStats.accepted_answers}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Durchschn. Fragen-Score</div>
              <div className="stat-value">{scraperStats.avg_question_score?.toFixed(1)}</div>
            </div>
          </div>
        )}
      </div>

      {/* Scraping Section */}
      <div className="query-section" style={{ marginTop: '20px' }}>
        <h3>🔍 Neue Daten abrufen</h3>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px', marginTop: '15px' }}>
          <div className="form-group">
            <label>Anzahl (1-1000):</label>
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
            <label>Tage zurück (1-3650):</label>
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
          <label>Tags (kommagetrennt):</label>
          <input
            type="text"
            value={scrapeParams.tags.join(', ')}
            onChange={(e) => setScrapeParams({...scrapeParams, tags: e.target.value.split(',').map(t => t.trim())})}
            placeholder="sql"
            disabled={dataLoading}
          />
        </div>

        <div className="form-group" style={{ marginTop: '15px' }}>
          <label>Startseite (für Fortsetzung):</label>
          <input
            type="number"
            min="1"
            value={scrapeParams.start_page}
            onChange={(e) => setScrapeParams({...scrapeParams, start_page: parseInt(e.target.value)})}
            disabled={dataLoading}
          />
          <small style={{ display: 'block', color: '#666', marginTop: '5px' }}>
            Beginnen Sie bei Seite X, um vom vorherigen Batch fortzufahren (100 Fragen pro Seite)
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
          <label htmlFor="onlyAccepted">Nur Fragen mit akzeptierten Antworten (⚠️ kann zu 0 Ergebnissen führen)</label>
        </div>

        <button
          onClick={handleStartScraping}
          disabled={dataLoading}
          style={{ marginTop: '15px', background: '#f48024' }}
        >
          {dataLoading && <span className="loading"></span>}
          {dataLoading ? 'Wird abgerufen...' : 'Abruf starten'}
        </button>

        {scrapeJobStatus && (
          <div style={{
            marginTop: '20px',
            padding: '20px',
            background: '#f8f9fa',
            borderRadius: '8px',
            border: '2px solid #007bff'
          }}>
            <h4>Job-Status: {scrapeJobStatus.status}</h4>
            {scrapeJobStatus.progress && (
              <div style={{ marginTop: '10px' }}>
                <p><strong>Fragen:</strong> {scrapeJobStatus.progress.questions_fetched} abgerufen, {scrapeJobStatus.progress.questions_stored} gespeichert</p>
                <p><strong>Antworten:</strong> {scrapeJobStatus.progress.answers_fetched} abgerufen, {scrapeJobStatus.progress.answers_stored} gespeichert</p>
                {scrapeJobStatus.progress.errors > 0 && (
                  <p style={{ color: '#dc3545' }}><strong>Fehler:</strong> {scrapeJobStatus.progress.errors}</p>
                )}
              </div>
            )}
            {scrapeJobStatus.result && (
              <div style={{ marginTop: '10px', padding: '10px', background: '#d4edda', borderRadius: '4px' }}>
                <strong>✓ Abgeschlossen:</strong> {scrapeJobStatus.result.questions_stored} Fragen und {scrapeJobStatus.result.answers_stored} Antworten gespeichert
              </div>
            )}
          </div>
        )}
      </div>

      {/* Questions Browse Section */}
      <div className="query-section" style={{ marginTop: '20px' }}>
        <h3>📋 Fragen durchsuchen</h3>

        {/* Filters */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px', marginTop: '15px' }}>
          <div className="form-group">
            <label>Nach Tags filtern:</label>
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
                  <tr style={{ background: TABLE_COLORS.headerBg }}>
                    <SortableHeader
                      column="title"
                      label="Titel"
                      sortBy={sortBy}
                      sortOrder={sortOrder}
                      onSort={(col) => {
                        if (sortBy === col) {
                          setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc')
                        } else {
                          setSortBy(col)
                          setSortOrder('asc')
                        }
                        setCurrentPage(1)
                      }}
                    />
                    <HeaderCell>Tags</HeaderCell>
                    <SortableHeader
                      column="score"
                      label="Score"
                      sortBy={sortBy}
                      sortOrder={sortOrder}
                      onSort={(col) => {
                        if (sortBy === col) {
                          setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc')
                        } else {
                          setSortBy(col)
                          setSortOrder('desc')
                        }
                        setCurrentPage(1)
                      }}
                      align="center"
                    />
                    <SortableHeader
                      column="view_count"
                      label="Ansichten"
                      sortBy={sortBy}
                      sortOrder={sortOrder}
                      onSort={(col) => {
                        if (sortBy === col) {
                          setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc')
                        } else {
                          setSortBy(col)
                          setSortOrder('desc')
                        }
                        setCurrentPage(1)
                      }}
                      align="center"
                    />
                    <HeaderCell align="center">Antworten</HeaderCell>
                    <SortableHeader
                      column="creation_date"
                      label="Erstellt"
                      sortBy={sortBy}
                      sortOrder={sortOrder}
                      onSort={(col) => {
                        if (sortBy === col) {
                          setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc')
                        } else {
                          setSortBy(col)
                          setSortOrder('desc')
                        }
                        setCurrentPage(1)
                      }}
                      align="center"
                    />
                  </tr>
                </thead>
                <tbody>
                  {paginatedQuestions.items.map((q) => (
                    <tr key={q.id} style={{ borderBottom: `1px solid ${TABLE_COLORS.rowBorder}` }}>
                      <td style={{ padding: '12px' }}>
                        <StackOverflowLink
                          stackOverflowId={q.stack_overflow_id}
                          title={q.title}
                        />
                      </td>
                      <td style={{ padding: '12px' }}>
                        <TagList tags={q.tags} maxTags={3} />
                      </td>
                      <td style={{ padding: '12px', textAlign: 'center', fontWeight: 'bold', color: getScoreDisplayColor(q.score) }}>
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
            <TablePagination
              page={paginatedQuestions.page}
              pageSize={pageSize}
              totalItems={paginatedQuestions.total}
              totalPages={paginatedQuestions.total_pages}
              hasNext={paginatedQuestions.has_next}
              hasPrev={paginatedQuestions.has_prev}
              onPageChange={setCurrentPage}
              onPageSizeChange={(size) => {
                setPageSize(size)
                setCurrentPage(1)
              }}
              pageSizeOptions={TABLE_PAGE_SIZES}
            />
          </>
        )}

        {dataLoading && !paginatedQuestions && (
          <div style={{ textAlign: 'center', padding: '40px' }}>
            <span className="loading"></span>
            <p>Fragen werden geladen...</p>
          </div>
        )}
      </div>

      {error && (
        <div className="error" style={{ marginTop: '20px' }}>
          <strong>Fehler:</strong> {error}
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
