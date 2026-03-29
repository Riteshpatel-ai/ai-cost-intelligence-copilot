import { getBackendBaseUrls, readProxyResponse } from '../../lib/backendProxy'

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    res.status(405).json({ error: 'Method not allowed' })
    return
  }

  try {
    const candidates = getBackendBaseUrls()
    let lastStatus = 502
    let lastData = { error: 'Backend unavailable' }

    for (const base of candidates) {
      try {
        const response = await fetch(`${base}/api/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(req.body || {}),
        })

        const data = await readProxyResponse(response)
        if (!response.ok) {
          lastStatus = response.status
          lastData = data
          continue
        }

        // Prefer richer response payloads that include report metadata.
        if (data && data.report) {
          res.status(response.status).json(data)
          return
        }

        lastStatus = response.status
        lastData = data
      } catch {
        // Try next backend candidate when current one is unreachable.
        lastStatus = 502
        lastData = { error: `Backend unavailable at ${base}` }
        continue
      }
    }

    res.status(lastStatus).json(lastData)
  } catch {
    res.status(502).json({ error: 'Backend unavailable' })
  }
}
