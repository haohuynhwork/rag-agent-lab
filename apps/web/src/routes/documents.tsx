import { createFileRoute } from '@tanstack/react-router'
import { DocumentLibrary } from '../features/documents/DocumentLibrary'
import { documentsQuery } from '../features/documents/queries'

export const Route = createFileRoute('/documents')({
  loader: ({ context }) => context.queryClient.prefetchQuery(documentsQuery),
  component: () => (
    <div className="py-6">
      <h1 className="mb-4 text-xl font-semibold">Document library</h1>
      <DocumentLibrary />
    </div>
  ),
})
