export default function Button({ children, className = '', ...props }) {
  return (
    <button
      className={`inline-flex items-center rounded-lg bg-indigo-500 px-5 py-2.5 font-medium text-white hover:bg-indigo-400 disabled:opacity-60 ${className}`}
      {...props}
    >
      {children}
    </button>
  )
}

