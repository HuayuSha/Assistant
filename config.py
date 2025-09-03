# API配置
BASE_URL = "https://chatgtp.vin/v1"
API_KEY = "sk-P2pSLjuCWtHZEU78nfPGCkbZtgesZppuVonLeM9Lms7WImyO"
MODEL = "auto"

# MCP服务器配置
MCP_HOST = "localhost"
MCP_PORT = 8080
MCP_NAME = "本地MCP服务器"
MCP_VERSION = "1.0.0"

# 聊天记录配置
# JSONL 文件路径，用于持久化助手对话记录
CHAT_LOG_PATH = "logs/chat_history.jsonl"

# 系统提示与历史窗口
SYSTEM_PROMPT = (
    "你是用户的私人秘书、好友与老师，语气温和、主动、负责。"
    "当用户谈到计划/进度时，帮助规划、检查与总结；"
    "必要时提出2-3条可执行的建议，并确认是否要将更改写入今日计划。"
)

# 发送到大模型时，附带的最近聊天条数（user/assistant 轮次）
CHAT_HISTORY_WINDOW = 50
