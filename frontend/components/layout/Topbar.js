import ThemeToggle from '../ThemeToggle'

export default function Topbar() {
  return (
    <header className="sticky top-0 z-20 border-b border-(--border) bg-[color-mix(in_srgb,var(--surface)_86%,transparent)] backdrop-blur-md">
      <div className="mx-auto max-w-[1600px] px-4 py-4 sm:px-6 flex flex-wrap gap-4 items-center justify-between">
        <div className="min-w-0">
          <div className="label">Enterprise Cost Intelligence</div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight">AI Copilot Command Center</h1>
          <p className="text-xs sm:text-sm text-(--text-muted) mt-1">Cross-domain anomaly intelligence with governed action flow</p>
        </div>
        <div className="flex items-center gap-2 flex-wrap justify-end">
          <span className="pill">
            <span className="h-2 w-2 rounded-full bg-(--success)" />
            Live Monitoring
          </span>
          <span className="pill text-(--text-muted)">Risk Engine v2</span>
          <ThemeToggle />
        </div>
      </div>
    </header>
  )
}

