@echo off
echo 启动MCP服务器...
echo.
echo 请确保已安装Python依赖：
echo pip install -r requirements.txt
echo.
echo 按任意键启动服务器...
pause >nul

python mcp_server.py

echo.
echo 服务器已停止，按任意键退出...
pause >nul
