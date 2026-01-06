/**
 * Builds URLSearchParams from an object, filtering out undefined/null values
 */
export function buildSearchParams(params: Record<string, unknown>): URLSearchParams {
  const searchParams = new URLSearchParams()

  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      searchParams.set(key, String(value))
    }
  })

  return searchParams
}

/**
 * Builds a query string from params, returning empty string if no params
 */
export function buildQueryString(params: Record<string, unknown>): string {
  const searchParams = buildSearchParams(params)
  const str = searchParams.toString()
  return str ? `?${str}` : ''
}
