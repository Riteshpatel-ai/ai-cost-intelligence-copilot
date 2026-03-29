import { getBackendBaseUrl, readProxyResponse } from '../../../lib/backendProxy'

export const config = {
  api: {
    bodyParser: false,
  },
}

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    res.status(405).json({ error: 'Method not allowed' })
    return
  }

  try {
    const headers = {}
    if (req.headers['content-type']) {
      headers['content-type'] = req.headers['content-type']
    }
    if (req.headers['content-length']) {
      headers['content-length'] = req.headers['content-length']
    }

    const response = await fetch(`${getBackendBaseUrl()}/api/ingest/upload`, {
      method: 'POST',
      headers,
      body: req,
      duplex: 'half',
    })

    const data = await readProxyResponse(response)
    res.status(response.status).json(data)
  } catch {
    res.status(502).json({ error: 'Backend unavailable' })
  }
}
