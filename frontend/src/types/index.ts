/** 用户信息 */
export interface UserInfo {
  id: number
  username: string
  role: 'admin' | 'user'
  created_at: string
}

/** 登录/注册请求 */
export interface AuthRequest {
  username: string
  password: string
}

/** 登录响应 */
export interface LoginResponse {
  access_token: string
  token_type: string
  username: string
  role: string
}

/** 修改密码请求 */
export interface ChangePasswordRequest {
  old_password: string
  new_password: string
}

/** 会话 */
export interface Session {
  id: number
  title: string
  created_at: string
  updated_at: string
  message_count: number
}

/** 消息 */
export interface Message {
  id: number
  session_id: number
  role: 'user' | 'assistant'
  content: string
  sources: SourceInfo[] | null
  created_at: string
}

/** 引用来源 */
export interface SourceInfo {
  doc_name: string
  content: string
  score: number
}

/** 知识库文档 */
export interface KnowledgeDocument {
  id: number
  filename: string
  original_name: string
  file_type: string
  file_size: number
  chunk_count: number
  char_count: number
  status: 'pending' | 'processing' | 'completed' | 'failed'
  error_message: string | null
  created_at: string
}

/** 文档列表响应 */
export interface DocumentListResponse {
  total: number
  page: number
  page_size: number
  items: KnowledgeDocument[]
}

/** 知识库统计 */
export interface KnowledgeStats {
  total_documents: number
  total_chunks: number
  total_chars: number
  completed_documents: number
  processing_documents: number
  failed_documents: number
}

/** API 统一响应 */
export interface ApiResponse<T = unknown> {
  code: number
  message: string
  data: T
}
