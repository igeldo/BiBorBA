import React from 'react'
import { TABLE_PAGE_SIZES, TABLE_COLORS } from '../../theme/tableConstants'

interface TablePaginationProps {
  page: number
  pageSize: number
  totalItems: number
  totalPages: number
  hasNext: boolean
  hasPrev: boolean
  onPageChange: (page: number) => void
  onPageSizeChange: (size: number) => void
  pageSizeOptions?: readonly number[]
  showFirstLast?: boolean
}

export const TablePagination: React.FC<TablePaginationProps> = ({
  page,
  pageSize,
  totalItems,
  totalPages,
  hasNext,
  hasPrev,
  onPageChange,
  onPageSizeChange,
  pageSizeOptions = TABLE_PAGE_SIZES,
  showFirstLast = true
}) => {
  const startItem = totalItems > 0 ? (page - 1) * pageSize + 1 : 0
  const endItem = Math.min(page * pageSize, totalItems)

  const buttonStyle = (enabled: boolean): React.CSSProperties => ({
    padding: '8px 16px',
    backgroundColor: enabled ? TABLE_COLORS.buttonSecondary : TABLE_COLORS.buttonDisabled,
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    cursor: enabled ? 'pointer' : 'not-allowed',
    fontSize: '13px',
    fontWeight: 500
  })

  return (
    <div style={{
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      padding: '12px 16px',
      backgroundColor: '#f8f9fa',
      borderRadius: '8px',
      marginTop: '16px'
    }}>
      {/* Info Section */}
      <div style={{ fontSize: '14px', color: '#666' }}>
        {totalItems > 0
          ? `Zeige ${startItem} - ${endItem} von ${totalItems}`
          : 'Keine Elemente'}
        {' | '}
        Page {page} of {totalPages || 1}
      </div>

      {/* Controls Section */}
      <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
        {showFirstLast && (
          <button
            onClick={() => onPageChange(1)}
            disabled={!hasPrev}
            style={buttonStyle(hasPrev)}
          >
            Erste
          </button>
        )}

        <button
          onClick={() => onPageChange(page - 1)}
          disabled={!hasPrev}
          style={buttonStyle(hasPrev)}
        >
          Zurück
        </button>

        <select
          value={pageSize}
          onChange={(e) => onPageSizeChange(Number(e.target.value))}
          style={{
            padding: '8px 12px',
            borderRadius: '4px',
            border: '1px solid #ddd',
            fontSize: '13px'
          }}
        >
          {pageSizeOptions.map(size => (
            <option key={size} value={size}>
              {size} pro Seite
            </option>
          ))}
        </select>

        <button
          onClick={() => onPageChange(page + 1)}
          disabled={!hasNext}
          style={buttonStyle(hasNext)}
        >
          Weiter
        </button>

        {showFirstLast && (
          <button
            onClick={() => onPageChange(totalPages)}
            disabled={!hasNext}
            style={buttonStyle(hasNext)}
          >
            Letzte
          </button>
        )}
      </div>
    </div>
  )
}
