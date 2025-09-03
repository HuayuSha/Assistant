from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json
import logging
from tools import mcp_tools
from daily_tools import (
    get_today_path as dt_get_today_path,
    create_today_from_template as dt_create_today,
    read_structured as dt_read_structured,
    add_task as dt_add_task,
    set_task_status as dt_set_task_status,
    append_note as dt_append_note,
    rollover_incomplete as dt_rollover_incomplete,
)
from config import MCP_HOST, MCP_PORT, MCP_NAME, MCP_VERSION

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=MCP_NAME,
    version=MCP_VERSION,
    description="本地MCP服务器，提供多种实用工具"
)

# OpenAI Tools格式的数据模型
class Tool(BaseModel):
    type: str
    function: Dict[str, Any]

class Message(BaseModel):
    role: str
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None

class ToolCall(BaseModel):
    id: str
    type: str
    function: Dict[str, Any]

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[Message]
    tools: Optional[List[Tool]] = None
    tool_choice: Optional[str] = None
    max_tokens: Optional[int] = 1000
    temperature: Optional[float] = 0.7

class ChatCompletionResponse(BaseModel):
    id: str
    object: str
    created: int
    model: str
    choices: List[Dict[str, Any]]
    usage: Dict[str, Any]

# 定义可用的工具
AVAILABLE_TOOLS = {
    "get_current_time": {
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
    },
    "get_weather": {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "获取指定城市的天气信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称",
                        "default": "北京"
                    }
                },
                "required": []
            }
        }
    },
    "calculate": {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "计算数学表达式",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "数学表达式，如：2+3*4"
                    }
                },
                "required": ["expression"]
            }
        }
    },
    "translate_text": {
        "type": "function",
        "function": {
            "name": "translate_text",
            "description": "翻译文本",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "要翻译的文本"
                    },
                    "target_lang": {
                        "type": "string",
                        "description": "目标语言",
                        "default": "en"
                    }
                },
                "required": ["text"]
            }
        }
    },
    "get_file_info": {
        "type": "function",
        "function": {
            "name": "get_file_info",
            "description": "获取文件信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "文件路径"
                    }
                },
                "required": ["file_path"]
            }
        }
    },
    "list_directory": {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "列出目录内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "dir_path": {
                        "type": "string",
                        "description": "目录路径",
                        "default": "."
                    }
                },
                "required": []
            }
        }
    },
    # === DailyPlan 工具 ===
    "dp_get_today_path": {
        "type": "function",
        "function": {
            "name": "dp_get_today_path",
            "description": "获取今日计划文件路径与存在性",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    "dp_create_today": {
        "type": "function",
        "function": {
            "name": "dp_create_today",
            "description": "从模板创建今日计划文件（已存在则默认跳过）",
            "parameters": {
                "type": "object",
                "properties": {
                    "force": {"type": "boolean", "description": "是否强制覆盖", "default": False}
                },
                "required": []
            }
        }
    },
    "dp_read_day": {
        "type": "function",
        "function": {
            "name": "dp_read_day",
            "description": "读取（默认今日）计划文件并解析结构化内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "可选，明确文件路径。不传则读取今日"}
                },
                "required": []
            }
        }
    },
    "dp_add_task": {
        "type": "function",
        "function": {
            "name": "dp_add_task",
            "description": "在指定分区追加一条任务",
            "parameters": {
                "type": "object",
                "properties": {
                    "section_title_prefix": {"type": "string", "description": "分区标题前缀，如 '🎯' 或 '今日重点任务'"},
                    "task_text": {"type": "string", "description": "任务文本"},
                    "status": {"type": "string", "description": "任务状态 todo|done|partial|cancelled|in_progress|need_help", "default": "todo"},
                    "path": {"type": "string", "description": "可选，明确文件路径"}
                },
                "required": ["section_title_prefix", "task_text"]
            }
        }
    },
    "dp_set_task_status": {
        "type": "function",
        "function": {
            "name": "dp_set_task_status",
            "description": "根据任务文本精确匹配并设置任务状态",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_text": {"type": "string", "description": "需要精确匹配的任务文本"},
                    "status": {"type": "string", "description": "todo|done|partial|cancelled|in_progress|need_help"},
                    "path": {"type": "string", "description": "可选，明确文件路径"}
                },
                "required": ["task_text", "status"]
            }
        }
    },
    "dp_append_note": {
        "type": "function",
        "function": {
            "name": "dp_append_note",
            "description": "在指定分区末尾追加一行备注（普通子弹）",
            "parameters": {
                "type": "object",
                "properties": {
                    "section_title_prefix": {"type": "string", "description": "分区标题前缀"},
                    "note_line": {"type": "string", "description": "备注内容"},
                    "path": {"type": "string", "description": "可选，明确文件路径"}
                },
                "required": ["section_title_prefix", "note_line"]
            }
        }
    },
    "dp_rollover_incomplete": {
        "type": "function",
        "function": {
            "name": "dp_rollover_incomplete",
            "description": "将未完成任务结转到明日文件（自动创建明日文件）",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "可选，源文件路径；不传默认今日"}
                },
                "required": []
            }
        }
    }
}

