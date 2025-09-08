import requests
import json
from typing import Dict, Any

class MCPTestClient:
    """MCP服务器测试客户端"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
    
    def test_server_info(self):
        """测试服务器信·息"""
        try:
            response = requests.get(f"{self.base_url}/")
            print("服务器信息:")
            print(json.dumps(response.json(), indent=2, ensure_ascii=False))
            return response.json()
        except Exception as e:
            print(f"获取服务器信息失败: {e}")
            return None
    
    def test_get_tools(self):
        """测试获取工具列表"""
        try:
            response = requests.get(f"{self.base_url}/tools")
            print("\n可用工具:")
            print(json.dumps(response.json(), indent=2, ensure_ascii=False))
            return response.json()
        except Exception as e:
            print(f"获取工具列表失败: {e}")
            return None
    
    def test_chat_completion(self, message: str, tools: list = None):
        """测试聊天完成"""
        try:
            data = {
                "model": "gpt-3.5-turbo",
                "messages": [{"role": "user", "content": message}],
                "max_tokens": 1000
            }
            
            if tools:
                data["tools"] = tools
            
            response = requests.post(
                f"{self.base_url}/v1/chat/completions",
                json=data,
                headers={"Content-Type": "application/json"}
            )
            
            print(f"\n聊天请求: {message}")
            print("响应:")
            print(json.dumps(response.json(), indent=2, ensure_ascii=False))
            return response.json()
        except Exception as e:
            print(f"聊天请求失败: {e}")
            return None
    
    def test_tool_calls(self):
        """测试工具调用"""
        # 测试获取时间
        print("\n=== 测试工具调用 ===")
        
        # 获取时间工具
        time_tool = {
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
        }
        
        # 计算工具
        calc_tool = {
            "type": "function",
            "function": {
                "name": "calculate",
                "description": "计算数学表达式",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "expression": {
                            "type": "string",
                            "description": "数学表达式"
                        }
                    },
                    "required": ["expression"]
                }
            }
        }
        
        # 天气工具
        weather_tool = {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "获取天气信息",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {
                            "type": "string",
                            "description": "城市名称"
                        }
                    },
                    "required": []
                }
            }
        }
        
        # 测试各种工具调用
        tools_to_test = [
            ([time_tool], "请告诉我现在的时间"),
            ([calc_tool], "请计算 15 * 8 + 23"),
            ([weather_tool], "请告诉我北京的天气"),
            ([time_tool, calc_tool, weather_tool], "请同时获取时间、计算2+3、查询上海天气")
        ]
        
        for tools, message in tools_to_test:
            print(f"\n--- 测试: {message} ---")
            self.test_chat_completion(message, tools)
    
    def test_health_check(self):
        """测试健康检查"""
        try:
            response = requests.get(f"{self.base_url}/health")
            print("\n健康检查:")
            print(json.dumps(response.json(), indent=2, ensure_ascii=False))
            return response.json()
        except Exception as e:
            print(f"健康检查失败: {e}")
            return None

def main():
    """主测试函数"""
    print("开始测试MCP服务器...")
    
    client = MCPTestClient()
    
    # 测试基本功能
    client.test_server_info()
    client.test_get_tools()
    client.test_health_check()
    
    # 测试普通聊天
    client.test_chat_completion("你好，请介绍一下你自己")
    
    # 测试工具调用
    client.test_tool_calls()
    
    print("\n测试完成！")

if __name__ == "__main__":
    main()
