@echo off
echo 启动MCP服务器Web界面...
echo.
echo 请确保已安装Python依赖：
echo pip install -r requirements.txt
echo.
echo Web界面将在 http://localhost:8080 启动
echo 按任意键启动Web界面...
pause >nul

python web_interface.py

echo.
echo Web界面已停止，按任意键退出...
pause >nul

