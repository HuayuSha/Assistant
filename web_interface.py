from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import json
import os
import logging
from datetime import datetime
from tools import mcp_tools
from config import MCP_NAME, MCP_VERSION, CHAT_LOG_PATH
import daily_tools as dt

# 配置日志记录
def setup_logging():
    """设置日志记录"""
    # 创建logs目录
    os.makedirs("logs", exist_ok=True)
    
    # 1. 程序内部API调用日志
    app_logger = logging.getLogger('app_api')
    app_logger.setLevel(logging.INFO)
    
    app_file_handler = logging.FileHandler('logs/app_api.log', encoding='utf-8')
    app_file_handler.setLevel(logging.INFO)
    app_file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    
    app_logger.addHandler(app_file_handler)
    
    # 2. 外部LLM API调用日志
    llm_logger = logging.getLogger('llm_api')
    llm_logger.setLevel(logging.INFO)
    
    llm_file_handler = logging.FileHandler('logs/llm_api.log', encoding='utf-8')
    llm_file_handler.setLevel(logging.INFO)
    llm_file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    
    llm_logger.addHandler(llm_file_handler)
    
    return app_logger, llm_logger

# 初始化日志记录器
app_logger, llm_logger = setup_logging()

app = FastAPI(
    title=f"{MCP_NAME} - Web界面",
    version=MCP_VERSION,
    description="用户友好的MCP工具使用界面"
)

# 聊天记录：确保目录存在
os.makedirs(os.path.dirname(CHAT_LOG_PATH), exist_ok=True)

