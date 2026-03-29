import { getBackendBaseUrl, readProxyResponse } from '../../lib/backendProxy'

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    res.status(405).json({ error: 'Method not allowed' })
    return
  }

  try {
    const response = await fetch(`${getBackendBaseUrl()}/api/action`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req.body || {}),
    })

    const data = await readProxyResponse(response)
    res.status(response.status).json(data)
  } catch {
    res.status(502).json({ error: 'Backend unavailable' })
  }
}
