import type { components } from './api-types'

export type Document = components['schemas']['DocumentOut']
export type ChatRequest = components['schemas']['ChatIn']
export type Health = components['schemas']['HealthOut']
export type Mode = NonNullable<ChatRequest['mode']>

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, init)
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, detail)
  }
  return (res.status === 204 ? undefined : await res.json()) as T
}

export const api = {
  health: () => request<Health>('/health'),
  listDocuments: () => request<Document[]>('/documents'),
  uploadDocument: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return request<Document>('/documents', { method: 'POST', body: form })
  },
  deleteDocument: (id: string) => request<void>(`/documents/${id}`, { method: 'DELETE' }),
}
