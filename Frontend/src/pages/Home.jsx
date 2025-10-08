import { Link } from 'react-router-dom'

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-900 via-slate-900 to-slate-800 text-white">
      <section className="mx-auto max-w-6xl px-6 pt-24 pb-16">
        <div className="grid gap-10 md:grid-cols-2 items-center">
          <div>
            <h1 className="text-4xl md:text-6xl font-extrabold tracking-tight">
              Plan smarter with your AI Calendar Agent
            </h1>
            <p className="mt-4 text-slate-300 text-lg">
              Schedule meetings, list events, find free slots, cancel or reschedule — all
              through natural language.
            </p>
            <div className="mt-8 flex items-center gap-4">
              <Link to="/schedule" className="inline-flex items-center rounded-lg bg-indigo-500 px-5 py-3 font-medium hover:bg-indigo-400 transition">
                Get Started
              </Link>
              <Link to="/history" className="inline-flex items-center rounded-lg border border-slate-600 px-5 py-3 font-medium hover:bg-slate-800 transition">
                View History
              </Link>
            </div>
          </div>
          <div className="relative">
            <div className="absolute -inset-4 rounded-2xl bg-indigo-500/20 blur-xl" />
            <div className="relative rounded-2xl border border-slate-700 bg-slate-800/50 p-6">
              <div className="grid grid-cols-7 gap-2 text-center text-sm text-slate-300">
                {[...Array(35)].map((_, i) => (
                  <div key={i} className="aspect-square rounded-md border border-slate-700/60 bg-slate-900/40" />
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}

