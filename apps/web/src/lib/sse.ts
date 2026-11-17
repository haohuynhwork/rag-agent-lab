import type { ChatRequest } from './api'

/** Mirrors ai_demo.application.dto.AnswerEvent / Citation. */
export type Citation = {
  n: number
  document_id: string
  filename: string
  chunk_index: number
  snippet: string
  score: number
}

export type AnswerEvent =
  | { type: 'token'; data: string }
  | { type: 'citations'; data: Citation[] }
  | { type: 'tool_call'; data: { name: string; arguments: Record<string, unknown> } }
  | { type: 'tool_result'; data: { name: string; result: string } }
  | { type: 'warning'; data: string }
  | { type: 'error'; data: string }
  | { type: 'done'; data: null }

/** POST + read a text/event-stream body (EventSource only supports GET). */
export async function* streamChat(body: ChatRequest, signal?: AbortSignal): AsyncGenerator<AnswerEvent> {
  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  })
  if (!res.ok || !res.body) {
    yield { type: 'error', data: `HTTP ${res.status}: ${await res.text()}` }
    return
  }
  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader()
  let buffer = ''
  for (;;) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += value
    let sep: number
    while ((sep = buffer.indexOf('\n\n')) !== -1) {
      const frame = buffer.slice(0, sep)
      buffer = buffer.slice(sep + 2)
      for (const line of frame.split('\n')) {
        if (line.startsWith('data: ')) yield JSON.parse(line.slice(6)) as AnswerEvent
      }
    }
  }
}
