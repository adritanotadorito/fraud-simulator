export default function TopBar({ title, subtitle }) {
  return (
    <header className="flex shrink-0 items-center justify-between border-b border-border bg-panel/50 px-6 py-4">
      <div>
        <h1 className="font-sans text-lg font-bold tracking-tight text-text">{title}</h1>
        {subtitle && <p className="mt-0.5 text-xs text-text-muted">{subtitle}</p>}
      </div>
      <div className="flex items-center gap-3 font-mono text-xs text-text-dim">
        <span className="rounded-md border border-border bg-panel px-2.5 py-1 text-[11px] text-text-muted">
          Env: <strong className="text-text font-medium">Production Risk Ops</strong>
        </span>
        <span>
          {new Date().toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })}
        </span>
      </div>
    </header>
  )
}
