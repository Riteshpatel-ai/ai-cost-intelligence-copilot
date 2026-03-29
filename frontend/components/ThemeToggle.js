import useUiStore from '../store/uiStore'

export default function ThemeToggle() {
  const theme = useUiStore((s) => s.theme)
  const setTheme = useUiStore((s) => s.setTheme)

  const options = [
    { id: 'operations-light', label: 'Light' },
    { id: 'executive-dark', label: 'Dark' },
  ]

  return (
    <div className="flex items-center gap-1 p-1 rounded-xl border border-(--border) bg-(--surface-soft)">
      {options.map((option) => {
        const active = theme === option.id
        return (
          <button
            key={option.id}
            aria-label={`Switch to ${option.label} theme`}
            className={`inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              active
                ? 'bg-(--surface) border border-(--border) text-(--text)'
                : 'opacity-75 hover:opacity-100 text-(--text-muted)'
            }`}
            onClick={() => setTheme(option.id)}
          >
            <span>{option.label}</span>
          </button>
        )
      })}
    </div>
  )
}
