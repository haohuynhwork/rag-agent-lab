import { useEffect, useRef, useState } from 'react'
import type { Mode } from '../../lib/api'
import { MessageView } from './MessageView'
import { useChat } from './useChat'

const MODES: { value: Mode; label: string; hint: string }[] = [
  { value: 'plain', label: 'Plain LLM', hint: 'No documents — model knowledge only' },
  { value: 'rag', label: 'RAG', hint: 'Retrieve top-k chunks, answer with citations' },
  { value: 'agent', label: 'Agent', hint: 'Model decides when to search, list docs or calculate' },
]

export function ChatView({ mode, onModeChange }: { mode: Mode; onModeChange: (m: Mode) => void }) {
  const { messages, send, stop, clear, busy } = useChat()
  const [input, setInput] = useState('')
  const bottom = useRef<HTMLDivElement>(null)

  useEffect(() => {
    // block body: scrollIntoView returns a Promise in newer browsers, and an
    // effect must return nothing or a cleanup function
    bottom.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const submit = () => {
    const q = input.trim()
    if (!q || busy) return
    setInput('')
    void send(q, mode)
  }

  return (
    <div className="flex h-[calc(100dvh-4rem)] flex-col">
      <div className="flex flex-wrap items-center gap-2 border-b border-zinc-200 py-3 dark:border-zinc-800">
        <div role="radiogroup" className="inline-flex rounded-lg bg-zinc-100 p-1 dark:bg-zinc-800">
          {MODES.map((m) => (
            <button
              key={m.value}
              role="radio"
              aria-checked={mode === m.value}
              title={m.hint}
              onClick={() => onModeChange(m.value)}
              className={`rounded-md px-3 py-1 text-sm ${
                mode === m.value ? 'bg-white shadow dark:bg-zinc-950' : 'text-zinc-500'
              }`}
            >
              {m.label}
            </button>
          ))}
        </div>
        <span className="text-xs text-zinc-500">{MODES.find((m) => m.value === mode)?.hint}</span>
        {messages.length > 0 && (
          <button onClick={clear} disabled={busy} className="ml-auto text-sm text-zinc-500 hover:underline">
            Clear
          </button>
        )}
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto py-4">
        {messages.length === 0 && (
          <p className="mt-16 text-center text-zinc-500">
            Upload documents, then ask a question. Switch modes to compare plain, RAG and agent answers.
          </p>
        )}
        {messages.map((m) => (
          <MessageView key={m.id} msg={m} />
        ))}
        <div ref={bottom} />
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault()
          submit()
        }}
        className="flex gap-2 border-t border-zinc-200 py-3 dark:border-zinc-800"
      >
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              submit()
            }
          }}
          rows={1}
          placeholder="Ask about your documents…"
          className="flex-1 resize-none rounded-lg border border-zinc-300 bg-transparent px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:border-zinc-700"
        />
        {busy ? (
          <button type="button" onClick={stop} className="rounded-lg bg-zinc-200 px-4 dark:bg-zinc-700">
            Stop
          </button>
        ) : (
          <button type="submit" disabled={!input.trim()} className="rounded-lg bg-indigo-600 px-4 text-white disabled:opacity-50">
            Send
          </button>
        )}
      </form>
    </div>
  )
}
