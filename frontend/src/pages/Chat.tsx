import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Input, Button, List, Typography, Empty, Popconfirm, message, Spin, Tag } from 'antd'
import {
  SendOutlined,
  PlusOutlined,
  DeleteOutlined,
  MessageOutlined,
  FileTextOutlined,
  StopOutlined,
} from '@ant-design/icons'
import { listSessions, createSession, deleteSession, getMessages, sendMessageSSE } from '../api/chat'
import type { Session, Message } from '../types'
import ReactMarkdown from 'react-markdown'

const { Text, Title } = Typography

export default function Chat() {
  const { sessionId } = useParams()
  const navigate = useNavigate()

  const [sessions, setSessions] = useState<Session[]>([])
  const [messages, setMessages] = useState<Message[]>([])
  const [currentSessionId, setCurrentSessionId] = useState<number | null>(
    sessionId ? parseInt(sessionId) : null
  )
  const [inputValue, setInputValue] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [streamingContent, setStreamingContent] = useState('')
  const [streamingSources, setStreamingSources] = useState<Message['sources']>(null)
  const [loadingSessions, setLoadingSessions] = useState(true)
  const [loadingMessages, setLoadingMessages] = useState(false)
  const abortRef = useRef<AbortController | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<any>(null)

  // 加载会话列表
  const fetchSessions = useCallback(async () => {
    try {
      const data = await listSessions()
      setSessions(data)
    } catch {
      // 已由拦截器处理
    } finally {
      setLoadingSessions(false)
    }
  }, [])

  useEffect(() => {
    fetchSessions()
  }, [fetchSessions])

  // 加载消息
  useEffect(() => {
    if (!currentSessionId) return
    setLoadingMessages(true)
    getMessages(currentSessionId)
      .then(({ messages: msgs }) => setMessages(msgs))
      .catch(() => {})
      .finally(() => setLoadingMessages(false))
  }, [currentSessionId])

  // 同步 URL 参数
  useEffect(() => {
    if (sessionId) {
      setCurrentSessionId(parseInt(sessionId))
    }
  }, [sessionId])

  // 滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingContent])

  // 创建新会话
  const handleNewSession = async () => {
    try {
      const session = await createSession()
      setSessions((prev) => [session, ...prev])
      setCurrentSessionId(session.id)
      setMessages([])
      navigate(`/chat/${session.id}`)
    } catch (err: any) {
      message.error(err.message)
    }
  }

  // 切换会话
  const handleSwitchSession = (id: number) => {
    setCurrentSessionId(id)
    navigate(`/chat/${id}`)
    setStreamingContent('')
    setStreamingSources(null)
  }

  // 删除会话
  const handleDeleteSession = async (id: number) => {
    try {
      await deleteSession(id)
      setSessions((prev) => prev.filter((s) => s.id !== id))
      if (currentSessionId === id) {
        const remaining = sessions.filter((s) => s.id !== id)
        if (remaining.length > 0) {
          handleSwitchSession(remaining[0].id)
        } else {
          setCurrentSessionId(null)
          setMessages([])
          navigate('/chat')
        }
      }
    } catch (err: any) {
      message.error(err.message)
    }
  }

  // 发送消息
  const handleSend = async () => {
    const content = inputValue.trim()
    if (!content || streaming) return

    let sid = currentSessionId
    if (!sid) {
      // 自动创建会话
      try {
        const session = await createSession()
        setSessions((prev) => [session, ...prev])
        sid = session.id
        setCurrentSessionId(sid)
        navigate(`/chat/${sid}`)
      } catch (err: any) {
        message.error(err.message)
        return
      }
    }

    setInputValue('')
    setStreaming(true)
    setStreamingContent('')
    setStreamingSources(null)

    // 添加用户消息到列表
    const userMsg: Message = {
      id: Date.now(),
      session_id: sid,
      role: 'user',
      content,
      sources: null,
      created_at: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, userMsg])

    abortRef.current = sendMessageSSE(
      sid,
      content,
      (token) => {
        setStreamingContent((prev) => prev + token)
      },
      (sources) => {
        setStreamingSources(sources)
      },
      () => {
        // 流式完成 - 添加助手消息
        setStreaming(false)
        setStreamingContent('')
        setStreamingSources(null)
        // 重新加载消息以获取服务器端保存的完整消息
        if (sid) {
          getMessages(sid)
            .then(({ messages: msgs }) => setMessages(msgs))
            .catch(() => {})
        }
        // 刷新会话列表更新标题
        fetchSessions()
      },
      (error) => {
        setStreaming(false)
        message.error(error)
      },
    )
  }

  // 停止生成
  const handleStop = () => {
    abortRef.current?.abort()
    setStreaming(false)
    // 保存当前流式内容
    if (streamingContent && currentSessionId) {
      getMessages(currentSessionId)
        .then(({ messages: msgs }) => setMessages(msgs))
        .catch(() => {})
    }
  }

  // 键盘事件
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div style={{ display: 'flex', height: 'calc(100vh - 64px)' }}>
      {/* 左侧会话列表 */}
      <div
        style={{
          width: 280,
          borderRight: '1px solid #f0f0f0',
          background: '#fff',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <div style={{ padding: '12px 16px', borderBottom: '1px solid #f0f0f0' }}>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            block
            onClick={handleNewSession}
          >
            新对话
          </Button>
        </div>

        <div style={{ flex: 1, overflow: 'auto' }}>
          {loadingSessions ? (
            <div style={{ textAlign: 'center', padding: 40 }}>
              <Spin />
            </div>
          ) : sessions.length === 0 ? (
            <Empty description="暂无对话" style={{ marginTop: 40 }} image={Empty.PRESENTED_IMAGE_SIMPLE} />
          ) : (
            <List
              dataSource={sessions}
              renderItem={(item) => (
                <div
                  key={item.id}
                  onClick={() => handleSwitchSession(item.id)}
                  style={{
                    padding: '10px 16px',
                    cursor: 'pointer',
                    background: currentSessionId === item.id ? '#e6f4ff' : 'transparent',
                    borderLeft: currentSessionId === item.id ? '3px solid #1677ff' : '3px solid transparent',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                  }}
                  onMouseEnter={(e) => {
                    (e.currentTarget as HTMLElement).style.background =
                      currentSessionId === item.id ? '#e6f4ff' : '#fafafa'
                  }}
                  onMouseLeave={(e) => {
                    (e.currentTarget as HTMLElement).style.background =
                      currentSessionId === item.id ? '#e6f4ff' : 'transparent'
                  }}
                >
                  <div style={{ flex: 1, overflow: 'hidden' }}>
                    <Text
                      ellipsis
                      style={{
                        fontSize: 14,
                        color: currentSessionId === item.id ? '#1677ff' : '#333',
                      }}
                    >
                      <MessageOutlined style={{ marginRight: 6 }} />
                      {item.title}
                    </Text>
                  </div>
                  <Popconfirm
                    title="确定删除此对话?"
                    onConfirm={(e) => {
                      e?.stopPropagation()
                      handleDeleteSession(item.id)
                    }}
                    onCancel={(e) => e?.stopPropagation()}
                  >
                    <Button
                      type="text"
                      size="small"
                      icon={<DeleteOutlined />}
                      onClick={(e) => e.stopPropagation()}
                      style={{ opacity: 0.5 }}
                    />
                  </Popconfirm>
                </div>
              )}
            />
          )}
        </div>
      </div>

      {/* 右侧对话区 */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', background: '#fff' }}>
        {!currentSessionId ? (
          <div
            style={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'center',
              alignItems: 'center',
              gap: 16,
            }}
          >
            <Title level={2} style={{ color: '#1677ff', marginBottom: 0 }}>
              企业制度知识库问答
            </Title>
            <Text type="secondary" style={{ fontSize: 16 }}>
              基于 LangChain + 阿里云百炼，智能回答公司制度相关问题
            </Text>
            <Button type="primary" size="large" onClick={handleNewSession} style={{ marginTop: 16 }}>
              开始新对话
            </Button>
          </div>
        ) : (
          <>
            {/* 消息列表 */}
            <div
              style={{
                flex: 1,
                overflow: 'auto',
                padding: '16px 24px',
              }}
            >
              {loadingMessages ? (
                <div style={{ textAlign: 'center', padding: 60 }}>
                  <Spin tip="加载消息中..." />
                </div>
              ) : (
                <>
                  {messages.map((msg) => (
                    <div
                      key={msg.id}
                      style={{
                        marginBottom: 20,
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: msg.role === 'user' ? 'flex-end' : 'flex-start',
                      }}
                    >
                      {/* 消息气泡 */}
                      <div
                        style={{
                          maxWidth: '75%',
                          padding: '12px 18px',
                          borderRadius: 12,
                          background: msg.role === 'user' ? '#1677ff' : '#f5f5f5',
                          color: msg.role === 'user' ? '#fff' : '#333',
                        }}
                      >
                        {msg.role === 'user' ? (
                          <Text style={{ color: '#fff', whiteSpace: 'pre-wrap' }}>{msg.content}</Text>
                        ) : (
                          <div className="markdown-body">
                            <ReactMarkdown>{msg.content}</ReactMarkdown>
                          </div>
                        )}
                      </div>

                      {/* 来源引用 */}
                      {msg.sources && msg.sources.length > 0 && (
                        <div style={{ maxWidth: '75%', marginTop: 6 }}>
                          {msg.sources.map((src, i) => (
                            <Text key={i} type="secondary" style={{ fontSize: 12 }}>
                              [{src.doc_name}]
                            </Text>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}

                  {/* 流式生成中的临时显示 */}
                  {streaming && (
                    <div style={{ marginBottom: 20 }}>
                      <div
                        style={{
                          maxWidth: '75%',
                          padding: '12px 18px',
                          borderRadius: 12,
                          background: '#f5f5f5',
                        }}
                      >
                        <div className="markdown-body">
                          <ReactMarkdown>{streamingContent || '思考中...'}</ReactMarkdown>
                        </div>
                      </div>
                      {streamingSources && streamingSources.length > 0 && (
                        <div style={{ maxWidth: '75%', marginTop: 6 }}>
                          {streamingSources.map((src, i) => (
                            <Text key={i} type="secondary" style={{ fontSize: 12 }}>
                              [{src.doc_name}]
                            </Text>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  <div ref={messagesEndRef} />
                </>
              )}
            </div>

            {/* 输入框 */}
            <div
              style={{
                padding: '12px 24px 20px',
                borderTop: '1px solid #f0f0f0',
                display: 'flex',
                gap: 12,
                alignItems: 'flex-end',
              }}
            >
              <Input.TextArea
                ref={inputRef}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="输入您的问题，Shift+Enter 换行，Enter 发送"
                autoSize={{ minRows: 1, maxRows: 5 }}
                disabled={streaming}
                style={{ flex: 1, borderRadius: 8 }}
              />
              {streaming ? (
                <Button
                  danger
                  icon={<StopOutlined />}
                  onClick={handleStop}
                  style={{ borderRadius: 8 }}
                >
                  停止
                </Button>
              ) : (
                <Button
                  type="primary"
                  icon={<SendOutlined />}
                  onClick={handleSend}
                  disabled={!inputValue.trim()}
                  style={{ borderRadius: 8 }}
                >
                  发送
                </Button>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
