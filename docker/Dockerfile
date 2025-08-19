FROM python:3.10-slim

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    curl \
    texlive-latex-base \
    texlive-latex-recommended \
    texlive-latex-extra \
    texlive-fonts-recommended \
    texlive-fonts-extra \
    texlive-bibtex-extra \
    biber \
    libxkbcommon0 \
    && rm -rf /var/lib/apt/lists/*

# 安装 Node.js 18.x
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# 安装 Claude Code SDK CLI
RUN npm install -g @anthropic-ai/claude-code

# 安装常用LaTeX宏包（使用实际可用的包）
RUN apt-get update && apt-get install -y \
    texlive-science \
    texlive-pictures \
    texlive-pstricks \
    texlive-publishers \
    texlive-humanities \
    texlive-latex-extra \
    texlive-bibtex-extra \
    texlive-fonts-extra \
    texlive-lang-all \
    texlive-games \
    texlive-music \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制requirements
COPY docker/requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 安装 Playwright 浏览器和系统依赖
RUN apt-get update && apt-get install -y \
    fonts-unifont \
    fonts-liberation \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*
RUN python -m playwright install-deps chromium || true
RUN python -m playwright install chromium

# 复制服务器代码和相关模块
COPY core ./core
COPY tools ./tools
COPY utils ./utils

# 创建工作空间目录
RUN mkdir -p /workspace

# 暴露端口
EXPOSE 8001

# 启动服务
CMD ["python", "-m", "core.server"]
