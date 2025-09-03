@echo off
echo 测试MCP服务器...
echo.
echo 请确保服务器正在运行（在另一个窗口中运行 start_server.bat）
echo.
echo 按任意键开始测试...
pause >nul

python test_client.py

echo.
echo 测试完成，按任意键退出...
pause >nul
