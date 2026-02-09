import { useState, Fragment } from 'react'
import type { EvaluationWithGraphType, AcceptedAnswerInfo } from '../../types'
import { EvaluationTableRow } from './EvaluationTableRow'
import { ExpandedComparison } from './ExpandedComparison'

interface EvaluationTableProps {
  evaluationsByGraphType: Record<string, EvaluationWithGraphType[]>
  referenceAnswer?: AcceptedAnswerInfo
}

type SortColumn = 'config' | 'bert_f1' | 'llm_correctness' | 'time' | 'rating'
type SortOrder = 'asc' | 'desc'

export function EvaluationTable({
  evaluationsByGraphType,
  referenceAnswer
}: EvaluationTableProps) {
  const [expandedEvaluation, setExpandedEvaluation] = useState<number | null>(null)
  const [expandedDocuments, setExpandedDocuments] = useState<Set<string>>(new Set())
  const [sortColumn, setSortColumn] = useState<SortColumn>('bert_f1')
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc')

  // Flatten evaluations from all graph types
  const allEvaluations = Object.values(evaluationsByGraphType).flat()

  // Sort evaluations
  const sortedEvaluations = [...allEvaluations].sort((a, b) => {
    let valueA: number | string | undefined
    let valueB: number | string | undefined

    switch (sortColumn) {
      case 'config':
        valueA = `${a.graph_type}_${a.llm_model || ''}`
        valueB = `${b.graph_type}_${b.llm_model || ''}`
        break
      case 'bert_f1':
        valueA = a.bert_f1 ?? -1
        valueB = b.bert_f1 ?? -1
        break
      case 'llm_correctness':
        valueA = a.llm_correctness_score ?? -1
        valueB = b.llm_correctness_score ?? -1
        break
      case 'time':
        valueA = a.processing_time_ms ?? Infinity
        valueB = b.processing_time_ms ?? Infinity
        break
      case 'rating':
        valueA = a.manual_rating ?? 0
        valueB = b.manual_rating ?? 0
        break
    }

    if (typeof valueA === 'string' && typeof valueB === 'string') {
      return sortOrder === 'asc'
        ? valueA.localeCompare(valueB)
        : valueB.localeCompare(valueA)
    }

    const numA = valueA as number
    const numB = valueB as number

    return sortOrder === 'asc' ? numA - numB : numB - numA
  })

  const handleSort = (column: SortColumn) => {
    if (sortColumn === column) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      setSortColumn(column)
      setSortOrder('desc')
    }
  }

  const toggleExpand = (evaluationId: number) => {
    setExpandedEvaluation(expandedEvaluation === evaluationId ? null : evaluationId)
  }

  const toggleDocument = (evaluationId: number, docIndex: number) => {
    const key = `${evaluationId}-${docIndex}`
    const newExpanded = new Set(expandedDocuments)
    if (newExpanded.has(key)) {
      newExpanded.delete(key)
    } else {
      newExpanded.add(key)
    }
    setExpandedDocuments(newExpanded)
  }

  const SortableHeader = ({
    column,
    label,
    align = 'left'
  }: {
    column: SortColumn
    label: string
    align?: 'left' | 'center' | 'right'
  }) => (
    <th
      style={{
        padding: '12px',
        textAlign: align,
        borderBottom: '2px solid #ddd',
        cursor: 'pointer',
        userSelect: 'none',
        backgroundColor: sortColumn === column ? '#e3f2fd' : '#f5f5f5',
        transition: 'background-color 0.15s ease'
      }}
      onClick={() => handleSort(column)}
    >
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: align === 'center' ? 'center' : 'flex-start',
        gap: '4px'
      }}>
        {label}
        <span style={{ fontSize: '10px', color: sortColumn === column ? '#1976d2' : '#999' }}>
          {sortColumn === column ? (sortOrder === 'asc' ? '▲' : '▼') : '○'}
        </span>
      </div>
    </th>
  )

  if (allEvaluations.length === 0) {
    return (
      <div style={{
        padding: '40px',
        textAlign: 'center',
        backgroundColor: '#f5f5f5',
        borderRadius: '8px',
        color: '#666'
      }}>
        Keine Evaluierungen vorhanden
      </div>
    )
  }

  return (
    <div style={{ marginBottom: '24px' }}>
      <h3 style={{ marginBottom: '12px' }}>
        Alle Evaluierungen ({allEvaluations.length})
        <span style={{ fontSize: '13px', fontWeight: 'normal', color: '#666', marginLeft: '12px' }}>
          Klicke auf eine Zeile für Side-by-Side Vergleich
        </span>
      </h3>
      <div style={{
        border: '1px solid #ddd',
        borderRadius: '8px',
        overflow: 'hidden'
      }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th style={{
                padding: '12px',
                textAlign: 'center',
                borderBottom: '2px solid #ddd',
                backgroundColor: '#f5f5f5',
                width: '50px'
              }}>
                #
              </th>
              <SortableHeader column="config" label="Config" />
              <SortableHeader column="bert_f1" label="BERT F1" align="center" />
              <SortableHeader column="llm_correctness" label="LLM Corr." align="center" />
              <SortableHeader column="time" label="Zeit" align="center" />
              <th style={{
                padding: '12px',
                textAlign: 'center',
                borderBottom: '2px solid #ddd',
                backgroundColor: '#f5f5f5',
                width: '100px'
              }}>
                Aktion
              </th>
            </tr>
          </thead>
          <tbody>
            {sortedEvaluations.map((evaluation, index) => (
              <Fragment key={evaluation.id}>
                <EvaluationTableRow
                  evaluation={evaluation}
                  index={index}
                  isExpanded={expandedEvaluation === evaluation.id}
                  onToggleExpand={() => toggleExpand(evaluation.id)}
                />
                {expandedEvaluation === evaluation.id && (
                  <ExpandedComparison
                    evaluation={evaluation}
                    referenceAnswer={referenceAnswer}
                    expandedDocuments={expandedDocuments}
                    onToggleDocument={(docIndex) => toggleDocument(evaluation.id, docIndex)}
                  />
                )}
              </Fragment>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
