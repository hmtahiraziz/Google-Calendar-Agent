import { useState } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'

export default function useApi() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  async function request(path, options = {}) {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API_BASE}${path}`, {
        headers: { 'Content-Type': 'application/json' },
        ...options,
      })
      const data = await res.json().catch(() => null)
      if (!res.ok) throw new Error(data?.detail || 'Request failed')
      return data
    } catch (e) {
      setError(e)
      return null
    } finally {
      setLoading(false)
    }
  }

  function get(path) {
    return request(path)
  }

  function post(path, body) {
    return request(path, { method: 'POST', body: JSON.stringify(body) })
  }

  return { get, post, loading, error }
}

