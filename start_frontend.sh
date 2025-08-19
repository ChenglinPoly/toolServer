#!/bin/bash

echo "=== Tool Server 前端界面启动脚本 ==="

# 检查工具服务器是否运行
echo "1. 检查 Tool Server 状态..."
if curl -s http://localhost:8001/health > /dev/null 2>&1; then
    echo "✅ Tool Server 正在运行 (localhost:8001)"
else
    echo "❌ Tool Server 未运行，请先启动服务器："
    echo "   cd /Users/chenglin/Desktop/research/agent_framwork/tool_server_uni"
    echo "   python -m core.server --port 8001 --workspace ./workspace"
    echo ""
    echo "是否现在启动 Tool Server? (y/n)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        echo "启动 Tool Server..."
        cd /Users/chenglin/Desktop/research/agent_framwork/tool_server_uni
        python -m core.server --port 8001 --workspace ./workspace &
        SERVER_PID=$!
        echo "Tool Server 启动中 (PID: $SERVER_PID)..."
        sleep 5
        
        # 再次检查
        if curl -s http://localhost:8001/health > /dev/null 2>&1; then
            echo "✅ Tool Server 启动成功"
        else
            echo "❌ Tool Server 启动失败"
            exit 1
        fi
    else
        echo "请手动启动 Tool Server 后再运行此脚本"
        exit 1
    fi
fi

# 切换到前端目录
cd "$(dirname "$0")/frontend"

echo ""
echo "2. 启动前端服务器..."

# 检查可用的方法
if command -v python3 &> /dev/null; then
    echo "使用 Python3 启动 HTTP 服务器..."
    echo "前端地址: http://localhost:8080"
    echo ""
    echo "=== 前端服务器正在运行 ==="
    echo "按 Ctrl+C 停止服务器"
    echo ""
    python3 -m http.server 8080
elif command -v python &> /dev/null; then
    echo "使用 Python 启动 HTTP 服务器..."
    echo "前端地址: http://localhost:8080"
    echo ""
    echo "=== 前端服务器正在运行 ==="
    echo "按 Ctrl+C 停止服务器"
    echo ""
    python -m http.server 8080
elif command -v npx &> /dev/null; then
    echo "使用 npx serve 启动服务器..."
    echo "前端地址: http://localhost:8080"
    echo ""
    npx serve . -p 8080
else
    echo "❌ 未找到可用的服务器工具"
    echo "请手动在浏览器中打开 frontend/index.html"
    echo "或安装 Python/Node.js 后重试"
    
    # 尝试直接打开浏览器
    if command -v open &> /dev/null; then
        echo ""
        echo "尝试直接在浏览器中打开..."
        open index.html
    fi
fi 