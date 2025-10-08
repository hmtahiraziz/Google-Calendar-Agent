import { useEffect, useState } from 'react'
import useSchedule from '../hooks/useSchedule'

export default function History() {
  const { history } = useSchedule()
  const [items, setItems] = useState([])

  useEffect(() => {
    setItems(history)
  }, [history])

  return (
    <div className="min-h-screen bg-slate-900 text-white">
      <div className="mx-auto max-w-3xl px-6 py-10">
        <h2 className="text-3xl font-bold">Recent requests</h2>
        <p className="mt-2 text-slate-300">Local-only log of your last actions.</p>
        <div className="mt-6 space-y-3">
          {items.length === 0 && (
            <p className="text-slate-400">No history yet.</p>
          )}
          {items.map((item, idx) => (
            <div key={idx} className="rounded-lg border border-slate-700 bg-slate-800/50 p-3">
              <div className="text-slate-300 text-sm">{new Date(item.ts).toLocaleString()}</div>
              <div className="mt-1 font-medium">{item.query}</div>
              {item.response && (
                <pre className="mt-2 whitespace-pre-wrap text-slate-200">{item.response}</pre>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

