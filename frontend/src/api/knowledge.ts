import apiClient from './client'
import type { DocumentListResponse, KnowledgeStats } from '../types'

export async function listDocuments(
  page = 1,
  pageSize = 20,
  statusFilter = ''
): Promise<DocumentListResponse> {
  const params: Record<string, string | number> = { page, page_size: pageSize }
  if (statusFilter) params.status_filter = statusFilter
  const res = await apiClient.get('/knowledge/documents', { params })
  return res.data.data
}

export async function uploadDocument(file: File): Promise<{ id: number; original_name: string; status: string }> {
  const formData = new FormData()
  formData.append('file', file)
  const res = await apiClient.post('/knowledge/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data.data
}

export async function deleteDocument(id: number): Promise<void> {
  await apiClient.delete(`/knowledge/documents/${id}`)
}

export async function getKnowledgeStats(): Promise<KnowledgeStats> {
  const res = await apiClient.get('/knowledge/stats')
  return res.data.data
}
