import type { EvaluatedQuestionListItem } from '../../types'
import { SortableHeader, HeaderCell, TablePagination, StackOverflowLink, TagList } from '../table'
import { TABLE_PAGE_SIZES, TABLE_COLORS, getScoreDisplayColor } from '../../theme/tableConstants'
import { ArchitectureMetricsCell } from './ArchitectureMetricsCell'

interface QuestionListProps {
  items: EvaluatedQuestionListItem[]
  selectedQuestionId: number | null
  sortBy: string
  sortOrder: 'asc' | 'desc'
  onSort: (column: string) => void
  onSelectQuestion: (questionId: number) => void
  // Pagination
  page: number
  pageSize: number
  totalItems: number
  totalPages: number
  hasNext: boolean
  hasPrev: boolean
  onPageChange: (page: number) => void
  onPageSizeChange: (size: number) => void
}

export function QuestionList({
  items,
  selectedQuestionId,
  sortBy,
  sortOrder,
  onSort,
  onSelectQuestion,
  page,
  pageSize,
  totalItems,
  totalPages,
  hasNext,
  hasPrev,
  onPageChange,
  onPageSizeChange
}: QuestionListProps) {
  return (
    <>
      <div style={{
        border: '1px solid #ddd',
        borderRadius: '8px',
        overflow: 'hidden'
      }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ backgroundColor: TABLE_COLORS.headerBg }}>
              <HeaderCell>Titel</HeaderCell>
              <SortableHeader
                column="score"
                label="Score"
                sortBy={sortBy}
                sortOrder={sortOrder}
                onSort={onSort}
                align="center"
              />
              <SortableHeader
                column="adaptive_rag_f1"
                label="Adaptive RAG"
                sortBy={sortBy}
                sortOrder={sortOrder}
                onSort={onSort}
                align="center"
              />
              <SortableHeader
                column="simple_rag_f1"
                label="Simple RAG"
                sortBy={sortBy}
                sortOrder={sortOrder}
                onSort={onSort}
                align="center"
              />
              <SortableHeader
                column="pure_llm_f1"
                label="Pure LLM"
                sortBy={sortBy}
                sortOrder={sortOrder}
                onSort={onSort}
                align="center"
              />
              <SortableHeader
                column="evaluation_count"
                label="Evals"
                sortBy={sortBy}
                sortOrder={sortOrder}
                onSort={onSort}
                align="center"
              />
              <HeaderCell>Aktion</HeaderCell>
            </tr>
          </thead>
          <tbody>
            {items.map((question) => (
              <tr
                key={question.question_id}
                style={{
                  backgroundColor: selectedQuestionId === question.question_id ? TABLE_COLORS.selectedRow : 'white',
                  borderBottom: `1px solid ${TABLE_COLORS.rowBorder}`
                }}
              >
                <td style={{ padding: '12px', maxWidth: '350px' }}>
                  <div style={{ fontWeight: 500, marginBottom: '4px' }}>
                    <StackOverflowLink
                      stackOverflowId={question.question_id}
                      title={question.question_title}
                    />
                  </div>
                  {question.tags.length > 0 && (
                    <TagList tags={question.tags} maxTags={3} />
                  )}
                </td>
                <td style={{ padding: '12px', textAlign: 'center', fontWeight: 500, color: getScoreDisplayColor(question.score) }}>
                  {question.score}
                </td>
                <td style={{ padding: '12px', textAlign: 'center' }}>
                  <ArchitectureMetricsCell
                    metrics={question.metrics_by_architecture?.adaptive_rag}
                  />
                </td>
                <td style={{ padding: '12px', textAlign: 'center' }}>
                  <ArchitectureMetricsCell
                    metrics={question.metrics_by_architecture?.simple_rag}
                  />
                </td>
                <td style={{ padding: '12px', textAlign: 'center' }}>
                  <ArchitectureMetricsCell
                    metrics={question.metrics_by_architecture?.pure_llm}
                  />
                </td>
                <td style={{ padding: '12px', textAlign: 'center' }}>{question.total_evaluations}</td>
                <td style={{ padding: '12px' }}>
                  <button
                    onClick={() => onSelectQuestion(question.question_id)}
                    style={{
                      padding: '6px 12px',
                      backgroundColor: TABLE_COLORS.buttonPrimary,
                      color: 'white',
                      border: 'none',
                      borderRadius: '4px',
                      cursor: 'pointer',
                      fontSize: '14px'
                    }}
                  >
                    Vergleichen
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination Controls */}
      <TablePagination
        page={page}
        pageSize={pageSize}
        totalItems={totalItems}
        totalPages={totalPages}
        hasNext={hasNext}
        hasPrev={hasPrev}
        onPageChange={onPageChange}
        onPageSizeChange={onPageSizeChange}
        pageSizeOptions={TABLE_PAGE_SIZES}
      />
    </>
  )
}