@app.get("/")
async def root():
    """根路径，返回服务器信息"""
    return {
        "name": MCP_NAME,
        "version": MCP_VERSION,
        "status": "运行中",
        "available_tools": list(AVAILABLE_TOOLS.keys())
    }

@app.get("/tools")
async def get_tools():
    """获取所有可用工具"""
    return {
        "tools": list(AVAILABLE_TOOLS.values())
    }

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """处理聊天完成请求，支持工具调用"""
    try:
        logger.info(f"收到聊天请求: {request.model}")
        
        # 检查是否有工具调用
        if request.tools and request.messages:
            last_message = request.messages[-1]
            
            # 检查是否需要工具调用
            if last_message.tool_calls:
                # 处理工具调用
                tool_results = []
                
                for tool_call in last_message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = tool_call.function.arguments
                    
                    if function_name in AVAILABLE_TOOLS:
                        # 执行工具调用
                        result = await execute_tool(function_name, function_args)
                        tool_results.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "content": json.dumps(result, ensure_ascii=False)
                        })
                    else:
                        tool_results.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "content": json.dumps({"error": f"未知工具: {function_name}"}, ensure_ascii=False)
                        })
                
                # 返回工具调用结果
                return {
                    "id": "chatcmpl-" + str(hash(str(request))),
                    "object": "chat.completion",
                    "created": 1234567890,
                    "model": request.model,
                    "choices": [{
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": "工具调用完成",
                            "tool_calls": last_message.tool_calls
                        },
                        "finish_reason": "tool_calls"
                    }],
                    "usage": {
                        "prompt_tokens": 100,
                        "completion_tokens": 50,
                        "total_tokens": 150
                    }
                }
        
        # 如果没有工具调用，返回普通回复
        response_content = f"你好！我是{MCP_NAME}。我可以帮助你使用以下工具：{', '.join(AVAILABLE_TOOLS.keys())}"
        
        return {
            "id": "chatcmpl-" + str(hash(str(request))),
            "object": "chat.completion",
            "created": 1234567890,
            "model": request.model,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response_content
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150
            }
        }
        
    except Exception as e:
        logger.error(f"处理聊天请求时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def execute_tool(function_name: str, arguments: str) -> Dict[str, Any]:
    """执行指定的工具"""
    try:
        # 解析参数
        if isinstance(arguments, str):
            args = json.loads(arguments)
        else:
            args = arguments
        
        logger.info(f"执行工具: {function_name}, 参数: {args}")
        
        # 根据工具名称调用相应的方法
        if function_name == "get_current_time":
            return mcp_tools.get_current_time()
        elif function_name == "get_weather":
            city = args.get("city", "北京")
            return mcp_tools.get_weather(city)
        elif function_name == "calculate":
            expression = args.get("expression", "")
            return mcp_tools.calculate(expression)
        elif function_name == "translate_text":
            text = args.get("text", "")
            target_lang = args.get("target_lang", "en")
            return mcp_tools.translate_text(text, target_lang)
        elif function_name == "get_file_info":
            file_path = args.get("file_path", "")
            return mcp_tools.get_file_info(file_path)
        elif function_name == "list_directory":
            dir_path = args.get("dir_path", ".")
            return mcp_tools.list_directory(dir_path)
        # === DailyPlan 工具分发 ===
        elif function_name == "dp_get_today_path":
            return dt_get_today_path()
        elif function_name == "dp_create_today":
            force = args.get("force", False)
            return dt_create_today(force=bool(force))
        elif function_name == "dp_read_day":
            path = args.get("path")
            return dt_read_structured(path=path)
        elif function_name == "dp_add_task":
            section_title_prefix = args.get("section_title_prefix")
            task_text = args.get("task_text")
            status = args.get("status", "todo")
            path = args.get("path")
            return dt_add_task(section_title_prefix, task_text, status=status, path=path)
        elif function_name == "dp_set_task_status":
            task_text = args.get("task_text")
            status = args.get("status")
            path = args.get("path")
            return dt_set_task_status(task_text, status, path=path)
        elif function_name == "dp_append_note":
            section_title_prefix = args.get("section_title_prefix")
            note_line = args.get("note_line")
            path = args.get("path")
            return dt_append_note(section_title_prefix, note_line, path=path)
        elif function_name == "dp_rollover_incomplete":
            path = args.get("path")
            return dt_rollover_incomplete(path=path)
        else:
            return {"error": f"未知工具: {function_name}"}
            
    except Exception as e:
        logger.error(f"执行工具 {function_name} 时出错: {str(e)}")
        return {"error": f"工具执行失败: {str(e)}"}

@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy", "timestamp": mcp_tools.get_current_time()}

if __name__ == "__main__":
    import uvicorn
    logger.info(f"启动{MCP_NAME}服务器...")
    uvicorn.run(app, host=MCP_HOST, port=MCP_PORT)
