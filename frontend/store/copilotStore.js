import { create } from 'zustand'

const defaultTimeline = [
  { stage: 'Ingestion', detail: 'ERP, SLA, and telemetry snapshots synchronized.' },
  { stage: 'RAG Retrieval', detail: 'Policy and invoice context assembled from enterprise corpus.' },
  { stage: 'Parallel Agents', detail: 'Spend, SLA, Resource, and Finance agents executed in parallel.' },
  { stage: 'Decision', detail: 'Risk and impact scored using confidence and recovery probability.' },
]

const useCopilotStore = create((set) => ({
  chat: [
    {
      role: 'assistant',
      text: 'Command center is live. Ask me where we are losing money, what to fix first, or how much can be recovered this quarter.'
    },
  ],
  kpis: {
    impact: 0,
    riskLevel: 'Low',
    approvalRoute: 'Auto',
    anomalies: 0,
  },
  insights: [],
  graph: { nodes: [], edges: [] },
  actions: [],
  criticalAlerts: [],
  latestUpload: {
    filename: '',
    rowCount: 0,
    rows: [],
  },
  timeline: defaultTimeline,
  setResult: (payload) =>
    set({
      kpis: {
        impact: payload.financial_impact || 0,
        riskLevel: (payload.risk_level || 'low').replace(/^./, (m) => m.toUpperCase()),
        approvalRoute: (payload.approval_required || 'auto').replace(/^./, (m) => m.toUpperCase()),
        anomalies: Object.values(payload.anomalies || {}).reduce(
          (sum, arr) => sum + (Array.isArray(arr) ? arr.length : 0),
          0,
        ),
      },
      insights: payload.recommendations || [],
      graph: payload.graph || { nodes: [], edges: [] },
      actions: payload.actions || [],
      criticalAlerts: [
        ...(Array.isArray(payload?.anomalies?.duplicates) && payload.anomalies.duplicates.length > 0
          ? [
              {
                level: 'high',
                text: `Duplicate payment clusters: ${payload.anomalies.duplicates.length}`,
              },
            ]
          : []),
        ...(Array.isArray(payload?.anomalies?.sla_breaches) && payload.anomalies.sla_breaches.length > 0
          ? [
              {
                level: 'medium',
                text: `SLA breach risks this cycle: ${payload.anomalies.sla_breaches.length}`,
              },
            ]
          : []),
        ...(payload?.risk_level === 'high'
          ? [
              {
                level: 'high',
                text: 'High risk impact detected - finance approval required.',
              },
            ]
          : []),
      ],
      timeline: payload.explainability?.action_audit_timeline?.length
        ? payload.explainability.action_audit_timeline.map((x) => ({
            stage: x.stage || 'Stage',
            detail: x.decision || x.explanation || 'Recorded in audit timeline.',
          }))
        : defaultTimeline,
    }),
  appendChat: (item) => set((state) => ({ chat: [...state.chat, item] })),
  setLatestUpload: (payload) =>
    set({
      latestUpload: {
        filename: payload?.filename || '',
        rowCount: payload?.rowCount || 0,
        rows: Array.isArray(payload?.rows) ? payload.rows : [],
      },
    }),
}))

export default useCopilotStore
