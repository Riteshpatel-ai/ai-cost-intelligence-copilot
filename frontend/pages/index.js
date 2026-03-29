import useCopilotStore from '../store/copilotStore'
import KpiTile from '../components/insights/KpiTile'
import ImpactChip from '../components/insights/ImpactChip'
import InsightCard from '../components/insights/InsightCard'
import ApprovalCard from '../components/approvals/ApprovalCard'
import ChatWindow from '../components/copilot/ChatWindow'
import GraphCanvas from '../components/graph/GraphCanvas'
import DataIntakePanel from '../components/ingest/DataIntakePanel'

function formatInr(value) {
  return Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(value || 0)
}

export default function Home() {
  const kpis = useCopilotStore((s) => s.kpis)
  const insights = useCopilotStore((s) => s.insights)
  const actions = useCopilotStore((s) => s.actions)
  const graph = useCopilotStore((s) => s.graph)
  const timeline = useCopilotStore((s) => s.timeline)

  return (
    <div className="space-y-6 pb-8">
      <section className="card p-6 sm:p-7 rise relative overflow-hidden">
        <div className="absolute -top-20 -right-16 h-52 w-52 rounded-full bg-[color-mix(in_srgb,var(--brand)_18%,transparent)] blur-2xl" />
        <div className="grid grid-cols-1 xl:grid-cols-[1.8fr_1fr] gap-5 items-end">
          <div>
            <p className="label">AI CFO Workspace</p>
            <h2 className="mt-2 text-3xl sm:text-5xl font-extrabold tracking-tight">From Data to Decision to Savings</h2>
            <p className="mt-4 max-w-4xl text-(--text-muted) text-base sm:text-lg leading-relaxed">
              Conversational intelligence for spend leakage, SLA risk, resource inefficiency, and finance variance with explainability, graph context, and governed actions.
            </p>
          </div>
          <div className="rounded-2xl border border-(--border) bg-(--surface) p-4">
            <div className="label">Impact Signal</div>
            <div className="mt-3">
              <ImpactChip amount={kpis.impact} />
            </div>
            <p className="text-xs mt-3 text-(--text-muted)">Live metric from current anomaly and recovery model.</p>
          </div>
        </div>
      </section>

      <section className="grid grid-cols-1 md:grid-cols-2 2xl:grid-cols-4 gap-4">
        <KpiTile label="Recoverable Impact" value={formatInr(kpis.impact)} hint="Projected monthly savings opportunity" />
        <KpiTile label="Risk Level" value={kpis.riskLevel} hint="Aggregate anomaly severity score" />
        <KpiTile label="Approval Route" value={kpis.approvalRoute} hint="Current governance workflow path" />
        <KpiTile label="Detected Anomalies" value={String(kpis.anomalies)} hint="Cross-domain anomaly count from agent mesh" />
      </section>

      <section className="space-y-2">
        <div className="label">Start Here</div>
        <DataIntakePanel />
      </section>

      <section className="grid grid-cols-1 2xl:grid-cols-[1.65fr_1fr] gap-4">
        <ChatWindow />
        <article className="card p-4 rise flex flex-col min-h-[420px]">
          <div className="label mb-2">Recommendations</div>
          <p className="text-xs text-(--text-muted) mb-3">Ranked advisory output from agent mesh and policy context.</p>
          <div className="space-y-2 overflow-auto pr-1">
            {(insights.length ? insights : ['Run a query in chat to generate recommendations.']).map((item, idx) => (
              <InsightCard key={idx} text={item} />
            ))}
          </div>
        </article>
      </section>

      <section className="grid grid-cols-1 2xl:grid-cols-[1.45fr_1fr] gap-4">
        <article className="card p-4 rise min-h-[430px]">
          <div className="label mb-2">Graph Risk Analyzer</div>
          <GraphCanvas graph={graph} />
        </article>

        <article className="card p-4 rise min-h-[430px] flex flex-col">
          <div className="label mb-2">Action and Approval Desk</div>
          <p className="text-xs text-(--text-muted) mb-3">Execution-ready playbooks with governance route.</p>
          <div className="space-y-2 overflow-auto pr-1">
            {actions.length ? (
              actions.map((item, idx) => (
                <ApprovalCard
                  key={idx}
                  label={item.label || item.type || 'Action'}
                  riskLevel={item.riskLevel || item.risk_level}
                  approvalRequired={item.approvalRequired || item.approval_required}
                />
              ))
            ) : (
              <p className="rounded-xl border border-(--border) bg-(--surface-soft) px-3 py-3 text-sm text-(--text-muted)">
                No action recommendations yet. Upload or fetch data and run analysis to generate approval-ready actions.
              </p>
            )}
          </div>
        </article>
      </section>

      <section className="card p-4 rise">
        <div className="label mb-2">Explainability Timeline</div>
        <ol className="space-y-2">
          {timeline.map((item, idx) => (
            <li key={`${item.stage}-${idx}`} className="rounded-xl border border-(--border) px-3 py-2 bg-(--surface-soft) flex gap-3 items-start">
              <span className="mt-1 h-2.5 w-2.5 rounded-full bg-(--brand) shrink-0" />
              <div>
                <p className="text-sm font-semibold">{item.stage}</p>
                <p className="text-xs mt-1 text-(--text-muted)">{item.detail}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>
    </div>
  )
}

