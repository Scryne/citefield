import { useQuery } from '@tanstack/react-query'
import { api } from './api'

export function useDocuments() {
  return useQuery({
    queryKey: ['documents'],
    queryFn: api.documents,
    // poll only while something is still being read
    refetchInterval: (q) => (q.state.data?.some((d) => d.status === 'queued' || d.status === 'processing') ? 1500 : false),
  })
}
