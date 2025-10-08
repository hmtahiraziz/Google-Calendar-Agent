import { useMemo } from 'react'

const STORAGE_KEY = 'ai-calendar-history'

function readHistory() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

function writeHistory(items) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(items))
}

export function addHistoryItem(item) {
  const items = readHistory()
  items.unshift(item)
  writeHistory(items.slice(0, 30))
}

export default function useSchedule() {
  const history = useMemo(() => readHistory(), [])
  return { history }
}

