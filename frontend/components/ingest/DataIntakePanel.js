import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import useCopilotStore from '../../store/copilotStore'

export default function DataIntakePanel() {
  const [uploadFile, setUploadFile] = useState(null)
  const [autoFetchMinutes, setAutoFetchMinutes] = useState('5')
  const [autoFetchEnabled, setAutoFetchEnabled] = useState(false)
  const [autoFetchLastRunAt, setAutoFetchLastRunAt] = useState('')
  const [autoFetchLastResult, setAutoFetchLastResult] = useState(null)
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const autoFetchInFlightRef = useRef(false)
  const setLatestUpload = useCopilotStore((s) => s.setLatestUpload)

  const fileName = useMemo(() => (uploadFile ? uploadFile.name : 'No file selected'), [uploadFile])
  const autoFetchIntervalMinutes = useMemo(() => {
    const parsed = Number(autoFetchMinutes)
    if (!Number.isFinite(parsed) || parsed < 1) return null
    return Math.floor(parsed)
  }, [autoFetchMinutes])

  const uploadDataset = async () => {
    if (!uploadFile) {
      setError('Choose a CSV or XLSX file first.')
      return
    }

    setBusy(true)
    setError('')
    setResult(null)

    try {
      const formData = new FormData()
      formData.append('file', uploadFile)

      const res = await fetch('/api/ingest/upload', {
        method: 'POST',
        body: formData,
      })

      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || data.error || 'Unable to upload dataset')
      setResult(data)
      setLatestUpload({
        filename: data.filename || uploadFile?.name || 'uploaded_file',
        rowCount: data.row_count || 0,
        rows: data.rows_for_analysis || data.preview || [],
      })
    } catch (e) {
      setError(e.message || 'Unable to upload dataset')
    } finally {
      setBusy(false)
    }
  }

  const fetchLatestGmailNow = useCallback(async (triggerMode = 'manual') => {
    if (triggerMode === 'auto') {
      if (autoFetchInFlightRef.current) return
      autoFetchInFlightRef.current = true
    } else {
      setBusy(true)
      setResult(null)
    }

    setError('')

    try {
      const res = await fetch('/api/gmail/manual-fetch-latest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ limit: 1 }),
      })

      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || data.error || 'Unable to fetch latest Gmail email')

      if (triggerMode === 'auto') {
        setAutoFetchLastRunAt(new Date().toLocaleString())
        setAutoFetchLastResult(data)
      } else {
        setResult(data)
      }
    } catch (e) {
      setError(e.message || 'Unable to fetch latest Gmail email')
      if (triggerMode === 'auto') {
        setAutoFetchEnabled(false)
      }
    } finally {
      if (triggerMode === 'auto') {
        autoFetchInFlightRef.current = false
      } else {
        setBusy(false)
      }
    }
  }, [])

  const toggleAutoFetch = () => {
    if (autoFetchEnabled) {
      setAutoFetchEnabled(false)
      return
    }

    if (!autoFetchIntervalMinutes) {
      setError('Enter a valid auto-fetch interval in minutes (minimum 1).')
      return
    }

    setError('')
    setAutoFetchEnabled(true)
  }

  useEffect(() => {
    if (!autoFetchEnabled || !autoFetchIntervalMinutes) return undefined

    fetchLatestGmailNow('auto')
    const intervalMs = autoFetchIntervalMinutes * 60 * 1000
    const timer = setInterval(() => {
      fetchLatestGmailNow('auto')
    }, intervalMs)

    return () => clearInterval(timer)
  }, [autoFetchEnabled, autoFetchIntervalMinutes, fetchLatestGmailNow])

  return (
    <section className="card p-4 rise" aria-labelledby="data-intake-title">
      <div className="label mb-2">Data Intake (Manual Upload + Gmail Fetch)</div>
      <h3 id="data-intake-title" className="text-base font-bold">Operational Intake Desk</h3>
      <p className="text-sm text-(--text-muted) mb-4">
        Manually upload CSV/XLSX data and run Gmail-based fetch workflows.
      </p>
      <p className="text-xs text-(--text-muted) mb-4">
        After upload, ask chat: Show top duplicate payments with impact math to analyze this file.
      </p>

      <div className="grid grid-cols-1 gap-4">
        <div className="rounded-xl border border-(--border) p-3 bg-(--surface)">
          <p className="text-[11px] uppercase tracking-wide text-(--text-muted)">Path A</p>
          <p className="text-sm font-semibold mb-2">Manual File Upload</p>
          <div className="space-y-2">
            <label htmlFor="upload-file-input" className="sr-only">Upload dataset file</label>
            <input
              id="upload-file-input"
              type="file"
              accept=".csv,.xlsx"
              onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
              className="w-full rounded-lg border border-(--border) bg-(--surface-soft) px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-(--brand)"
            />
            <p className="text-xs text-(--text-muted)">{fileName}</p>
            <button
              type="button"
              onClick={uploadDataset}
              disabled={busy}
              className="rounded-lg px-3 py-2 text-sm font-semibold border border-(--border) bg-(--surface-soft) disabled:opacity-70 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-(--brand)"
            >
              Upload and Ingest
            </button>
          </div>
        </div>
      </div>

      <div className="mt-4 rounded-xl border border-(--border) p-3 bg-(--surface)">
        <p className="text-[11px] uppercase tracking-wide text-(--text-muted)">Path B</p>
        <p className="text-sm font-semibold mb-2">Gmail Quick Fetch + Automation</p>
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-3">
          <div className="space-y-2 rounded-lg border border-(--border) bg-(--surface-soft) p-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-(--text-muted)">Instant Fetch</p>
            <button
              type="button"
              onClick={() => fetchLatestGmailNow('manual')}
              disabled={busy}
              className="rounded-lg px-3 py-2 text-sm font-semibold bg-(--brand) text-white hover:bg-(--brand-strong) disabled:opacity-70 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-(--brand)"
            >
              Fetch Latest Gmail Now
            </button>
          </div>

          <div className="space-y-2 rounded-lg border border-(--border) bg-(--surface-soft) p-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-(--text-muted)">Automation Scheduler</p>
            <label htmlFor="auto-fetch-minutes" className="text-xs text-(--text-muted)">
              Fetch every (minutes)
            </label>
            <input
              id="auto-fetch-minutes"
              type="number"
              min="1"
              step="1"
              value={autoFetchMinutes}
              onChange={(e) => setAutoFetchMinutes(e.target.value)}
              className="w-full rounded-lg border border-(--border) bg-(--surface) px-3 py-2 text-sm outline-none focus:border-(--brand) focus-visible:ring-2 focus-visible:ring-(--brand)"
              placeholder="5"
            />
            <button
              type="button"
              onClick={toggleAutoFetch}
              disabled={busy}
              className="rounded-lg px-3 py-2 text-sm font-semibold border border-(--border) bg-(--surface) disabled:opacity-70 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-(--brand)"
            >
              {autoFetchEnabled ? 'Stop Automation' : 'Start Automation'}
            </button>
            <p className="text-xs text-(--text-muted)">
              Status: {autoFetchEnabled ? `Running every ${autoFetchIntervalMinutes || '?'} minute(s)` : 'Stopped'}
            </p>
            {autoFetchLastRunAt ? (
              <p className="text-xs text-(--text-muted)">Last auto run: {autoFetchLastRunAt}</p>
            ) : null}
            {autoFetchLastResult ? (
              <pre className="text-xs overflow-auto whitespace-pre-wrap max-h-45 rounded-lg border border-(--border) bg-(--surface) p-2">
                {JSON.stringify(autoFetchLastResult, null, 2)}
              </pre>
            ) : null}
          </div>
        </div>
      </div>

      {error ? <div className="mt-3 text-sm text-(--danger)" role="alert">{error}</div> : null}

      {result ? (
        <div className="mt-3 rounded-xl border border-(--border) bg-(--surface-soft) p-3" aria-live="polite">
          <p className="text-sm font-semibold mb-1">Latest Response</p>
          <pre className="text-xs overflow-auto whitespace-pre-wrap max-h-55">{JSON.stringify(result, null, 2)}</pre>
        </div>
      ) : null}
    </section>
  )
}

