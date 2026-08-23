# 考试宝题库爬取工具 - Dockerfile
# 支持多阶段构建，最终镜像约 500MB

# ============================================
# 阶段1: 基础构建环境
# ============================================
FROM python:3.12-slim AS builder

# 设置工作目录
WORKDIR /app

# 安装系统依赖（构建时需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    libatspi2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 安装Playwright Chromium
RUN playwright install chromium && \
    playwright install-deps chromium

# ============================================
# 阶段2: 运行时镜像
# ============================================
FROM python:3.12-slim AS runtime

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    DEBIAN_FRONTEND=noninteractive

# 创建非root用户
RUN groupadd -r appuser && useradd -r -g appuser appuser

# 安装运行时系统依赖（Chromium运行所需）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    libatspi2.0-0 \
    fonts-liberation \
    fonts-dejavu-core \
    fontconfig \
    && rm -rf /var/lib/apt/lists/* && \
    fc-cache -f -v

# 从builder阶段复制Python包
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 从builder阶段复制Playwright浏览器
COPY --from=builder /root/.cache/ms-playwright /ms-playwright

# 设置工作目录
WORKDIR /app

# 复制应用代码
COPY --chown=appuser:appuser . .

# 创建输出和日志目录
RUN mkdir -p /app/output /app/logs && \
    chown -R appuser:appuser /app/output /app/logs

# 切换到非root用户
USER appuser

# 暴露端口
EXPOSE 5678

# 健康检查（使用专用 /health 端点，返回 503 时标记不健康）
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5678/health')" || exit 1

# 启动命令（生产环境用gunicorn，开发环境用python app.py）
CMD ["gunicorn", "--bind", "0.0.0.0:5678", "--workers", "1", "--timeout", "120", "--access-logfile", "-", "app:app"]