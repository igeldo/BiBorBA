import type { ExportFormat, ExportJobStatus } from '../../types'

interface AvailableModels {
  llm_models: string[]
  embedding_models: string[]
}

interface ActiveFilters {
  tagFilter: string
}

type ExportScope = 'all' | 'comparison_filter' | 'custom'

interface ExportModalProps {
  isOpen: boolean
  onClose: () => void
  // Export type
  exportType: 'full' | 'statistics' | 'comparison'
  setExportType: (type: 'full' | 'statistics' | 'comparison') => void
  // Format
  exportFormat: ExportFormat
  setExportFormat: (format: ExportFormat) => void
  // Full export options
  includeDocuments: boolean
  setIncludeDocuments: (value: boolean) => void
  includeFullAnswers: boolean
  setIncludeFullAnswers: (value: boolean) => void
  // Statistics options
  groupByGraphType: boolean
  setGroupByGraphType: (value: boolean) => void
  groupByLLM: boolean
  setGroupByLLM: (value: boolean) => void
  groupByEmbedding: boolean
  setGroupByEmbedding: (value: boolean) => void
  // Scope
  exportScope: ExportScope
  setExportScope: (scope: ExportScope) => void
  exportLlmModel: string
  setExportLlmModel: (model: string) => void
  exportEmbeddingModel: string
  setExportEmbeddingModel: (model: string) => void
  // Deduplication
  deduplicateLatest: boolean
  setDeduplicateLatest: (value: boolean) => void
  // Models and filters
  availableModels: AvailableModels
  activeFilters: ActiveFilters
  // Job status
  jobId: string | null
  jobStatus: ExportJobStatus | null
  isLoading: boolean
  onStartExport: () => void
  onDownload: () => void
}

