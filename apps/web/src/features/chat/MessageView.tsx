import { Fragment, type ReactNode } from 'react'
import type { ChatMessage } from './useChat'

/** Turn "[1]" markers into superscript chips that link to the source list. */
function withCitationChips(text: string, msgId: number): ReactNode[] {
  return text.split(/(\[\d+\])/g).map((part, i) => {
    const m = /^\[(\d+)\]$/.exec(part)
    if (!m) return <Fragment key={i}>{part}</Fragment>
    return (
      <a
        key={i}
        href={`#cite-${msgId}-${m[1]}`}
        className="mx-0.5 rounded bg-indigo-100 px-1 align-super text-[10px] font-semibold text-indigo-700 no-underline dark:bg-indigo-900 dark:text-indigo-200"
      >
        {m[1]}
      </a>
    )
  })
}

export function MessageView({ msg }: { msg: ChatMessage }) {
  if (msg.role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] whitespace-pre-wrap rounded-2xl rounded-br-sm bg-indigo-600 px-4 py-2 text-white">
          {msg.content}
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-[90%] space-y-2">
      {msg.trace.length > 0 && (
        <details className="rounded-lg border border-zinc-200 text-xs dark:border-zinc-800" open={msg.pending}>
          <summary className="cursor-pointer px-3 py-1.5 text-zinc-500">
            Agent trace · {msg.trace.filter((t) => t.kind === 'call').length} tool calls
          </summary>
          <ol className="space-y-1 px-3 pb-2 font-mono">
            {msg.trace.map((t, i) =>
              t.kind === 'call' ? (
                <li key={i} className="text-amber-700 dark:text-amber-400">
                  → {t.name}({JSON.stringify(t.arguments)})
                </li>
              ) : (
                <li key={i} className="line-clamp-3 whitespace-pre-wrap pl-4 text-zinc-500">
                  ← {t.result}
                </li>
              ),
            )}
          </ol>
        </details>
      )}

      <div className="whitespace-pre-wrap rounded-2xl rounded-bl-sm bg-zinc-100 px-4 py-2 dark:bg-zinc-800">
        {msg.content ? withCitationChips(msg.content, msg.id) : msg.pending ? <span className="animate-pulse">▍</span> : null}
        {msg.error && <p className="text-red-600">⚠ {msg.error}</p>}
      </div>

      {msg.warnings.map((w, i) => (
        <p key={i} className="text-xs text-amber-600">
          ⚠ {w}
        </p>
      ))}

      {msg.citations.length > 0 && (
        <ol className="space-y-1 text-xs">
          {msg.citations.map((c) => (
            <li
              key={c.n}
              id={`cite-${msg.id}-${c.n}`}
              className="rounded-md border border-zinc-200 px-2 py-1 target:ring-2 target:ring-indigo-400 dark:border-zinc-800"
            >
              <span className="font-semibold">[{c.n}]</span> {c.filename} · chunk {c.chunk_index} ·{' '}
              <span className="text-zinc-500">score {c.score.toFixed(2)}</span>
              <p className="line-clamp-2 text-zinc-500">{c.snippet}</p>
            </li>
          ))}
        </ol>
      )}
      <p className="text-[10px] uppercase tracking-wide text-zinc-400">{msg.mode}</p>
    </div>
  )
}
