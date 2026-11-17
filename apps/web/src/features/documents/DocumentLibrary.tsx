import { useQuery } from '@tanstack/react-query'
import { useRef, useState } from 'react'
import { documentsQuery, useDeleteDocument, useUploadDocument } from './queries'

const ACCEPT = '.pdf,.md,.markdown,.txt'

export function DocumentLibrary() {
  const docs = useQuery(documentsQuery)
  const upload = useUploadDocument()
  const remove = useDeleteDocument()
  const input = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)

  const uploadFiles = async (files: FileList | null) => {
    for (const f of Array.from(files ?? [])) await upload.mutateAsync(f).catch(() => {})
  }

  return (
    <div className="space-y-6">
      <div
        onDragOver={(e) => {
          e.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragging(false)
          void uploadFiles(e.dataTransfer.files)
        }}
        onClick={() => input.current?.click()}
        className={`cursor-pointer rounded-xl border-2 border-dashed p-10 text-center transition ${
          dragging ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-950' : 'border-zinc-300 dark:border-zinc-700'
        }`}
      >
        <p className="font-medium">{upload.isPending ? 'Embedding…' : 'Drop files here or click to upload'}</p>
        <p className="mt-1 text-sm text-zinc-500">PDF, Markdown or text · chunked and embedded locally</p>
        <input
          ref={input}
          type="file"
          accept={ACCEPT}
          multiple
          hidden
          onChange={(e) => {
            void uploadFiles(e.target.files)
            e.target.value = ''
          }}
        />
      </div>
      {upload.error && <p className="text-sm text-red-600">Upload failed: {upload.error.message}</p>}

      {docs.isPending ? (
        <p className="text-zinc-500">Loading…</p>
      ) : docs.error ? (
        <p className="text-red-600">Could not load documents: {docs.error.message}</p>
      ) : docs.data.length === 0 ? (
        <p className="text-zinc-500">No documents yet.</p>
      ) : (
        <ul className="divide-y divide-zinc-200 rounded-xl border border-zinc-200 dark:divide-zinc-800 dark:border-zinc-800">
          {docs.data.map((d) => (
            <li key={d.id} className="flex items-center justify-between gap-4 px-4 py-3">
              <div className="min-w-0">
                <p className="truncate font-medium">{d.filename}</p>
                <p className="text-xs text-zinc-500">
                  {d.chunk_count} chunks · {new Date(d.created_at).toLocaleString()}
                </p>
              </div>
              <button
                onClick={() => remove.mutate(d.id)}
                disabled={remove.isPending}
                className="rounded-md px-2 py-1 text-sm text-red-600 hover:bg-red-50 disabled:opacity-50 dark:hover:bg-red-950"
              >
                Delete
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
