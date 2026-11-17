import { queryOptions, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../../lib/api'

export const documentsQuery = queryOptions({
  queryKey: ['documents'],
  queryFn: api.listDocuments,
})

export const healthQuery = queryOptions({
  queryKey: ['health'],
  queryFn: api.health,
  staleTime: 60_000,
  retry: false,
})

export function useUploadDocument() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: api.uploadDocument,
    onSuccess: () => qc.invalidateQueries({ queryKey: documentsQuery.queryKey }),
  })
}

export function useDeleteDocument() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: api.deleteDocument,
    onSuccess: () => qc.invalidateQueries({ queryKey: documentsQuery.queryKey }),
  })
}
