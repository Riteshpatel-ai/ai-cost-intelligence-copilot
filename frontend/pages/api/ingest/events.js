import { getBackendBaseUrl, readProxyResponse } from '../../../lib/backendProxy'

export default async function handler(req, res) {
  if (req.method !== 'GET') {
    res.status(405).json({ error: 'Method not allowed' })
    return
  }

  try {
    const query = new URLSearchParams(req.query || {}).toString()
    const response = await fetch(`${getBackendBaseUrl()}/api/ingest/events${query ? `?${query}` : ''}`)
    const data = await readProxyResponse(response)
    res.status(response.status).json(data)
  } catch {
    res.status(502).json({ error: 'Backend unavailable' })
  }
}
