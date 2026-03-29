export default function ApprovalCard({ label, riskLevel, approvalRequired }) {
  const risk = (riskLevel || 'low').toLowerCase()
  const riskClass =
    risk === 'high'
      ? 'bg-[color-mix(in_srgb,var(--danger)_18%,transparent)] text-[color-mix(in_srgb,var(--danger)_80%,black)]'
      : risk === 'medium'
        ? 'bg-[color-mix(in_srgb,var(--warning)_22%,transparent)] text-[color-mix(in_srgb,var(--warning)_88%,black)]'
        : 'bg-[color-mix(in_srgb,var(--success)_20%,transparent)] text-[color-mix(in_srgb,var(--success)_80%,black)]'

  return (
    <div className="rounded-xl border border-(--border) p-3 bg-(--surface)">
      <div className="flex items-start justify-between gap-2">
        <div className="text-sm font-semibold">{label || 'Action proposal'}</div>
        <span className={`text-[11px] px-2 py-1 rounded-full font-semibold ${riskClass}`}>{risk.toUpperCase()}</span>
      </div>
      <div className="mt-1 text-xs text-(--text-muted)">
        Approval: {(approvalRequired || 'auto').toUpperCase()}
      </div>
      <div className="mt-3 flex gap-2">
        <button
          type="button"
          aria-label={`Request approval for ${label || 'action proposal'}`}
          className="rounded-lg px-3 py-1.5 text-xs font-semibold bg-(--brand) text-white hover:bg-(--brand-strong) transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-(--brand)"
        >
          Request Approval
        </button>
        <button
          type="button"
          aria-label={`Simulate ${label || 'action proposal'}`}
          className="rounded-lg px-3 py-1.5 text-xs font-semibold border border-(--border) bg-(--surface-soft) hover:bg-(--surface) focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-(--brand)"
        >
          Simulate
        </button>
      </div>
    </div>
  )
}

