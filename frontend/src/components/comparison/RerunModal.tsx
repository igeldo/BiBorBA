import type { Collection, BatchQueryJobStatus } from '../../types'
import { getGraphTypeBadgeColor, getGraphTypeName } from './utils'

interface RerunModalProps {
  isOpen: boolean
  onClose: () => void
  questionTitle: string
  selectedGraphTypes: string[]
  onToggleGraphType: (graphType: string) => void
  selectedCollections: number[]
  onToggleCollection: (collectionId: number) => void
  availableCollections: Collection[]
  jobId: string | null
  jobStatus: BatchQueryJobStatus | null
  isLoading: boolean
  onStartRerun: () => void
}

export function RerunModal({
  isOpen,
  onClose,
  questionTitle,
  selectedGraphTypes,
  onToggleGraphType,
  selectedCollections,
  onToggleCollection,
  availableCollections,
  jobId,
  jobStatus,
  isLoading,
  onStartRerun
}: RerunModalProps) {
  if (!isOpen) return null

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
          <h2 style={{ margin: 0 }}>Frage erneut ausführen</h2>
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

        <div style={{
          padding: '12px',
          backgroundColor: '#f5f5f5',
          borderRadius: '6px',
          marginBottom: '20px',
          fontSize: '14px'
        }}>
          <strong>Frage:</strong> {questionTitle}
        </div>

        {/* Graph Types Selection */}
        <div style={{ marginBottom: '20px' }}>
          <h4 style={{ marginBottom: '12px' }}>Graph-Typen auswählen:</h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {['adaptive_rag', 'simple_rag', 'pure_llm'].map((graphType) => {
              const colors = getGraphTypeBadgeColor(graphType)
              return (
                <label
                  key={graphType}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    padding: '10px 12px',
                    backgroundColor: selectedGraphTypes.includes(graphType) ? colors.bg : '#f9f9f9',
                    borderRadius: '6px',
                    cursor: 'pointer',
                    border: selectedGraphTypes.includes(graphType) ? `2px solid ${colors.color}` : '2px solid transparent'
                  }}
                >
                  <input
                    type="checkbox"
                    checked={selectedGraphTypes.includes(graphType)}
                    onChange={() => onToggleGraphType(graphType)}
                    style={{ marginRight: '10px' }}
                  />
                  <span style={{
                    padding: '4px 10px',
                    backgroundColor: colors.bg,
                    color: colors.color,
                    borderRadius: '4px',
                    fontWeight: 500
                  }}>
                    {getGraphTypeName(graphType)}
                  </span>
                </label>
              )
            })}
          </div>
          {selectedGraphTypes.length === 0 && (
            <div style={{ color: '#d32f2f', fontSize: '12px', marginTop: '8px' }}>
              Mindestens ein Graph-Typ muss ausgewählt werden
            </div>
          )}
        </div>

        {/* Collections Selection */}
        <div style={{ marginBottom: '20px' }}>
          <h4 style={{ marginBottom: '12px' }}>
            Collections (optional):
            <span style={{ fontWeight: 'normal', fontSize: '12px', color: '#666', marginLeft: '8px' }}>
              Leer = StackOverflow Retriever
            </span>
          </h4>
          {availableCollections.length === 0 ? (
            <div style={{ color: '#666', fontStyle: 'italic', fontSize: '14px' }}>
              Keine Collections verfügbar
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', maxHeight: '150px', overflowY: 'auto' }}>
              {availableCollections.map((collection) => (
                <label
                  key={collection.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    padding: '8px 12px',
                    backgroundColor: selectedCollections.includes(collection.id) ? '#e3f2fd' : '#f9f9f9',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    border: selectedCollections.includes(collection.id) ? '1px solid #1976d2' : '1px solid transparent'
                  }}
                >
                  <input
                    type="checkbox"
                    checked={selectedCollections.includes(collection.id)}
                    onChange={() => onToggleCollection(collection.id)}
                    style={{ marginRight: '10px' }}
                  />
                  <span style={{ flex: 1 }}>
                    {collection.name}
                    <span style={{ fontSize: '12px', color: '#666', marginLeft: '8px' }}>
                      ({collection.question_count} Fragen)
                    </span>
                  </span>
                </label>
              ))}
            </div>
          )}
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
                {jobStatus.status === 'running' ? 'Läuft...' :
                 jobStatus.status === 'completed' ? 'Abgeschlossen' :
                 jobStatus.status === 'failed' ? 'Fehlgeschlagen' : jobStatus.status}
              </span>
            </div>
            {jobStatus.progress && (
              <div style={{ fontSize: '14px' }}>
                <div style={{ marginBottom: '4px' }}>
                  Fortschritt: {jobStatus.progress.processed} / {jobStatus.progress.total_questions}
                </div>
                {jobStatus.progress.successful > 0 && (
                  <div style={{ color: '#4caf50' }}>
                    Erfolgreich: {jobStatus.progress.successful}
                  </div>
                )}
                {jobStatus.progress.failed > 0 && (
                  <div style={{ color: '#f44336' }}>
                    Fehlgeschlagen: {jobStatus.progress.failed}
                  </div>
                )}
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
            {jobStatus?.status === 'completed' ? 'Schließen' : 'Abbrechen'}
          </button>
          {(!jobId || jobStatus?.status === 'completed') && (
            <button
              onClick={onStartRerun}
              disabled={selectedGraphTypes.length === 0 || isLoading}
              style={{
                padding: '10px 24px',
                backgroundColor: selectedGraphTypes.length === 0 || isLoading ? '#ccc' : '#ff9800',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: selectedGraphTypes.length === 0 || isLoading ? 'not-allowed' : 'pointer',
                fontWeight: 'bold',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}
            >
              {isLoading ? 'Wird ausgeführt...' : jobStatus?.status === 'completed' ? 'Erneut starten' : 'Ausführen'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
