# PhotoStory 前端

PhotoStory 项目的 React + Vite 前端界面。

## 项目结构

```
frontend/
├── index.html              # HTML 入口文件
├── package.json            # 项目配置和依赖
├── vite.config.js          # Vite 配置文件
├── src/
│   ├── main.jsx            # React 应用入口
│   ├── App.jsx             # 主组件
│   ├── App.css             # 全局样式
│   ├── index.css           # 组件样式
│   ├── api.js              # API 封装
│   ├── components/
│   │   ├── Header.jsx      # 顶部导航栏
│   │   └── ProgressBar.jsx # 进度条组件
│   └── pages/
│       ├── LoginPage.jsx   # 登录页面
│       ├── UploadPage.jsx  # 上传页面
│       ├── ProcessingPage.jsx  # 处理进度页面
│       ├── ResultsPage.jsx # 结果展示页面
│       ├── StoryPage.jsx   # 故事展示页面
│       └── ExportPage.jsx  # 导出页面
```

## 安装依赖

```bash
npm install
```

## 启动开发服务器

```bash
npm run dev
```

访问 `http://localhost:5173` 查看应用。

## 构建生产版本

```bash
npm run build
```

构建产物将输出到 `dist/` 目录。

## 与后端对接

前端默认连接后端 API 地址：
- HTTP API: `http://localhost:8000/api/v1`
- WebSocket: `ws://localhost:8000`

支持的 API 端点：
- `POST /api/v1/upload/initiate` - 初始化上传
- `POST /api/v1/upload/chunk` - 上传分片
- `POST /api/v1/upload/complete` - 完成上传
- `GET /api/v1/upload/status/{id}` - 查询上传状态
- `GET /api/v1/tasks/{id}` - 查询任务状态
- `GET /api/v1/tasks/{id}/results` - 获取处理结果
- `POST /api/v1/tasks/{id}/story` - 触发故事生成
- `WS /ws/task/{task_id}` - WebSocket 进度推送
- `POST /api/v1/auth/register` - 用户注册
- `POST /api/v1/auth/login` - 用户登录
- `GET /health` - 健康检查

## 功能特性

1. **用户认证** - 支持注册和登录
2. **照片上传** - 拖拽上传，支持批量选择
3. **处理进度** - 实时显示处理进度和阶段
4. **结果展示** - 精选照片网格展示
5. **故事生成** - LLM 生成照片故事
6. **导出功能** - PDF 和视频导出

## 部署

构建生产版本后，将 `dist/` 目录部署到 Web 服务器即可。

```bash
npm run build
# 将 dist/ 目录复制到 Web 服务器
```
