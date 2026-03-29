import { useMemo, useState } from 'react'
import useCopilotStore from '../../store/copilotStore'
import { postChat } from '../../lib/apiClient'
import { formatAssistantResponse } from '../../lib/chatFormatter'
import MessageBubble from './MessageBubble'

const prompts = [
  'Show top duplicate payments with impact math',
  'Which SLA breaches can trigger penalties this week?',
  'What actions should we approve first for max savings?',
]

export default function ChatWindow() {
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const chat = useCopilotStore((s) => s.chat)
  const latestUpload = useCopilotStore((s) => s.latestUpload)
  const appendChat = useCopilotStore((s) => s.appendChat)
  const setResult = useCopilotStore((s) => s.setResult)
  const latestReport = useMemo(() => {
    for (let i = chat.length - 1; i >= 0; i -= 1) {
      if (chat[i]?.report?.download_url) {
        return chat[i].report
      }
    }
    return null
  }, [chat])

  const send = async (message) => {
    const text = (message || input).trim()
    if (!text || loading) return
    appendChat({ role: 'user', text })
    setInput('')
    setLoading(true)

    try {
      const data = await postChat(text, {
        uploaded_rows: latestUpload?.rows || [],
        uploaded_filename: latestUpload?.filename || '',
      })
      setResult(data)
      appendChat({
        role: 'assistant',
        text: formatAssistantResponse(data.response || 'Analysis complete. Review insights and actions.', latestUpload?.filename),
        report: data.report || null,
      })
    } catch {
      appendChat({ role: 'assistant', text: 'Unable to reach backend. Please check API service.' })
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="card p-4 rise min-h-[420px] flex flex-col">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div>
          <div className="label">Copilot Workspace</div>
          <p className="text-xs text-(--text-muted) mt-1">Ask, investigate, and convert anomalies into governed action.</p>
        </div>
      </div>

      <div className="flex flex-wrap gap-2 mb-3">
        {prompts.map((prompt) => (
          <button
            key={prompt}
            type="button"
            onClick={() => send(prompt)}
            className="rounded-full border border-(--border) bg-(--surface-soft) px-3 py-1.5 text-xs font-semibold hover:border-(--brand) hover:text-(--brand) transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-(--brand)"
            aria-label={`Run suggested prompt: ${prompt}`}
          >
            {prompt}
          </button>
        ))}
      </div>

      <div className="mb-3 rounded-xl border border-(--border) bg-(--surface-soft) px-3 py-2.5 flex items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold text-(--text)">Report Center</p>
          <p className="text-[11px] text-(--text-muted)">Latest audit artifact generated from your most recent analysis.</p>
        </div>
        {latestReport?.download_url ? (
          <a
            href={latestReport.download_url}
            className="inline-flex items-center rounded-lg border border-(--border) bg-(--surface) px-3 py-1.5 text-xs font-semibold text-(--text) hover:border-(--brand) hover:text-(--brand)"
          >
            Download Latest Report (PDF)
          </a>
        ) : (
          <span className="text-[11px] text-(--text-muted)">No report generated yet</span>
        )}
      </div>

      <div className="h-[320px] overflow-y-auto rounded-xl border border-(--border) bg-(--surface) p-3 flex-1" role="log" aria-live="polite" aria-busy={loading}>
        {chat.map((m, i) => (
          <MessageBubble key={`${m.role}-${i}`} role={m.role} text={m.text} />
        ))}
        {loading && <MessageBubble role="assistant" text="Running parallel agent analysis..." />}
      </div>

      <form
        className="mt-3 flex gap-2"
        onSubmit={(e) => {
          e.preventDefault()
          send()
        }}
      >
        <label htmlFor="copilot-query-input" className="sr-only">Copilot query</label>
        <input
          id="copilot-query-input"
          className="flex-1 rounded-xl border border-(--border) bg-(--surface) px-4 py-3 text-sm outline-none focus:border-(--brand) focus-visible:ring-2 focus-visible:ring-(--brand)"
          placeholder="Ask about spend leakage, SLA risk, resource waste, or finance variance..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded-xl px-4 py-3 text-sm font-semibold bg-(--brand) text-white hover:bg-(--brand-strong) disabled:opacity-70 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-(--brand)"
          aria-label="Send copilot query"
        >
          Send
        </button>
      </form>
    </section>
  )
}

