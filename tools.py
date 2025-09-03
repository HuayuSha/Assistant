import json
import requests
import datetime
import os
import logging
from typing import Dict, Any, List, Generator
from config import BASE_URL, API_KEY, MODEL, CHAT_LOG_PATH, SYSTEM_PROMPT, CHAT_HISTORY_WINDOW

# 配置外部LLM API调用日志
def setup_llm_logging():
    """设置LLM API调用日志"""
    os.makedirs("logs", exist_ok=True)
    
    llm_logger = logging.getLogger('llm_api')
    llm_logger.setLevel(logging.INFO)
    
    # 避免重复添加handler
    if not llm_logger.handlers:
        file_handler = logging.FileHandler('logs/llm_api.log', encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        llm_logger.addHandler(file_handler)
    
    return llm_logger

llm_logger = setup_llm_logging()

class MCPTools:
    """MCP工具集合"""
    
    def __init__(self):
        self.base_url = BASE_URL
        self.api_key = API_KEY
        self.model = MODEL
    
    def _load_recent_history(self, limit: int) -> List[Dict[str, str]]:
        """读取最近 limit 条历史消息，转换为 OpenAI messages 结构。"""
        messages: List[Dict[str, str]] = []
        try:
            if not os.path.exists(CHAT_LOG_PATH):
                return messages
            lines: List[Dict[str, Any]] = []
            with open(CHAT_LOG_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                        role = obj.get("role")
                        content = obj.get("content", "")
                        if role in ("user", "assistant"):
                            lines.append({"role": role, "content": content})
                    except Exception:
                        continue
            if limit > 0:
                lines = lines[-limit:]
            # 直接返回 role/content 对
            messages.extend(lines)
        except Exception as e:
            llm_logger.error(f"读取历史失败: {e}")
        return messages
    
    def _build_messages(self, current_user_text: str) -> List[Dict[str, str]]:
        """构造发送给大模型的 messages: system + 最近历史 + 当前用户。"""
        messages: List[Dict[str, str]] = []
        # system
        if SYSTEM_PROMPT:
            messages.append({"role": "system", "content": SYSTEM_PROMPT})
        # history (最近N条记录)
        recent = self._load_recent_history(CHAT_HISTORY_WINDOW)
        messages.extend(recent)
        # current user
        messages.append({"role": "user", "content": current_user_text})
        return messages
    
    def get_current_time(self) -> Dict[str, Any]:
        """获取当前时间"""
        now = datetime.datetime.now()
        return {
            "current_time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "timestamp": now.timestamp(),
            "timezone": "Asia/Shanghai"
        }
    
    def get_weather(self, city: str = "北京") -> Dict[str, Any]:
        """获取天气信息（模拟）"""
        weather_data = {
            "city": city,
            "temperature": "22°C",
            "condition": "晴天",
            "humidity": "65%",
            "wind": "东北风 3级"
        }
        return weather_data
    
    def calculate(self, expression: str) -> Dict[str, Any]:
        """计算数学表达式"""
        try:
            allowed_chars = set('0123456789+-*/.() ')
            if not all(c in allowed_chars for c in expression):
                return {"error": "表达式包含不允许的字符"}
            result = eval(expression)
            return {
                "expression": expression,
                "result": result,
                "type": type(result).__name__
            }
        except Exception as e:
            return {"error": f"计算错误: {str(e)}"}
    
    def translate_text(self, text: str, target_lang: str = "en") -> Dict[str, Any]:
        """翻译文本（模拟）"""
        translations = {
            "你好": "Hello",
            "谢谢": "Thank you",
            "再见": "Goodbye"
        }
        if text in translations:
            return {
                "original": text,
                "translated": translations[text],
                "target_language": target_lang
            }
        else:
            return {
                "original": text,
                "translated": f"[{text}] (模拟翻译)",
                "target_language": target_lang
            }
    
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """获取文件信息"""
        try:
            if os.path.exists(file_path):
                stat = os.stat(file_path)
                return {
                    "file_path": file_path,
                    "exists": True,
                    "size": stat.st_size,
                    "modified": datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                    "is_file": os.path.isfile(file_path),
                    "is_directory": os.path.isdir(file_path)
                }
            else:
                return {
                    "file_path": file_path,
                    "exists": False,
                    "error": "文件不存在"
                }
        except Exception as e:
            return {
                "file_path": file_path,
                "error": f"获取文件信息失败: {str(e)}"
            }
    
    def list_directory(self, dir_path: str = ".") -> Dict[str, Any]:
        """列出目录内容"""
        try:
            if os.path.exists(dir_path) and os.path.isdir(dir_path):
                items = os.listdir(dir_path)
                files = []
                directories = []
                for item in items:
                    item_path = os.path.join(dir_path, item)
                    if os.path.isfile(item_path):
                        files.append(item)
                    elif os.path.isdir(item_path):
                        directories.append(item)
                return {
                    "directory": dir_path,
                    "files": files,
                    "directories": directories,
                    "total_files": len(files),
                    "total_directories": len(directories)
                }
            else:
                return {
                    "directory": dir_path,
                    "error": "目录不存在或不是目录"
                }
        except Exception as e:
            return {
                "directory": dir_path,
                "error": f"列出目录失败: {str(e)}"
            }
    
    def call_openai_api(self, prompt: str, max_tokens: int = 100) -> Dict[str, Any]:
        """调用OpenAI API"""
        start_time = datetime.datetime.now()
        
        # 记录请求信息
        llm_logger.info(f"=== 外部LLM API调用 ===")
        llm_logger.info(f"调用时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        llm_logger.info(f"API端点: {self.base_url}/chat/completions")
        llm_logger.info(f"请求方法: POST")
        llm_logger.info(f"请求头: {json.dumps({'Authorization': 'Bearer ***', 'Content-Type': 'application/json', 'Accept-Charset': 'utf-8'}, ensure_ascii=False)}")
        llm_logger.info(f"请求参数: model={self.model}, max_tokens={max_tokens}")
        llm_logger.info(f"请求内容: {prompt}")
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept-Charset": "utf-8"
            }
            data = {
                "model": self.model,
                "messages": self._build_messages(prompt),
                "max_tokens": max_tokens
            }
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=60
            )
            
            # 强制按UTF-8解码
            response.encoding = 'utf-8'
            
            end_time = datetime.datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # 记录响应信息
            llm_logger.info(f"=== 外部LLM API响应 ===")
            llm_logger.info(f"响应时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            llm_logger.info(f"响应状态码: {response.status_code}")
            llm_logger.info(f"响应头: {dict(response.headers)}")
            llm_logger.info(f"响应内容: {response.text}")
            llm_logger.info(f"请求耗时: {duration:.3f}秒")
            
            if response.status_code == 200:
                # 使用UTF-8文本进行解析，避免误判编码
                try:
                    result = json.loads(response.text)
                except Exception:
                    result = response.json()
                llm_logger.info(f"解析后的响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
                llm_logger.info(f"---")
                
                return {
                    "success": True,
                    "response": result["choices"][0]["message"]["content"],
                    "usage": result.get("usage", {})
                }
            else:
                llm_logger.error(f"API调用失败: {response.status_code}")
                llm_logger.error(f"错误响应: {response.text}")
                llm_logger.info(f"---")
                
                return {
                    "success": False,
                    "error": f"API调用失败: {response.status_code}",
                    "response_text": response.text
                }
        except Exception as e:
            end_time = datetime.datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            llm_logger.error(f"=== 外部LLM API异常 ===")
            llm_logger.error(f"异常时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            llm_logger.error(f"异常信息: {str(e)}")
            llm_logger.error(f"请求耗时: {duration:.3f}秒")
            llm_logger.info(f"---")
            
            return {
                "success": False,
                "error": f"请求异常: {str(e)}"
            }

    def stream_openai_api(self, prompt: str, max_tokens: int = 300) -> Generator[str, None, None]:
        """流式调用，按增量content产出文本块"""
        start_time = datetime.datetime.now()
        
        # 记录请求信息
        llm_logger.info(f"=== 外部LLM流式API调用 ===")
        llm_logger.info(f"调用时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        llm_logger.info(f"API端点: {self.base_url}/chat/completions")
        llm_logger.info(f"请求方法: POST (Stream)")
        llm_logger.info(f"请求头: {json.dumps({'Authorization': 'Bearer ***', 'Content-Type': 'application/json', 'Accept-Charset': 'utf-8'}, ensure_ascii=False)}")
        llm_logger.info(f"请求参数: model={self.model}, max_tokens={max_tokens}, stream=True")
        llm_logger.info(f"请求内容: {prompt}")
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept-Charset": "utf-8"
            }
            data = {
                "model": self.model,
                "messages": self._build_messages(prompt),
                "max_tokens": max_tokens,
                "stream": True
            }
            
            with requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=data,
                stream=True,
                timeout=300
            ) as r:
                r.raise_for_status()
                
                raw_chunks = []
                # 按字节读取并手动UTF-8解码，避免错码
                for raw in r.iter_lines(decode_unicode=False):
                    if not raw:
                        continue
                    line = raw.strip()
                    if line.startswith(b'data: '):
                        payload_bytes = line[len(b'data: '):].strip()
                    else:
                        payload_bytes = line
                    if payload_bytes == b'[DONE]':
                        break
                    payload = payload_bytes.decode('utf-8', errors='replace')
                    try:
                        obj = json.loads(payload)
                        delta = obj.get('choices', [{}])[0].get('delta', {})
                        chunk = delta.get('content')
                        if chunk:
                            raw_chunks.append(payload)
                            yield chunk
                    except Exception:
                        # 尝试兼容不同供应商流格式
                        try:
                            obj = json.loads(payload)
                            text = obj.get('choices', [{}])[0].get('message', {}).get('content')
                            if text:
                                raw_chunks.append(payload)
                                yield text
                        except Exception:
                            continue
                
                end_time = datetime.datetime.now()
                duration = (end_time - start_time).total_seconds()
                
                # 记录响应信息
                llm_logger.info(f"=== 外部LLM流式API响应 ===")
                llm_logger.info(f"响应时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
                llm_logger.info(f"响应状态: 200 OK (Stream)")
                llm_logger.info(f"原始流式数据块: {raw_chunks}")
                llm_logger.info(f"请求耗时: {duration:.3f}秒")
                llm_logger.info(f"---")
                
        except Exception as e:
            end_time = datetime.datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            llm_logger.error(f"=== 外部LLM流式API异常 ===")
            llm_logger.error(f"异常时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            llm_logger.error(f"异常信息: {str(e)}")
            llm_logger.error(f"请求耗时: {duration:.3f}秒")
            llm_logger.info(f"---")
            
            # 如果流式调用失败，回退到普通调用并模拟流式输出
            llm_logger.info(f"流式调用失败，回退到普通调用: {e}")
            try:
                result = self.call_openai_api(prompt, max_tokens)
                if result.get('success'):
                    content = result.get('response', '抱歉，我无法回复你的消息。')
                else:
                    content = f"API调用失败: {result.get('error', '未知错误')}"
                # 模拟流式输出，每次输出几个字符
                words = content.split()
                for i, word in enumerate(words):
                    if i == 0:
                        yield word
                    else:
                        yield ' ' + word
                    # 添加小延迟模拟流式效果
                    import time
                    time.sleep(0.05)
            except Exception as fallback_error:
                yield f"抱歉，API调用失败: {str(fallback_error)}"

# 创建工具实例
mcp_tools = MCPTools()
