import React from 'react'
import { formatNodeName, getNodeDescription } from '../utils/formatting'

interface GraphTraceProps {
  graphTrace: string[]
  nodeTimings?: Record<string, number>
}

export const GraphTrace: React.FC<GraphTraceProps> = ({ graphTrace, nodeTimings }) => {
  if (!graphTrace || graphTrace.length === 0) {
    return null
  }

  return (
    <div className="graph-trace-section">
      <h3>🔍 Processing Pipeline</h3>
      <p className="trace-description">
        The system executed the following steps to generate this answer:
      </p>
      <div className="graph-trace">
        {graphTrace.map((node, index) => (
          <React.Fragment key={index}>
            <div className="trace-node">
              <div className="trace-node-number">{index + 1}</div>
              <div className="trace-node-content">
                <div className="trace-node-name">
                  {formatNodeName(node)}
                  {nodeTimings && nodeTimings[node] !== undefined && (
                    <span style={{
                      marginLeft: '8px',
                      fontSize: '11px',
                      color: '#666',
                      fontWeight: 'normal',
                      backgroundColor: '#f0f0f0',
                      padding: '2px 6px',
                      borderRadius: '3px'
                    }}>
                      {nodeTimings[node].toFixed(0)}ms
                    </span>
                  )}
                </div>
                <div className="trace-node-description">{getNodeDescription(node)}</div>
              </div>
            </div>
            {index < graphTrace.length - 1 && (
              <div className="trace-arrow">→</div>
            )}
          </React.Fragment>
        ))}
      </div>
    </div>
  )
}
