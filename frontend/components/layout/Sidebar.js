import useCopilotStore from '../../store/copilotStore'

const agents = ['Spend Agent', 'SLA Agent', 'Resource Agent', 'Finance Agent']

export default function Sidebar() {
  const criticalAlerts = useCopilotStore((s) => s.criticalAlerts)

  const alertClass = (level) => {
    if (level === 'high') {
      return 'bg-[color-mix(in_srgb,var(--danger)_14%,transparent)] border border-[color-mix(in_srgb,var(--danger)_45%,white)]'
    }
    if (level === 'medium') {
      return 'bg-[color-mix(in_srgb,var(--warning)_14%,transparent)] border border-[color-mix(in_srgb,var(--warning)_45%,white)]'
    }
    return 'bg-(--surface-soft) border border-(--border)'
  }

  return (
    <aside className="card p-4 rise xl:sticky xl:top-24 h-fit space-y-5">
      <section className="rounded-2xl border border-(--border) bg-(--surface) p-3">
        <div className="label mb-2">Critical Alerts</div>
        <div className="space-y-2 text-sm">
          {criticalAlerts.length > 0 ? (
            criticalAlerts.map((alert, idx) => (
              <div key={`${alert.level}-${idx}`} className={`rounded-xl px-3 py-2 font-medium ${alertClass(alert.level)}`}>
                {alert.text}
              </div>
            ))
          ) : (
            <div className="rounded-xl px-3 py-2 bg-(--surface-soft) border border-(--border) text-(--text-muted)">
              No active critical alerts. Upload/fetch data and run analysis.
            </div>
          )}
        </div>
      </section>

      <section className="rounded-2xl border border-(--border) bg-(--surface) p-3">
        <div className="label mb-2">Agent Mesh</div>
        <div className="space-y-2">
          {agents.map((agent) => (
            <div
              key={agent}
              className="flex items-center justify-between rounded-xl px-3 py-2 border border-(--border) bg-(--surface-soft)"
            >
              <span className="text-sm font-medium">{agent}</span>
              <span className="text-xs font-bold text-(--success)">Healthy</span>
            </div>
          ))}
        </div>
      </section>

      <section className="rounded-2xl border border-(--border) bg-(--surface) p-3 text-sm text-(--text-muted) leading-relaxed">
        <div className="label mb-2">Approval Workflow</div>
        <div className="space-y-1.5">
          <div>Low risk: auto execute</div>
          <div>Medium risk: manager approval</div>
          <div>High risk: finance approval</div>
        </div>
      </section>

      <section className="rounded-2xl border border-(--border) bg-(--surface-soft) p-3">
        <div className="label mb-2">Data to Savings</div>
        <p className="text-sm leading-relaxed text-(--text-muted)">
          Data intake to anomaly detection to impact math to approval route to corrective action.
        </p>
      </section>
    </aside>
  )
}

