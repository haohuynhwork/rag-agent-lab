import type { QueryClient } from '@tanstack/react-query'
import { useQuery } from '@tanstack/react-query'
import { type ErrorComponentProps, Link, Outlet, createRootRouteWithContext } from '@tanstack/react-router'
import { healthQuery } from '../features/documents/queries'

export const Route = createRootRouteWithContext<{ queryClient: QueryClient }>()({
  component: RootLayout,
  errorComponent: RootError,
})

function RootError({ error, reset }: ErrorComponentProps) {
  return (
    <div className="mx-auto max-w-xl px-4 py-16 text-center">
      <h1 className="text-lg font-semibold">Something went wrong</h1>
      <pre className="mt-3 whitespace-pre-wrap text-left text-sm text-red-600">{error instanceof Error ? error.message : String(error)}</pre>
      <button onClick={reset} className="mt-4 rounded-lg bg-indigo-600 px-4 py-2 text-white">
        Try again
      </button>
    </div>
  )
}

function RootLayout() {
  const health = useQuery(healthQuery)
  const linkCls = 'rounded-md px-3 py-1.5 text-sm text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100'
  const activeCls = 'bg-zinc-100 !text-zinc-900 dark:bg-zinc-800 dark:!text-zinc-100'

  return (
    <div className="mx-auto max-w-4xl px-4">
      <header className="flex h-16 items-center gap-2 border-b border-zinc-200 dark:border-zinc-800">
        <span className="mr-4 font-semibold">ai-demo</span>
        <Link to="/chat" className={linkCls} activeProps={{ className: activeCls }}>
          Chat
        </Link>
        <Link to="/documents" className={linkCls} activeProps={{ className: activeCls }}>
          Documents
        </Link>
        <span className="ml-auto text-xs text-zinc-500">
          {health.data ? (
            <>
              <span className="mr-1 inline-block size-2 rounded-full bg-emerald-500" />
              {health.data.chat_model} · {health.data.embed_model}
            </>
          ) : health.isError ? (
            <>
              <span className="mr-1 inline-block size-2 rounded-full bg-red-500" />
              API offline
            </>
          ) : null}
        </span>
      </header>
      <Outlet />
    </div>
  )
}
