import React from 'react'
import { TABLE_COLORS } from '../../theme/tableConstants'

interface SortableHeaderProps {
  column: string
  label: string
  sortBy: string
  sortOrder: 'asc' | 'desc'
  onSort: (column: string) => void
  align?: 'left' | 'center' | 'right'
  width?: string
}

export const SortableHeader: React.FC<SortableHeaderProps> = ({
  column,
  label,
  sortBy,
  sortOrder,
  onSort,
  align = 'left',
  width
}) => {
  const isActive = sortBy === column
  const indicator = isActive ? (sortOrder === 'desc' ? ' ▼' : ' ▲') : ''

  return (
    <th
      onClick={() => onSort(column)}
      style={{
        padding: '12px',
        textAlign: align,
        borderBottom: `2px solid ${TABLE_COLORS.headerBorder}`,
        cursor: 'pointer',
        userSelect: 'none',
        backgroundColor: isActive ? TABLE_COLORS.selectedRow : undefined,
        width,
        transition: 'background-color 0.2s'
      }}
      onMouseEnter={(e) => {
        if (!isActive) {
          e.currentTarget.style.backgroundColor = TABLE_COLORS.hoverRow
        }
      }}
      onMouseLeave={(e) => {
        if (!isActive) {
          e.currentTarget.style.backgroundColor = ''
        }
      }}
    >
      {label}{indicator}
    </th>
  )
}

/**
 * Non-sortable header cell with consistent styling
 */
interface HeaderCellProps {
  children: React.ReactNode
  align?: 'left' | 'center' | 'right'
  width?: string
}

export const HeaderCell: React.FC<HeaderCellProps> = ({
  children,
  align = 'left',
  width
}) => (
  <th
    style={{
      padding: '12px',
      textAlign: align,
      borderBottom: `2px solid ${TABLE_COLORS.headerBorder}`,
      width
    }}
  >
    {children}
  </th>
)
