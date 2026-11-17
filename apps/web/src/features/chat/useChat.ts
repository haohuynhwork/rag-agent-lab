import { useCallback, useRef, useState } from 'react'
import type { Mode } from '../../lib/api'
import { streamChat, type Citation } from '../../lib/sse'

export type TraceStep =
  | { kind: 'call'; name: string; arguments: Record<string, unknown> }
  | { kind: 'result'; name: string; result: string }

export type ChatMessage = {
  id: number
  role: 'user' | 'assistant'
  content: string
  mode?: Mode
  citations: Citation[]
  trace: TraceStep[]
  warnings: string[]
  error?: string
  pending?: boolean
}

let nextId = 1

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const abort = useRef<AbortController | null>(null)
  const busy = messages.some((m) => m.pending)

  const send = useCallback(
    async (question: string, mode: Mode) => {
      const history = messages
        .filter((m) => !m.error && m.content)
        .map(({ role, content }) => ({ role, content }))
      const user: ChatMessage = { id: nextId++, role: 'user', content: question, citations: [], trace: [], warnings: [] }
      const assistantId = nextId++
      setMessages((ms) => [
        ...ms,
        user,
        { id: assistantId, role: 'assistant', content: '', mode, citations: [], trace: [], warnings: [], pending: true },
      ])

      const patch = (fn: (m: ChatMessage) => ChatMessage) =>
        setMessages((ms) => ms.map((m) => (m.id === assistantId ? fn(m) : m)))

      abort.current = new AbortController()
      try {
        for await (const ev of streamChat({ question, mode, history }, abort.current.signal)) {
          switch (ev.type) {
            case 'token':
              patch((m) => ({ ...m, content: m.content + ev.data }))
              break
            case 'citations':
              patch((m) => ({ ...m, citations: ev.data }))
              break
            case 'tool_call':
              patch((m) => ({ ...m, trace: [...m.trace, { kind: 'call', ...ev.data }] }))
              break
            case 'tool_result':
              patch((m) => ({ ...m, trace: [...m.trace, { kind: 'result', ...ev.data }] }))
              break
            case 'warning':
              patch((m) => ({ ...m, warnings: [...m.warnings, ev.data] }))
              break
            case 'error':
              patch((m) => ({ ...m, error: ev.data }))
              break
          }
        }
      } catch (e) {
        if ((e as Error).name !== 'AbortError') patch((m) => ({ ...m, error: String(e) }))
      } finally {
        patch((m) => ({ ...m, pending: false }))
        abort.current = null
      }
    },
    [messages],
  )

  const stop = useCallback(() => abort.current?.abort(), [])
  const clear = useCallback(() => setMessages([]), [])

  return { messages, send, stop, clear, busy }
}