export function ExportModal({
  isOpen,
  onClose,
  exportType,
  setExportType,
  exportFormat,
  setExportFormat,
  includeDocuments,
  setIncludeDocuments,
  includeFullAnswers,
  setIncludeFullAnswers,
  groupByGraphType,
  setGroupByGraphType,
  groupByLLM,
  setGroupByLLM,
  groupByEmbedding,
  setGroupByEmbedding,
  exportScope,
  setExportScope,
  exportLlmModel,
  setExportLlmModel,
  exportEmbeddingModel,
  setExportEmbeddingModel,
  deduplicateLatest,
  setDeduplicateLatest,
  availableModels,
  activeFilters,
  jobId,
  jobStatus,
  isLoading,
  onStartExport,
  onDownload
}: ExportModalProps) {
  if (!isOpen) return null

  const { tagFilter } = activeFilters

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.5)',
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      zIndex: 1000
    }}>
      <div style={{
        backgroundColor: 'white',
        borderRadius: '12px',
        padding: '24px',
        minWidth: '500px',
        maxWidth: '600px',
        maxHeight: '80vh',
        overflowY: 'auto',
        boxShadow: '0 4px 20px rgba(0, 0, 0, 0.2)'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h2 style={{ margin: 0 }}>Daten exportieren</h2>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              fontSize: '24px',
              cursor: 'pointer',
              color: '#666'
            }}
          >
            ×
          </button>
        </div>

        {/* Export Type Selection */}
        <div style={{ marginBottom: '20px' }}>
          <h4 style={{ marginBottom: '12px' }}>Export-Typ:</h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {[
              { value: 'statistics', label: 'Statistiken', desc: 'Aggregierte Metriken mit Mean, Std, 95% CI' },
              { value: 'comparison', label: 'Vergleichstabelle', desc: 'Side-by-side Vergleich pro Frage' },
              { value: 'full', label: 'Vollexport', desc: 'Alle Evaluierungsdaten inkl. Antworten' }
            ].map((type) => (
              <label
                key={type.value}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  padding: '12px',
                  backgroundColor: exportType === type.value ? '#e3f2fd' : '#f9f9f9',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  border: exportType === type.value ? '2px solid #1976d2' : '2px solid transparent'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center' }}>
                  <input
                    type="radio"
                    name="exportType"
                    checked={exportType === type.value}
                    onChange={() => setExportType(type.value as 'full' | 'statistics' | 'comparison')}
                    style={{ marginRight: '10px' }}
                  />
                  <span style={{ fontWeight: 500 }}>{type.label}</span>
                </div>
                <span style={{ fontSize: '12px', color: '#666', marginLeft: '24px', marginTop: '4px' }}>
                  {type.desc}
                </span>
              </label>
            ))}
          </div>
        </div>

        {/* Format Selection */}
        <div style={{ marginBottom: '20px' }}>
          <h4 style={{ marginBottom: '12px' }}>Format:</h4>
          <div style={{ display: 'flex', gap: '10px' }}>
            {[
              { value: 'csv', label: 'CSV', desc: 'Für Excel, R, Python' },
              { value: 'json', label: 'JSON', desc: 'Vollständige Daten' },
              { value: 'latex', label: 'LaTeX', desc: 'Paper-fertige Tabellen' }
            ].map((fmt) => (
              <label
                key={fmt.value}
                style={{
                  flex: 1,
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  padding: '12px',
                  backgroundColor: exportFormat === fmt.value ? '#e8f5e9' : '#f9f9f9',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  border: exportFormat === fmt.value ? '2px solid #28a745' : '2px solid transparent'
                }}
              >
                <input
                  type="radio"
                  name="exportFormat"
                  checked={exportFormat === fmt.value}
                  onChange={() => setExportFormat(fmt.value as ExportFormat)}
                  style={{ marginBottom: '4px' }}
                />
                <span style={{ fontWeight: 500 }}>{fmt.label}</span>
                <span style={{ fontSize: '11px', color: '#666' }}>{fmt.desc}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Options for Full Export */}
        {exportType === 'full' && (
          <div style={{ marginBottom: '20px' }}>
            <h4 style={{ marginBottom: '12px' }}>Optionen:</h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={includeDocuments}
                  onChange={(e) => setIncludeDocuments(e.target.checked)}
                  style={{ marginRight: '10px' }}
                />
                <span>Retrieved Documents einschließen</span>
              </label>
              <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={includeFullAnswers}
                  onChange={(e) => setIncludeFullAnswers(e.target.checked)}
                  style={{ marginRight: '10px' }}
                />
                <span>Vollständige Antworttexte einschließen</span>
              </label>
            </div>
          </div>
        )}

        {/* Group-by Options for Statistics Export */}
        {exportType === 'statistics' && (
          <div style={{ marginBottom: '20px' }}>
            <h4 style={{ marginBottom: '12px' }}>Gruppieren nach:</h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={groupByGraphType}
                  onChange={(e) => setGroupByGraphType(e.target.checked)}
                  style={{ marginRight: '10px' }}
                />
                <span>Graph-Typ (adaptive_rag, simple_rag, pure_llm)</span>
              </label>
              <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={groupByLLM}
                  onChange={(e) => setGroupByLLM(e.target.checked)}
                  style={{ marginRight: '10px' }}
                />
                <span>LLM Modell (z.B. gemma3:12b, gemma3:4b)</span>
              </label>
              <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={groupByEmbedding}
                  onChange={(e) => setGroupByEmbedding(e.target.checked)}
                  style={{ marginRight: '10px' }}
                />
                <span>Embedding Modell (z.B. embeddinggemma:latest)</span>
              </label>
            </div>
            {!groupByGraphType && !groupByLLM && !groupByEmbedding && (
              <div style={{ fontSize: '12px', color: '#f57c00', marginTop: '8px' }}>
                Hinweis: Wenn keine Option gewählt ist, wird nach Graph-Typ gruppiert.
              </div>
            )}
          </div>
        )}

        {/* Export-Umfang */}
        <div style={{ marginBottom: '20px' }}>
          <h4 style={{ marginBottom: '12px' }}>Export-Umfang:</h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>

            {/* Option 1: Alle Daten */}
            <label style={{
              display: 'flex', flexDirection: 'column', padding: '12px',
              backgroundColor: exportScope === 'all' ? '#e3f2fd' : '#f9f9f9',
              borderRadius: '6px', cursor: 'pointer',
              border: exportScope === 'all' ? '2px solid #1976d2' : '2px solid transparent'
            }}>
              <div style={{ display: 'flex', alignItems: 'center' }}>
                <input type="radio" name="exportScope" checked={exportScope === 'all'}
                  onChange={() => setExportScope('all')} style={{ marginRight: '10px' }} />
                <span style={{ fontWeight: 500 }}>Alle Daten</span>
              </div>
              <span style={{ fontSize: '12px', color: '#666', marginLeft: '24px' }}>
                Exportiert alle Evaluierungen ohne Filter
              </span>
            </label>

            {/* Option 2: Mit Vergleichsansicht-Filter */}
            <label style={{
              display: 'flex', flexDirection: 'column', padding: '12px',
              backgroundColor: exportScope === 'comparison_filter' ? '#e3f2fd' : '#f9f9f9',
              borderRadius: '6px', cursor: 'pointer',
              border: exportScope === 'comparison_filter' ? '2px solid #1976d2' : '2px solid transparent'
            }}>
              <div style={{ display: 'flex', alignItems: 'center' }}>
                <input type="radio" name="exportScope" checked={exportScope === 'comparison_filter'}
                  onChange={() => setExportScope('comparison_filter')} style={{ marginRight: '10px' }} />
                <span style={{ fontWeight: 500 }}>Mit Vergleichsansicht-Filter</span>
              </div>
              {tagFilter ? (
                <span style={{ fontSize: '12px', color: '#1976d2', marginLeft: '24px', marginTop: '4px' }}>
                  Aktive Filter: Tags: {tagFilter}
                </span>
              ) : (
                <span style={{ fontSize: '12px', color: '#999', marginLeft: '24px', marginTop: '4px' }}>
                  Keine Filter aktiv (entspricht "Alle Daten")
                </span>
              )}
            </label>

            {/* Option 3: Benutzerdefiniert */}
            <label style={{
              display: 'flex', flexDirection: 'column', padding: '12px',
              backgroundColor: exportScope === 'custom' ? '#e3f2fd' : '#f9f9f9',
              borderRadius: '6px', cursor: 'pointer',
              border: exportScope === 'custom' ? '2px solid #1976d2' : '2px solid transparent'
            }}>
              <div style={{ display: 'flex', alignItems: 'center' }}>
                <input type="radio" name="exportScope" checked={exportScope === 'custom'}
                  onChange={() => setExportScope('custom')} style={{ marginRight: '10px' }} />
                <span style={{ fontWeight: 500 }}>Benutzerdefiniert</span>
              </div>
              <span style={{ fontSize: '12px', color: '#666', marginLeft: '24px', marginTop: '4px' }}>
                Spezifische Modell-Kombination auswählen
              </span>

              {exportScope === 'custom' && (
                <div style={{ display: 'flex', gap: '12px', marginTop: '12px', marginLeft: '24px' }}
                  onClick={(e) => e.stopPropagation()}>
                  <div style={{ flex: 1 }}>
                    <label style={{ fontSize: '12px', color: '#666' }}>LLM Modell:</label>
                    <select value={exportLlmModel} onChange={(e) => setExportLlmModel(e.target.value)}
                      style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}>
                      <option value="">Alle</option>
                      {availableModels.llm_models.map(m => <option key={m} value={m}>{m}</option>)}
                    </select>
                  </div>
                  <div style={{ flex: 1 }}>
                    <label style={{ fontSize: '12px', color: '#666' }}>Embedding Modell:</label>
                    <select value={exportEmbeddingModel} onChange={(e) => setExportEmbeddingModel(e.target.value)}
                      style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}>
                      <option value="">Alle</option>
                      {availableModels.embedding_models.map(m => <option key={m} value={m}>{m}</option>)}
                    </select>
                  </div>
                </div>
              )}
            </label>
          </div>
        </div>

        {/* Deduplizierung */}
        <div style={{ marginBottom: '20px' }}>
          <h4 style={{ marginBottom: '12px' }}>Deduplizierung:</h4>
          <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={deduplicateLatest}
              onChange={(e) => setDeduplicateLatest(e.target.checked)}
              style={{ marginRight: '10px' }}
            />
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span>Nur neueste Evaluation pro Kombination</span>
              <span style={{ fontSize: '12px', color: '#666' }}>
                Dedupliziert nach (Frage, LLM, Embedding, Graph-Typ, LLM-Evaluator)
              </span>
            </div>
          </label>
        </div>

        {/* Job Status / Progress */}
        {jobId && jobStatus && (
          <div style={{
            padding: '16px',
            backgroundColor: jobStatus.status === 'completed' ? '#e8f5e9' :
                            jobStatus.status === 'failed' ? '#ffebee' : '#e3f2fd',
            borderRadius: '8px',
            marginBottom: '20px'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
              <strong>Status:</strong>
              <span style={{
                padding: '4px 10px',
                borderRadius: '4px',
                backgroundColor: jobStatus.status === 'completed' ? '#4caf50' :
                                jobStatus.status === 'failed' ? '#f44336' :
                                jobStatus.status === 'running' ? '#2196f3' : '#9e9e9e',
                color: 'white',
                fontSize: '12px',
                fontWeight: 500
              }}>
                {jobStatus.status === 'running' ? 'Wird erstellt...' :
                 jobStatus.status === 'completed' ? 'Fertig' :
                 jobStatus.status === 'failed' ? 'Fehlgeschlagen' : jobStatus.status}
              </span>
            </div>
            {jobStatus.progress && (
              <div style={{ fontSize: '14px' }}>
                <div style={{ marginBottom: '4px' }}>
                  Phase: {jobStatus.progress.phase}
                </div>
                <div style={{
                  width: '100%',
                  height: '8px',
                  backgroundColor: '#e0e0e0',
                  borderRadius: '4px',
                  overflow: 'hidden'
                }}>
                  <div style={{
                    width: `${jobStatus.progress.percent}%`,
                    height: '100%',
                    backgroundColor: '#4caf50',
                    transition: 'width 0.3s ease'
                  }} />
                </div>
                <div style={{ fontSize: '12px', color: '#666', marginTop: '4px' }}>
                  {Math.round(jobStatus.progress.percent)}%
                </div>
              </div>
            )}
            {jobStatus.status === 'completed' && jobStatus.file_size_bytes && (
              <div style={{ marginTop: '8px', fontSize: '13px', color: '#666' }}>
                Dateigröße: {(jobStatus.file_size_bytes / 1024).toFixed(1)} KB
              </div>
            )}
            {jobStatus.error && (
              <div style={{ color: '#c62828', marginTop: '8px' }}>
                Fehler: {jobStatus.error}
              </div>
            )}
          </div>
        )}

        {/* Action Buttons */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
          <button
            onClick={onClose}
            style={{
              padding: '10px 20px',
              backgroundColor: '#f5f5f5',
              color: '#333',
              border: '1px solid #ddd',
              borderRadius: '6px',
              cursor: 'pointer',
              fontWeight: 500
            }}
          >
            Schließen
          </button>
          {jobStatus?.status === 'completed' ? (
            <button
              onClick={onDownload}
              style={{
                padding: '10px 24px',
                backgroundColor: '#28a745',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                fontWeight: 'bold',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}
            >
              Herunterladen
            </button>
          ) : (
            <button
              onClick={onStartExport}
              disabled={isLoading}
              style={{
                padding: '10px 24px',
                backgroundColor: isLoading ? '#ccc' : '#28a745',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: isLoading ? 'not-allowed' : 'pointer',
                fontWeight: 'bold',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}
            >
              {isLoading ? 'Wird erstellt...' : 'Export starten'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