def append_chat_log(role: str, content: str):
    """将单条消息追加写入 JSONL 聊天日志。"""
    try:
        record = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "role": role,
            "content": content,
        }
        with open(CHAT_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as e:
        app_logger.error(f"写入聊天记录失败: {e}")

# 添加中间件记录所有HTTP请求和响应
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录所有HTTP请求和响应的中间件"""
    start_time = datetime.now()
    
    # 记录请求信息
    app_logger.info(f"=== HTTP请求 ===")
    app_logger.info(f"请求时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    app_logger.info(f"请求方法: {request.method}")
    app_logger.info(f"请求路径: {request.url.path}")
    app_logger.info(f"请求查询参数: {dict(request.query_params)}")
    app_logger.info(f"请求头: {dict(request.headers)}")
    
    # 如果是POST请求，尝试记录请求体
    if request.method == "POST":
        try:
            body = await request.body()
            if body:
                app_logger.info(f"请求体: {body.decode('utf-8')}")
        except Exception as e:
            app_logger.info(f"请求体读取失败: {e}")
    
    # 处理请求
    response = await call_next(request)
    
    # 记录响应信息
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    app_logger.info(f"=== HTTP响应 ===")
    app_logger.info(f"响应时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    app_logger.info(f"响应状态: {response.status_code}")
    app_logger.info(f"响应头: {dict(response.headers)}")
    app_logger.info(f"请求耗时: {duration:.3f}秒")
    app_logger.info(f"---")
    
    return response

# 创建templates目录
os.makedirs("templates", exist_ok=True)
os.makedirs("static", exist_ok=True)

# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/logs", StaticFiles(directory="logs"), name="logs")

# 创建Jinja2模板
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """主页"""
    return templates.TemplateResponse("index.html", {"request": request, "MCP_NAME": MCP_NAME, "MCP_VERSION": MCP_VERSION})

@app.post("/api/execute_tool")
async def execute_tool(
    tool_name: str = Form(...),
    city: str = Form(None),
    expression: str = Form(None),
    text: str = Form(None),
    target_lang: str = Form(None),
    file_path: str = Form(None),
    dir_path: str = Form(None)
):
    """执行工具API"""
    try:
        if tool_name == "get_current_time":
            result = mcp_tools.get_current_time()
        elif tool_name == "get_weather":
            city = city or "北京"
            result = mcp_tools.get_weather(city)
        elif tool_name == "calculate":
            if not expression:
                return {"success": False, "error": "请输入数学表达式"}
            result = mcp_tools.calculate(expression)
        elif tool_name == "translate_text":
            if not text:
                return {"success": False, "error": "请输入要翻译的文本"}
            target_lang = target_lang or "en"
            result = mcp_tools.translate_text(text, target_lang)
        elif tool_name == "get_file_info":
            if not file_path:
                return {"success": False, "error": "请输入文件路径"}
            result = mcp_tools.get_file_info(file_path)
        elif tool_name == "list_directory":
            dir_path = dir_path or "."
            result = mcp_tools.list_directory(dir_path)
        else:
            result = {"error": f"未知工具: {tool_name}"}
        
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

# 新增：DailyPlan相关API
@app.get("/api/daily/today")
async def api_daily_today():
    return dt.get_today_path()

@app.post("/api/daily/create")
async def api_daily_create(force: bool = Form(False)):
    return dt.create_today_from_template(force=force)

@app.get("/api/daily/read")
async def api_daily_read(path: str = None):
    return dt.read_structured(path)

# 读取历史聊天记录（最近N条）
@app.get("/api/chat/history")
async def api_chat_history(limit: int = 50, before: int = None):
    """分页读取聊天记录：
    - limit: 返回条数（默认50）
    - before: 读取在该索引之前的记录（基于0..N-1全量顺序索引）。若未提供，则读取最新limit条。
    返回：history（按时间顺序升序）、next_before（可用于继续向上翻）、total
    """
    try:
        if not os.path.exists(CHAT_LOG_PATH):
            return JSONResponse({"success": True, "history": [], "next_before": None, "total": 0})
        items = []
        with open(CHAT_LOG_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    role = obj.get("role")
                    if role in ("user", "assistant"):
                        items.append(obj)
                except Exception:
                    continue
        total = len(items)
        if total == 0:
            return JSONResponse({"success": True, "history": [], "next_before": None, "total": 0})
        # 计算窗口
        if before is None:
            end_idx = total
        else:
            end_idx = max(0, min(before, total))
        start_idx = max(0, end_idx - max(1, limit))
        slice_items = items[start_idx:end_idx]
        next_before = start_idx if start_idx > 0 else None
        return JSONResponse({"success": True, "history": slice_items, "next_before": next_before, "total": total})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

@app.post("/api/daily/set_status")
async def api_daily_set_status(task_text: str = Form(...), status: str = Form(...)):
    return dt.set_task_status(task_text, status)

@app.post("/api/daily/add_task")
async def api_daily_add_task(section_title: str = Form(...), task_text: str = Form(...), status: str = Form('todo')):
    return dt.add_task(section_title, task_text, status)

@app.post("/api/daily/append_note")
async def api_daily_append_note(section_title: str = Form(...), note_line: str = Form(...)):
    return dt.append_note(section_title, note_line)

@app.post("/api/daily/rollover")
async def api_daily_rollover():
    return dt.rollover_incomplete()

# 新增：聊天接口

@app.post("/api/chat")
async def api_chat(message: str = Form(...)):
    """普通聊天接口"""
    prompt = message
    
    # 记录请求
    app_logger.info(f"=== 聊天请求 ===")
    app_logger.info(f"请求时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    app_logger.info(f"请求方法: POST")
    app_logger.info(f"请求路径: /api/chat")
    app_logger.info(f"请求参数: message={message}")
    # 不再拼接系统提示，系统提示由后端工具注入
    
    try:
        # 持久化：记录用户消息
        append_chat_log("user", message)
        res = mcp_tools.call_openai_api(prompt, max_tokens=300)
        
        # 记录响应
        app_logger.info(f"=== 聊天响应 ===")
        app_logger.info(f"响应时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        app_logger.info(f"响应状态: 200 OK")
        app_logger.info(f"原始API响应: {json.dumps(res, ensure_ascii=False, indent=2)}")
        app_logger.info(f"响应内容: {res.get('response', '无内容')}")
        app_logger.info(f"---")
        # 持久化：记录助手回复
        if isinstance(res, dict) and res.get("success"):
            append_chat_log("assistant", res.get("response", ""))
        
        return res
    except Exception as e:
        error_msg = f"聊天接口错误: {str(e)}"
        app_logger.error(f"=== 聊天错误 ===")
        app_logger.error(f"错误时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        app_logger.error(f"错误信息: {error_msg}")
        app_logger.error(f"---")
        return {"success": False, "error": error_msg}

@app.post("/api/chat/stream")
async def api_chat_stream(message: str = Form(...)):
    """流式聊天接口"""
    prompt = message
    
    # 记录请求
    app_logger.info(f"=== 流式聊天请求 ===")
    app_logger.info(f"请求时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    app_logger.info(f"请求方法: POST")
    app_logger.info(f"请求路径: /api/chat/stream")
    app_logger.info(f"请求参数: message={message}")
    # 不再拼接系统提示，系统提示由后端工具注入
    
    def event_gen():
        try:
            full_response = ""
            raw_chunks = []
            
            # 记录原始流式数据
            for chunk in mcp_tools.stream_openai_api(prompt, max_tokens=600):
                raw_chunks.append(chunk)
                full_response += chunk
                yield f"data: {json.dumps({'delta': chunk}, ensure_ascii=False)}\n\n"
            
            # 记录完整响应
            app_logger.info(f"=== 流式聊天响应 ===")
            app_logger.info(f"响应时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            app_logger.info(f"响应状态: 200 OK (Stream)")
            app_logger.info(f"原始流式数据块: {raw_chunks}")
            app_logger.info(f"完整回复: {full_response}")
            app_logger.info(f"---")
            # 持久化：记录用户与助手消息
            append_chat_log("user", message)
            append_chat_log("assistant", full_response)
            
        except Exception as e:
            error_msg = f"流式聊天错误: {str(e)}"
            app_logger.error(f"=== 流式聊天错误 ===")
            app_logger.error(f"错误时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            app_logger.error(f"错误信息: {error_msg}")
            app_logger.error(f"---")
            yield f"data: {json.dumps({'error': error_msg}, ensure_ascii=False)}\n\n"
        
        yield "data: [DONE]\n\n"
    
    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
        "Content-Type": "text/event-stream; charset=utf-8",
    }
    return StreamingResponse(event_gen(), media_type="text/event-stream", headers=headers)

if __name__ == "__main__":
    import uvicorn
    print(f"启动{MCP_NAME} Web界面...")
    print("服务器将在 http://0.0.0.0:8080 启动")
    print("本地访问: http://localhost:8080")
    print("网络访问: http://100.86.196.9:8080")
    print("程序API日志: logs/app_api.log")
    print("外部LLM API日志: logs/llm_api.log")
    uvicorn.run(app, host="0.0.0.0", port=8080)
