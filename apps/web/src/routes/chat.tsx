import { createFileRoute } from '@tanstack/react-router'
import type { Mode } from '../lib/api'
import { ChatView } from '../features/chat/ChatView'

const MODES: readonly Mode[] = ['plain', 'rag', 'agent']

export const Route = createFileRoute('/chat')({
  // mode lives in the URL so it's shareable: /chat?mode=agent
  validateSearch: (search: Record<string, unknown>): { mode?: Mode } =>
    MODES.includes(search.mode as Mode) ? { mode: search.mode as Mode } : {},
  component: ChatPage,
})

function ChatPage() {
  const { mode = 'rag' } = Route.useSearch()
  const navigate = Route.useNavigate()
  return <ChatView mode={mode} onModeChange={(m) => navigate({ search: { mode: m }, replace: true })} />
}
