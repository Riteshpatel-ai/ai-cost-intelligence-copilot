import { getBackendBaseUrls } from '../../../lib/backendProxy'

export default async function handler(req, res) {
  if (req.method !== 'GET') {
    res.status(405).json({ error: 'Method not allowed' })
    return
  }

  try {
    const candidates = getBackendBaseUrls()
    let lastStatus = 502
    let lastError = 'Unable to download report PDF'

    for (const base of candidates) {
      try {
        const response = await fetch(`${base}/api/reports/latest-pdf`, {
          method: 'GET',
        })

        if (!response.ok) {
          lastStatus = response.status
          lastError = (await response.text()) || lastError
          continue
        }

        const arrayBuffer = await response.arrayBuffer()
        const contentDisposition = response.headers.get('content-disposition') || 'attachment; filename="cost-optimization-audit.pdf"'
        res.setHeader('Content-Type', 'application/pdf')
        res.setHeader('Content-Disposition', contentDisposition)
        res.status(200).send(Buffer.from(arrayBuffer))
        return
      } catch {
        // Try next backend candidate when current one is unreachable.
        lastStatus = 502
        lastError = `Backend unavailable at ${base}`
        continue
      }
    }

    res.status(lastStatus).json({ error: lastError })
  } catch {
    res.status(502).json({ error: 'Backend unavailable' })
  }
}
