// Utility functions for UI formatting

export const formatNodeName = (nodeName: string): string => {
  return nodeName
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

export const getNodeDescription = (nodeName: string): string => {
  const descriptions: Record<string, string> = {
    'retrieve': 'Retrieved relevant documents from the vector store',
    'grade_documents': 'Evaluated document relevance to the question',
    'generate': 'Generated answer based on retrieved documents',
    'transform_query': 'Optimized the question for better retrieval',
    'hallucination_grader': 'Verified answer is grounded in facts',
    'answer_grader': 'Checked if answer addresses the question'
  }
  return descriptions[nodeName] || 'Processed step in the pipeline'
}

export const getSourceColor = (source: string): string => {
  const colors: Record<string, string> = {
    'pdf': '#007bff',
    'stackoverflow': '#f48024',
  }
  return colors[source.toLowerCase()] || '#6c757d'
}

export const getBertScoreColor = (score: number): string => {
  if (score >= 0.9) return '#28a745'
  if (score >= 0.8) return '#5cb85c'
  if (score >= 0.7) return '#ffc107'
  if (score >= 0.6) return '#fd7e14'
  return '#dc3545'
}

export const formatCollectionName = (type: string): string => {
  const names: Record<string, string> = {
    'pdf': 'PDF Dokumente',
    'stackoverflow': 'StackOverflow'
  }
  return names[type] || type
}
