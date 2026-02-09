import React from 'react'
import type { ViewType } from '../../types'

interface ViewSwitcherProps {
  currentView: ViewType
  onViewChange: (view: ViewType) => void
}

interface ViewButton {
  id: ViewType
  label: string
  matchViews?: ViewType[] // Additional views that should show this button as active
}

const VIEW_BUTTONS: ViewButton[] = [
  { id: 'query', label: 'Abfragemodus' },
  { id: 'data', label: 'SO-Datenverwaltung' },
  { id: 'collection-management', label: 'Collectionsverwaltung' },
  { id: 'batch-queries', label: 'Batch-Verarbeitung', matchViews: ['batch-progress'] },
  { id: 'missing-questions', label: 'Fehlende Fragen' },
  { id: 'comparison', label: 'Antworten-Vergleich' }
]

export const ViewSwitcher: React.FC<ViewSwitcherProps> = ({
  currentView,
  onViewChange
}) => {
  const isActive = (button: ViewButton): boolean => {
    if (currentView === button.id) return true
    if (button.matchViews?.includes(currentView)) return true
    return false
  }

  return (
    <div style={{
      marginTop: '20px',
      display: 'flex',
      gap: '10px',
      justifyContent: 'center',
      flexWrap: 'wrap'
    }}>
      {VIEW_BUTTONS.map((button) => (
        <button
          key={button.id}
          className={`button ${isActive(button) ? 'active' : ''}`}
          onClick={() => onViewChange(button.id)}
          style={{
            background: isActive(button) ? '#0056b3' : '#6c757d'
          }}
        >
          {button.label}
        </button>
      ))}
    </div>
  )
}
