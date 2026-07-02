import { useState, useEffect, useCallback } from 'react'
import { Table, Button, Upload, Space, Popconfirm, message } from 'antd'
import { UploadOutlined, DeleteOutlined, ReloadOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { listDocuments, uploadDocument, deleteDocument } from '../api/knowledge'
import type { KnowledgeDocument } from '../types'

const statusText: Record<string, string> = {
  pending: '等待中',
  processing: '处理中',
  completed: '已完成',
  failed: '失败',
}

export default function KnowledgeManage() {
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)

  const fetchDocuments = useCallback(async (p = 1) => {
    setLoading(true)
    try {
      const data = await listDocuments(p, 20)
      setDocuments(data.items)
      setTotal(data.total)
      setPage(data.page)
    } catch { /* handled by interceptor */ } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchDocuments() }, [fetchDocuments])

  const handleUpload = async (file: File) => {
    setUploading(true)
    try {
      await uploadDocument(file)
      message.success('上传成功')
      fetchDocuments(1)
    } catch (err: any) {
      message.error(err.message || '上传失败')
    } finally {
      setUploading(false)
    }
    return false
  }

  const handleDelete = async (id: number) => {
    try {
      await deleteDocument(id)
      message.success('已删除')
      fetchDocuments(page)
    } catch (err: any) {
      message.error(err.message)
    }
  }

  const columns: ColumnsType<KnowledgeDocument> = [
    {
      title: '文件名',
      dataIndex: 'original_name',
      ellipsis: true,
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      render: (s: string) => statusText[s] || s,
    },
    {
      title: '操作',
      width: 80,
      render: (_, record) => (
        <Popconfirm title="确定删除？" onConfirm={() => handleDelete(record.id)}>
          <Button type="link" danger size="small">删除</Button>
        </Popconfirm>
      ),
    },
  ]

  return (
    <div style={{ padding: 24 }}>
      <div style={{ marginBottom: 16 }}>
        <Space>
          <Upload
            accept=".pdf,.txt,.md,.csv,.docx,.html"
            showUploadList={false}
            beforeUpload={(file) => { handleUpload(file); return false }}
          >
            <Button type="primary" icon={<UploadOutlined />} loading={uploading}>上传文档</Button>
          </Upload>
          <Button icon={<ReloadOutlined />} onClick={() => fetchDocuments(page)}>刷新</Button>
        </Space>
      </div>

      <Table
        columns={columns}
        dataSource={documents}
        rowKey="id"
        loading={loading}
        size="small"
        pagination={{
          current: page,
          total,
          pageSize: 20,
          showSizeChanger: false,
          onChange: (p) => fetchDocuments(p),
        }}
      />
    </div>
  )
}
