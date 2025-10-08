export default function Footer() {
  return (
    <footer className="border-t border-slate-800 bg-slate-900 text-slate-400">
      <div className="mx-auto max-w-6xl px-6 py-6 text-sm">
        <span>© {new Date().getFullYear()} AI Calendar Agent</span>
      </div>
    </footer>
  )
}

