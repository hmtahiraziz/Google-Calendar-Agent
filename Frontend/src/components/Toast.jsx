import { useEffect } from 'react'

export default function Toast({ message, visible, onHide }) {
  useEffect(() => {
    if (!visible) return
    const id = setTimeout(onHide, 2000)
    return () => clearTimeout(id)
  }, [visible, onHide])

  if (!visible) return null

  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 rounded-lg bg-slate-800 px-4 py-2 text-white shadow-xl ring-1 ring-slate-700">
      {message}
    </div>
  )
}

