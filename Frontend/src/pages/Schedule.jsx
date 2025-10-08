import { useState } from 'react'
import useApi from '../hooks/useApi'
import useToast from '../hooks/useToast'
import { addHistoryItem } from '../hooks/useSchedule'

export default function Schedule() {
  const { post, loading } = useApi()
  const { show, Toast } = useToast()
  const [query, setQuery] = useState('Schedule standup with team tomorrow 10:00')
  const [response, setResponse] = useState('')

  async function handleSubmit(e) {
    e.preventDefault()
    const res = await post('/ask', { query })
    if (res?.response) {
      setResponse(res.response)
      show('Request completed')
      addHistoryItem({ query, response: res.response, ts: Date.now() })
    } else {
      show('Something went wrong')
    }
  }

  return (
    <div className="min-h-screen bg-slate-900 text-white">
      <div className="mx-auto max-w-3xl px-6 py-10">
        <h2 className="text-3xl font-bold">Ask your Calendar Agent</h2>
        <p className="mt-2 text-slate-300">Describe what you want to do in plain English.</p>

        <form onSubmit={handleSubmit} className="mt-8 space-y-4">
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full min-h-32 rounded-xl border border-slate-700 bg-slate-800/60 p-4 outline-none ring-0 focus:border-indigo-500"
            placeholder="e.g., Create a meeting with John on 2025-10-10 at 14:00"
          />
          <div className="flex items-center gap-3">
            <button
              type="submit"
              disabled={loading}
              className="inline-flex items-center rounded-lg bg-indigo-500 px-5 py-2.5 font-medium hover:bg-indigo-400 disabled:opacity-60"
            >
              {loading ? 'Working…' : 'Send'}
            </button>
            <a href="/history" className="text-slate-300 hover:text-white">View history</a>
          </div>
        </form>

        {response && (
          <div className="mt-8 rounded-xl border border-slate-700 bg-slate-800/50 p-4">
            <h3 className="font-semibold mb-2">Agent response</h3>
            <pre className="whitespace-pre-wrap text-slate-200">{response}</pre>
          </div>
        )}
      </div>
      <Toast />
    </div>
  )
}

