import apiClient from './client'
import type { Session, Message } from '../types'

export async function listSessions(): Promise<Session[]> {
  const res = await apiClient.get('/chat/sessions')
  return res.data.data
}

export async function createSession(title?: string): Promise<Session> {
  const res = await apiClient.post('/chat/sessions', { title: title || '新对话' })
  return res.data.data
}

export async function deleteSession(id: number): Promise<void> {
  await apiClient.delete(`/chat/sessions/${id}`)
}

export async function getMessages(sessionId: number): Promise<{
  session: Session
  messages: Message[]
}> {
  const res = await apiClient.get(`/chat/sessions/${sessionId}/messages`)
  return res.data.data
}

/**
 * 发送消息 - 返回 SSE EventSource 用于流式读取
 */
export function sendMessageSSE(
  sessionId: number,
  content: string,
  onToken: (token: string) => void,
  onSources: (sources: { doc_name: string; content: string; score: number }[]) => void,
  onDone: () => void,
  onError: (error: string) => void,
): AbortController {
  const token = localStorage.getItem('token')
  const controller = new AbortController()

  fetch(`/api/chat/sessions/${sessionId}/send`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ content }),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        const err = await response.json()
        onError(err.detail || '请求失败')
        return
      }

      const reader = response.body?.getReader()
      if (!reader) {
        onError('无法读取响应流')
        return
      }

      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              if (data.type === 'token') {
                onToken(data.content)
              } else if (data.type === 'sources') {
                onSources(data.sources)
              } else if (data.type === 'done') {
                onDone()
              } else if (data.type === 'error') {
                onError(data.message)
              }
            } catch {
              // 忽略 JSON 解析错误
            }
          }
        }
      }
    })
    .catch((err) => {
      if (err.name !== 'AbortError') {
        onError(err.message || '网络错误')
      }
    })

  return controller
}
