import { useState, useEffect, useCallback } from 'react'
import { apiService } from '../../services/api'
import type { ConfigurationStatistics, AggregatedStatisticsResponse } from '../../types'
import { TABLE_COLORS } from '../../theme/tableConstants'
import { MiniMetricBar } from './MiniMetricBar'
import { getGraphTypeName, formatProcessingTime } from './utils'

type GroupByOption = 'graph_type' | 'llm_model' | 'embedding_model'

interface GlobalStatisticsProps {
  defaultExpanded?: boolean
}

type SortColumn = 'config' | 'n' | 'bert_f1' | 'llm_correctness' | 'time'
type SortDirection = 'asc' | 'desc'

export function GlobalStatistics({ defaultExpanded = true }: GlobalStatisticsProps) {
  const [expanded, setExpanded] = useState(defaultExpanded)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<AggregatedStatisticsResponse | null>(null)

  // Grouping options
  const [groupByGraphType, setGroupByGraphType] = useState(true)
  const [groupByLLM, setGroupByLLM] = useState(true)
  const [groupByEmbedding, setGroupByEmbedding] = useState(false)

  // Sorting
  const [sortColumn, setSortColumn] = useState<SortColumn>('n')
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc')

  const loadStatistics = useCallback(async () => {
    const groupBy: GroupByOption[] = []
    if (groupByGraphType) groupBy.push('graph_type')
    if (groupByLLM) groupBy.push('llm_model')
    if (groupByEmbedding) groupBy.push('embedding_model')

    if (groupBy.length === 0) {
      groupBy.push('graph_type')
    }

    setLoading(true)
    setError(null)
    try {
      const result = await apiService.getAggregatedStatistics({ group_by: groupBy })
      setData(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load statistics')
    } finally {
      setLoading(false)
    }
  }, [groupByGraphType, groupByLLM, groupByEmbedding])

  useEffect(() => {
    if (expanded) {
      loadStatistics()
    }
  }, [expanded, loadStatistics])

  const handleSort = (column: SortColumn) => {
    if (sortColumn === column) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setSortColumn(column)
      setSortDirection('desc')
    }
  }

  const sortedStatistics = data?.statistics ? [...data.statistics].sort((a, b) => {
    let aVal: number | string = 0
    let bVal: number | string = 0

    switch (sortColumn) {
      case 'config':
        aVal = getConfigLabel(a, data.group_by)
        bVal = getConfigLabel(b, data.group_by)
        break
      case 'n':
        aVal = a.n
        bVal = b.n
        break
      case 'bert_f1':
        aVal = a.bert_f1_mean ?? -1
        bVal = b.bert_f1_mean ?? -1
        break
      case 'llm_correctness':
        aVal = a.llm_correctness_mean ?? -1
        bVal = b.llm_correctness_mean ?? -1
        break
      case 'time':
        aVal = a.processing_time_ms_mean ?? Infinity
        bVal = b.processing_time_ms_mean ?? Infinity
        break
    }

    if (typeof aVal === 'string' && typeof bVal === 'string') {
      return sortDirection === 'asc'
        ? aVal.localeCompare(bVal)
        : bVal.localeCompare(aVal)
    }

    return sortDirection === 'asc'
      ? (aVal as number) - (bVal as number)
      : (bVal as number) - (aVal as number)
  }) : []


  return (
    <div style={{
      marginBottom: '24px',
      border: '1px solid #ddd',
      borderRadius: '8px',
      overflow: 'hidden'
    }}>
      {/* Header */}
      <div
        onClick={() => setExpanded(!expanded)}
        style={{
          padding: '12px 16px',
          backgroundColor: '#f8f9fa',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          cursor: 'pointer',
          borderBottom: expanded ? '1px solid #ddd' : 'none'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontWeight: 600 }}>
            {expanded ? '\u25BC' : '\u25B6'} Globale Statistiken
          </span>
          {data && (
            <span style={{ color: '#666', fontSize: '14px' }}>
              ({data.total_evaluations} Evaluierungen)
            </span>
          )}
        </div>
      </div>

      {/* Content */}
      {expanded && (
        <div style={{ padding: '16px' }}>
          {/* Grouping Controls */}
          <div style={{
            marginBottom: '16px',
            display: 'flex',
            alignItems: 'center',
            gap: '16px',
            flexWrap: 'wrap'
          }}>
            <span style={{ fontWeight: 500, color: '#666' }}>Gruppieren nach:</span>
            <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={groupByGraphType}
                onChange={(e) => setGroupByGraphType(e.target.checked)}
              />
              Graph-Type
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={groupByLLM}
                onChange={(e) => setGroupByLLM(e.target.checked)}
              />
              + LLM
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={groupByEmbedding}
                onChange={(e) => setGroupByEmbedding(e.target.checked)}
              />
              + Embedding
            </label>
          </div>

          {loading && (
            <div style={{ padding: '20px', textAlign: 'center', color: '#666' }}>
              Lade Statistiken...
            </div>
          )}

          {error && (
            <div style={{ padding: '16px', backgroundColor: '#ffebee', color: '#c62828', borderRadius: '4px' }}>
              {error}
            </div>
          )}

          {!loading && !error && data && (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ backgroundColor: TABLE_COLORS.headerBg }}>
                    <SortableHeader
                      column="config"
                      label="Konfiguration"
                      sortColumn={sortColumn}
                      sortDirection={sortDirection}
                      onSort={handleSort}
                    />
                    <SortableHeader
                      column="n"
                      label="n"
                      sortColumn={sortColumn}
                      sortDirection={sortDirection}
                      onSort={handleSort}
                      align="center"
                    />
                    <SortableHeader
                      column="bert_f1"
                      label="Ø BERT F1"
                      sortColumn={sortColumn}
                      sortDirection={sortDirection}
                      onSort={handleSort}
                      align="center"
                    />
                    <th style={{ padding: '12px', textAlign: 'center', fontWeight: 600 }}>σ</th>
                    <SortableHeader
                      column="llm_correctness"
                      label="Ø LLM Corr."
                      sortColumn={sortColumn}
                      sortDirection={sortDirection}
                      onSort={handleSort}
                      align="center"
                    />
                    <th style={{ padding: '12px', textAlign: 'center', fontWeight: 600 }}>σ</th>
                    <SortableHeader
                      column="time"
                      label="Zeit"
                      sortColumn={sortColumn}
                      sortDirection={sortDirection}
                      onSort={handleSort}
                      align="center"
                    />
                  </tr>
                </thead>
                <tbody>
                  {sortedStatistics.map((stat, idx) => (
                    <tr
                      key={idx}
                      style={{ borderBottom: `1px solid ${TABLE_COLORS.rowBorder}` }}
                    >
                      <td style={{ padding: '12px' }}>
                        <ConfigLabel stat={stat} groupBy={data.group_by} />
                      </td>
                      <td style={{ padding: '12px', textAlign: 'center', fontWeight: 500 }}>
                        {stat.n}
                      </td>
                      <td style={{ padding: '12px', textAlign: 'center' }}>
                        <MiniMetricBar value={stat.bert_f1_mean} type="bert" />
                      </td>
                      <td style={{ padding: '12px', textAlign: 'center', color: '#666', fontSize: '13px' }}>
                        {stat.bert_f1_std !== null && stat.bert_f1_std !== undefined
                          ? `±${stat.bert_f1_std.toFixed(2)}`
                          : '-'}
                      </td>
                      <td style={{ padding: '12px', textAlign: 'center' }}>
                        <MiniMetricBar value={stat.llm_correctness_mean} type="llm" />
                      </td>
                      <td style={{ padding: '12px', textAlign: 'center', color: '#666', fontSize: '13px' }}>
                        {stat.llm_correctness_std !== null && stat.llm_correctness_std !== undefined
                          ? `±${stat.llm_correctness_std.toFixed(2)}`
                          : '-'}
                      </td>
                      <td style={{ padding: '12px', textAlign: 'center' }}>
                        {stat.processing_time_ms_mean !== null && stat.processing_time_ms_mean !== undefined
                          ? formatProcessingTime(stat.processing_time_ms_mean)
                          : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// Helper components

interface SortableHeaderProps {
  column: SortColumn
  label: string
  sortColumn: SortColumn
  sortDirection: SortDirection
  onSort: (column: SortColumn) => void
  align?: 'left' | 'center' | 'right'
}

function SortableHeader({ column, label, sortColumn, sortDirection, onSort, align = 'left' }: SortableHeaderProps) {
  const isActive = sortColumn === column
  return (
    <th
      onClick={() => onSort(column)}
      style={{
        padding: '12px',
        textAlign: align,
        fontWeight: 600,
        cursor: 'pointer',
        userSelect: 'none'
      }}
    >
      {label}
      {isActive && (
        <span style={{ marginLeft: '4px' }}>
          {sortDirection === 'asc' ? '\u25B2' : '\u25BC'}
        </span>
      )}
    </th>
  )
}

function getConfigLabel(stat: ConfigurationStatistics, groupBy: string[]): string {
  const parts: string[] = []

  if (groupBy.includes('graph_type')) {
    parts.push(getGraphTypeName(stat.graph_type))
  }
  if (groupBy.includes('llm_model') && stat.llm_model) {
    parts.push(stat.llm_model)
  }
  if (groupBy.includes('embedding_model') && stat.embedding_model) {
    parts.push(stat.embedding_model)
  }

  return parts.join(' / ') || stat.graph_type
}

interface ConfigLabelProps {
  stat: ConfigurationStatistics
  groupBy: string[]
}

function ConfigLabel({ stat, groupBy }: ConfigLabelProps) {
  const parts: { label: string; type: 'graph' | 'llm' | 'embedding' }[] = []

  if (groupBy.includes('graph_type')) {
    parts.push({ label: getGraphTypeName(stat.graph_type), type: 'graph' })
  }
  if (groupBy.includes('llm_model') && stat.llm_model) {
    parts.push({ label: stat.llm_model, type: 'llm' })
  }
  if (groupBy.includes('embedding_model') && stat.embedding_model) {
    parts.push({ label: stat.embedding_model, type: 'embedding' })
  }

  return (
    <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', alignItems: 'center' }}>
      {parts.map((part, idx) => (
        <span
          key={idx}
          style={{
            padding: '3px 8px',
            borderRadius: '4px',
            fontSize: '13px',
            fontWeight: 500,
            backgroundColor: part.type === 'graph' ? '#e3f2fd' : part.type === 'llm' ? '#fff3e0' : '#f3e5f5',
            color: part.type === 'graph' ? '#1976d2' : part.type === 'llm' ? '#f57c00' : '#7b1fa2'
          }}
        >
          {part.label}
        </span>
      ))}
    </div>
  )
}
