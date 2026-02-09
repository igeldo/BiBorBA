import React from 'react'
import { TABLE_COLORS } from '../../theme/tableConstants'

interface StackOverflowLinkProps {
  stackOverflowId: number
  title?: string
  showId?: boolean
}

export const StackOverflowLink: React.FC<StackOverflowLinkProps> = ({
  stackOverflowId,
  title,
  showId = false
}) => {
  const displayText = title || stackOverflowId.toString()
  const url = `https://stackoverflow.com/questions/${stackOverflowId}`

  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      style={{
        color: TABLE_COLORS.link,
        textDecoration: 'none'
      }}
      title={`View on StackOverflow (ID: ${stackOverflowId})`}
    >
      {showId && title ? `${displayText} (${stackOverflowId})` : displayText}
    </a>
  )
}
