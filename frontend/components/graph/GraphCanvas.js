import ReactFlow, { Background, Controls } from 'reactflow'
import 'reactflow/dist/style.css'

export default function GraphCanvas({ graph }) {
  const nodes = graph?.nodes || []
  const edges = graph?.edges || []
  const hasGraphData = nodes.length > 0 || edges.length > 0

  return (
    <div className="rounded-xl border border-(--border) overflow-hidden bg-(--surface)" aria-live="polite">
      <div className="px-3 py-2 border-b border-(--border) bg-(--surface-soft) flex items-center justify-between gap-3">
        <p className="text-xs text-(--text-muted)">Entity relationship map for current anomalies</p>
        <div className="text-xs font-semibold text-(--text-muted)">{nodes.length} nodes | {edges.length} edges</div>
      </div>
      {hasGraphData ? (
        <div className="h-[300px]">
          <ReactFlow fitView nodes={nodes} edges={edges}>
            <Controls />
            <Background gap={22} size={1} />
          </ReactFlow>
        </div>
      ) : (
        <div className="h-[300px] grid place-items-center px-6 text-center">
          <div>
            <p className="text-sm font-semibold">No graph data yet</p>
            <p className="text-xs text-(--text-muted) mt-2">
              Upload a dataset, then ask Copilot for duplicate payments or SLA risks to generate entity links.
            </p>
          </div>
        </div>
      )}
    </div>
  )
}

