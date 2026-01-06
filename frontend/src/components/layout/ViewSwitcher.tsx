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
  { id: 'query', label: 'Query Mode' },
  { id: 'data', label: 'SO Data Management' },
  { id: 'collection-management', label: 'Collection Management' },
  { id: 'batch-queries', label: 'Batch Processing', matchViews: ['batch-progress'] },
  { id: 'comparison', label: 'Graph Comparison' }
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
