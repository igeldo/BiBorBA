import React, { useState, useEffect } from 'react'
import { apiService } from '../services/api'

interface RatingStarsProps {
  // Query mode (existing)
  sessionId?: string
  // Evaluation mode (for comparison view)
  evaluationId?: number
  // Initial rating (for showing existing rating)
  initialRating?: number
  // Callback when rating is submitted
  onRatingSubmit?: (rating: number) => void
  // Compact mode for smaller UI
  compact?: boolean
}

export const RatingStars: React.FC<RatingStarsProps> = ({
  sessionId,
  evaluationId,
  initialRating,
  onRatingSubmit,
  compact = false
}) => {
  const [userRating, setUserRating] = useState(initialRating || 0)
  const [hoverRating, setHoverRating] = useState(0)
  const [submitted, setSubmitted] = useState(!!initialRating)
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Update state when initialRating changes
  useEffect(() => {
    if (initialRating) {
      setUserRating(initialRating)
      setSubmitted(true)
    }
  }, [initialRating])

  const handleSubmit = async (rating: number) => {
    // Validate that we have either sessionId or evaluationId
    if (!sessionId && !evaluationId) {
      setError('No query or evaluation to rate')
      return
    }

    setIsSubmitting(true)
    try {
      if (evaluationId) {
        // Evaluation mode
        await apiService.rateEvaluation(evaluationId, rating)
      } else if (sessionId) {
        // Query mode (existing behavior)
        await apiService.rateQuery(sessionId, rating)
      }
      setUserRating(rating)
      setSubmitted(true)
      setError(null)
      onRatingSubmit?.(rating)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save rating')
    } finally {
      setIsSubmitting(false)
    }
  }

  // Compact mode styles
  const containerStyle = compact ? {
    padding: '8px',
    backgroundColor: submitted ? '#e8f5e9' : 'transparent',
    borderRadius: '4px',
    display: 'inline-flex',
    alignItems: 'center',
    gap: '8px'
  } : {
    marginTop: '20px',
    padding: '15px',
    backgroundColor: submitted ? '#e8f5e9' : '#f8f9fa',
    borderRadius: '8px',
    border: `1px solid ${submitted ? '#4caf50' : '#dee2e6'}`,
    textAlign: 'center' as const
  }

  const starSize = compact ? '20px' : '28px'

  return (
    <div style={containerStyle}>
      {!compact && (
        <h4 style={{
          marginBottom: '12px',
          fontSize: '15px',
          fontWeight: 600,
          color: '#495057'
        }}>
          {submitted ? 'Bewertet!' : 'Antwort bewerten'}
        </h4>
      )}
      <div style={{ display: 'flex', justifyContent: 'center', gap: compact ? '4px' : '8px', marginBottom: compact ? 0 : '8px' }}>
        {[1, 2, 3, 4, 5].map((star) => (
          <button
            key={star}
            onClick={() => !submitted && !isSubmitting && handleSubmit(star)}
            onMouseEnter={() => !submitted && !isSubmitting && setHoverRating(star)}
            onMouseLeave={() => !submitted && !isSubmitting && setHoverRating(0)}
            disabled={submitted || isSubmitting}
            style={{
              background: 'none',
              border: 'none',
              cursor: (submitted || isSubmitting) ? 'default' : 'pointer',
              fontSize: starSize,
              padding: compact ? '2px' : '4px',
              transition: 'transform 0.2s',
              transform: (hoverRating >= star || userRating >= star) && !submitted ? 'scale(1.2)' : 'scale(1)',
              opacity: (submitted || isSubmitting) ? 0.8 : 1
            }}
          >
            {(hoverRating >= star || userRating >= star) ? '★' : '☆'}
          </button>
        ))}
      </div>
      {!compact && userRating > 0 && submitted && (
        <div style={{ fontSize: '13px', color: '#388e3c' }}>
          Bewertung: {userRating}/5 Sterne
        </div>
      )}
      {isSubmitting && (
        <div style={{ fontSize: '12px', color: '#666', marginTop: compact ? 0 : '8px' }}>
          Speichere...
        </div>
      )}
      {error && (
        <div style={{ fontSize: compact ? '11px' : '13px', color: '#d32f2f', marginTop: compact ? 0 : '8px' }}>
          {error}
        </div>
      )}
    </div>
  )
}
