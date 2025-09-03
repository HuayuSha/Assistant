# 本地MCP服务器

这是一个本地运行的MCP（Model Context Protocol）服务器，使用OpenAI的tools格式，提供多种实用工具。

## 功能特性

- 🚀 完全兼容OpenAI API格式
- 🛠️ 内置多种实用工具
- 🔧 支持工具调用（Function Calling）
- 📡 本地部署，无需外部依赖
- 🎯 简单易用的REST API接口
- 🌐 美观的Web用户界面
- 📱 响应式设计，支持移动设备
- 🎨 现代化UI设计，用户体验优秀

## 可用工具

| 工具名称 | 描述 | 参数 |
|---------|------|------|
| `get_current_time` | 获取当前时间信息 | 无 |
| `get_weather` | 获取指定城市天气 | `city` (可选，默认北京) |
| `calculate` | 计算数学表达式 | `expression` (必需) |
| `translate_text` | 翻译文本 | `text` (必需), `target_lang` (可选) |
| `get_file_info` | 获取文件信息 | `file_path` (必需) |
| `list_directory` | 列出目录内容 | `dir_path` (可选，默认当前目录) |

## 安装和运行

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置API

编辑 `config.py` 文件，设置你的API配置：

```python
BASE_URL = "https://chatgtp.vin/v1"
API_KEY = "你的API密钥"
MODEL = "auto"
```

### 3. 启动方式

#### 方式一：Web界面（推荐）
```bash
python web_interface.py
```
或者双击 `start_web.bat`

Web界面将在 `http://localhost:8080` 启动，提供美观的用户界面。

#### 方式二：API服务器
```bash
python mcp_server.py
```
或者双击 `start_server.bat`

API服务器将在 `http://localhost:8000` 启动。

### 4. 测试服务器

```bash
python test_client.py
```
或者双击 `test_server.bat`

## API接口

### 基础接口

- `GET /` - 获取服务器信息
- `GET /tools` - 获取可用工具列表
- `GET /health` - 健康检查

### OpenAI兼容接口

- `POST /v1/chat/completions` - 聊天完成接口，支持工具调用

## 使用示例

### 1. Web界面使用（推荐）

1. 启动Web界面：`python web_interface.py`
2. 在浏览器中访问：`http://localhost:8080`
3. 直接点击工具卡片使用各种功能

### 2. API接口使用

#### 获取服务器信息
```bash
curl http://localhost:8000/
```

#### 查看可用工具
```bash
curl http://localhost:8000/tools
```

#### 调用工具
```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [{"role": "user", "content": "请告诉我现在的时间"}],
    "tools": [{
      "type": "function",
      "function": {
        "name": "get_current_time",
        "description": "获取当前时间信息",
        "parameters": {
          "type": "object",
          "properties": {},
          "required": []
        }
      }
    }]
  }'
```

## 项目结构

```
├── config.py              # 配置文件
├── tools.py               # 工具实现
├── mcp_server.py          # API服务器
├── web_interface.py       # Web界面服务器
├── templates/
│   └── index.html        # Web界面模板
├── test_client.py         # 测试客户端
├── requirements.txt       # Python依赖
├── start_server.bat       # 启动API服务器
├── start_web.bat          # 启动Web界面
├── test_server.bat        # 测试服务器
└── README.md             # 项目说明
```

## 扩展工具

要添加新工具，请：

1. 在 `tools.py` 中添加新的方法
2. 在 `mcp_server.py` 的 `AVAILABLE_TOOLS` 中添加工具定义
3. 在 `execute_tool` 函数中添加工具调用逻辑

## 注意事项

- 确保API密钥的安全性
- 生产环境中建议使用环境变量存储敏感信息
- 工具调用支持异步执行，提高性能
- 所有工具返回JSON格式数据

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request！
