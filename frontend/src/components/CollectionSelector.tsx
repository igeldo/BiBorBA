import React from 'react'
import type { Collection } from '../types'

interface CollectionSelectorProps {
  collections: Collection[]
  selectedIds: number[]
  onSelectionChange: (ids: number[]) => void
  disabled?: boolean
}

export const CollectionSelector: React.FC<CollectionSelectorProps> = ({
  collections,
  selectedIds,
  onSelectionChange,
  disabled = false
}) => {
  const handleToggle = (collectionId: number, checked: boolean) => {
    if (checked) {
      onSelectionChange([...selectedIds, collectionId])
    } else {
      onSelectionChange(selectedIds.filter(id => id !== collectionId))
    }
  }

  return (
    <div className="form-group">
      <label style={{ display: 'block', marginBottom: '8px', fontWeight: 500 }}>
        Collections to Search:
      </label>

      <div style={{
        border: '1px solid #ddd',
        borderRadius: '4px',
        padding: '8px 12px',
        maxHeight: '200px',
        overflowY: 'auto',
        backgroundColor: '#fff',
        display: 'inline-block',
        minWidth: '300px'
      }}>
        {collections.length === 0 ? (
          <div style={{ color: '#666', fontStyle: 'italic', fontSize: '14px' }}>
            No collections available. Create collections in the Collection Management tab.
          </div>
        ) : (
          collections.map((collection, index) => (
            <div key={collection.id} style={{ marginBottom: index < collections.length - 1 ? '6px' : 0 }}>
              <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer', gap: '8px' }}>
                <input
                  type="checkbox"
                  checked={selectedIds.includes(collection.id)}
                  onChange={(e) => handleToggle(collection.id, e.target.checked)}
                  disabled={disabled}
                  style={{ width: 'auto', margin: 0, flexShrink: 0 }}
                />
                <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span>{collection.name}</span>
                  <span style={{
                    padding: '2px 6px',
                    borderRadius: '3px',
                    fontSize: '0.85em',
                    backgroundColor: collection.collection_type === 'pdf' ? '#e3f2fd' : '#f3e5f5',
                    color: collection.collection_type === 'pdf' ? '#1976d2' : '#7b1fa2'
                  }}>
                    {collection.collection_type}
                  </span>
                  <span style={{ color: '#666', fontSize: '0.9em' }}>
                    ({collection.question_count} items)
                  </span>
                </span>
              </label>
            </div>
          ))
        )}
      </div>

      {selectedIds.length > 0 && (
        <div style={{ marginTop: '8px', fontSize: '0.9em', color: '#666' }}>
          {selectedIds.length} collection(s) selected
        </div>
      )}

      {selectedIds.length === 0 && (
        <div style={{ marginTop: '8px', fontSize: '0.9em', color: '#999', fontStyle: 'italic' }}>
          Select at least one collection for retrieval
        </div>
      )}
    </div>
  )
}
