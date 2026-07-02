# 企业制度知识库问答系统

基于 LangChain RAG 框架的企业级知识库问答系统，支持文档上传、向量检索和智能问答。

## 技术栈

| 层次 | 技术 |
|------|------|
| LLM | 阿里云百炼平台（qwen-plus） |
| 向量化 | DashScope Embeddings（text-embedding-v2） |
| 后端 | Python FastAPI |
| 向量库 | ChromaDB |
| 数据库 | SQLite（开发）/ PostgreSQL（生产） |
| 前端 | React 18 + TypeScript + Vite + Ant Design 5 |
| 认证 | JWT |

## 功能

- 用户注册、登录、修改密码
- 多轮对话问答（流式输出）
- 答案来源引用（标注引用文档）
- 知识库文档上传、管理（仅管理员）
- 多会话管理，历史记录持久化

## 快速开始

### 1. 环境要求

- Python 3.10+
- Node.js 18+
- 阿里云百炼 API Key

### 2. 后端启动

```bash
cd backend
pip install -r requirements.txt

# 配置 .env 文件
echo DASHSCOPE_API_KEY=你的API密钥 > .env

# 重建知识库（从 D:\Desktop\知识库 目录导入文档）
python rebuild_kb.py

# 启动服务（默认端口 8001）
python run.py
```

### 3. 前端启动

```bash
cd frontend
npm install
npm run dev
```

### 4. 访问

- 前端页面：http://localhost:5173
- 后端 API 文档：http://localhost:8001/docs
- 管理员账号：admin / 123456

## 知识库文档

知识库文档存放在 `D:\Desktop\知识库` 目录下，系统启动时通过 `rebuild_kb.py` 脚本导入。

| 文档 | 内容 |
|------|------|
| 员工手册.txt | 入职、离职、工作时间、行为准则 |
| 考勤与假期.txt | 打卡、请假、加班、年假福利 |
| 报销与薪酬.txt | 报销范围标准流程、薪资福利 |
| IT使用规范.txt | 网络、设备、安全、远程办公 |

## 项目结构

```
KnowledgeBase/
├── backend/
│   ├── app/
│   │   ├── api/          # API 路由
│   │   ├── models/       # 数据库模型
│   │   ├── schemas/      # 请求响应模型
│   │   ├── services/     # 业务逻辑
│   │   ├── rag/          # RAG 流水线（检索、生成）
│   │   └── utils/        # 工具函数
│   ├── run.py            # 启动入口
│   └── rebuild_kb.py     # 知识库重建脚本
├── frontend/
│   └── src/
│       ├── api/          # API 请求封装
│       ├── pages/        # 页面组件
│       ├── components/   # 通用组件
│       └── stores/       # 状态管理
└── README.md
```
