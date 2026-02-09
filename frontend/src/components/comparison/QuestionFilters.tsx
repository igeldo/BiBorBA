interface QuestionFiltersProps {
  titleSearch: string
  setTitleSearch: (value: string) => void
  tagFilter: string
  setTagFilter: (value: string) => void
  onSearch: () => void
}

export function QuestionFilters({
  titleSearch,
  setTitleSearch,
  tagFilter,
  setTagFilter,
  onSearch
}: QuestionFiltersProps) {
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      onSearch()
    }
  }

  return (
    <div style={{
      display: 'flex',
      gap: '15px',
      padding: '15px',
      backgroundColor: '#f8f9fa',
      borderRadius: '8px',
      marginBottom: '16px',
      alignItems: 'flex-end'
    }}>
      <div style={{ flex: 1 }}>
        <label style={{ display: 'block', marginBottom: '4px', fontSize: '12px', color: '#666' }}>
          Titel suchen:
        </label>
        <input
          type="text"
          value={titleSearch}
          onChange={(e) => setTitleSearch(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="z.B. SQL query, JOIN"
          style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
        />
      </div>

      <div style={{ flex: 1 }}>
        <label style={{ display: 'block', marginBottom: '4px', fontSize: '12px', color: '#666' }}>
          Tags filtern:
        </label>
        <input
          type="text"
          value={tagFilter}
          onChange={(e) => setTagFilter(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="z.B. sql, postgresql"
          style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
        />
      </div>

      <button
        onClick={onSearch}
        style={{
          padding: '8px 16px',
          backgroundColor: '#007bff',
          color: 'white',
          border: 'none',
          borderRadius: '4px',
          cursor: 'pointer'
        }}
      >
        Suchen
      </button>
    </div>
  )
}
