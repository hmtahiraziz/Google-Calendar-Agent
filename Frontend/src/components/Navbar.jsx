import { Link } from 'react-router-dom'

export default function Navbar() {
  return (
    <header className="sticky top-0 z-30 border-b border-slate-800 bg-slate-900/80 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-6">
        <Link to="/" className="font-bold tracking-tight text-white">AI Calendar</Link>
        <nav className="flex items-center gap-6 text-slate-300">
          <Link className="hover:text-white" to="/">Home</Link>
          <Link className="hover:text-white" to="/schedule">Schedule</Link>
          <Link className="hover:text-white" to="/history">History</Link>
        </nav>
      </div>
    </header>
  )
}

