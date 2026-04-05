import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL || '/api/v1'

const client = axios.create({
  baseURL: BASE_URL,
  timeout: 120_000,
})

// ── CV Upload ─────────────────────────────────────────────────────────────────

/**
 * Upload a PDF file and start the analysis pipeline.
 * @param {File} file
 * @returns {Promise<{ session_id: string, status: string, message: string }>}
 */
export async function uploadCV(file, professionalObjective = "No especificado") {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('professional_objective', professionalObjective)

  const { data } = await client.post('/upload-cv', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

// ── Job status polling ────────────────────────────────────────────────────────

/**
 * Check processing status for a session.
 * @param {string} sessionId
 * @returns {Promise<{ status: string, learning_path?: object, errors?: string[] }>}
 */
export async function getJobStatus(sessionId) {
  const { data } = await client.get(`/job-status/${sessionId}`)
  return data
}

// ── Learning Path ─────────────────────────────────────────────────────────────

/**
 * Fetch the completed learning path for a session.
 * @param {string} sessionId
 */
export async function getLearningPath(sessionId) {
  const { data } = await client.get(`/learning-path/${sessionId}`)
  return data
}

// ── Polling helper ────────────────────────────────────────────────────────────

/**
 * Poll the job status every `intervalMs` ms until completed or failed.
 * Calls onProgress(status) each tick, resolves with the learning_path on success.
 *
 * @param {string} sessionId
 * @param {{ onProgress?: (status: string) => void, intervalMs?: number, maxAttempts?: number, signal?: AbortSignal }} options
 * @returns {Promise<object>}
 */
export async function pollUntilDone(
  sessionId,
  { onProgress = () => {}, intervalMs = 3000, maxAttempts = 100, signal } = {}
) {
  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    // Check if aborted before each request
    if (signal?.aborted) throw new Error('Operación cancelada por el usuario.')

    const job = await getJobStatus(sessionId)
    onProgress(job.status)

    if (job.status === 'completed' || job.status === 'completado') {
      return job.learning_path
    }
    if (job.status === 'failed' || job.status === 'fallido') {
      throw new Error(job.errors?.join('\n') || 'El análisis ha fallado.')
    }

    // Wait with abortion check
    await new Promise((resolve, reject) => {
      const timer = setTimeout(resolve, intervalMs)
      if (signal) {
        signal.addEventListener('abort', () => {
          clearTimeout(timer)
          reject(new Error('Operación cancelada por el usuario.'))
        }, { once: true })
      }
    })
  }
  throw new Error('Se agotó el tiempo de espera para el análisis.')
}
