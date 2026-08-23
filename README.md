# 考试宝题库爬取工具

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)
![Tests](https://img.shields.io/badge/Tests-112%20Passing-brightgreen)
![Score](https://img.shields.io/badge/Score-9.4%2F10-blueviolet)
![Docker](https://img.shields.io/badge/Docker-Ready-blue?logo=docker&logoColor=white)

自动爬取考试宝(kaoshibao.com)已购买题库的全部题目、选项、正确答案和解析，导出为格式化的 Excel 文件，同时支持 PostgreSQL 数据库存储。

## 核心特性

- **Chrome CDP 模式** — 连接已登录的 Chrome 浏览器，直接复用完整登录态（包括 httpOnly cookies），无需手动管理 cookies
- **跨平台支持** — Windows / Linux 自动检测浏览器路径，Linux 下通过 Xvfb 虚拟显示器运行 Chrome
- **noVNC 远程浏览器** — 服务器部署时通过 Web 浏览器远程操作 Chrome 登录考试宝，无需桌面环境
- **多种读取模式** — OCR 模式（最准）、DOM 模式（最快）、混合模式（推荐）、竞赛模式（三种同时运行对比）
- **多任务并行** — 最多 5 个题库同时爬取，每个任务独立标签页、独立进度
- **分段并行爬取** — 单个题库可拆分为 2-5 个分段并行爬取，速度提升 2-5 倍
- **批量导入** — 一次输入多个题库 ID（最多 10 个），批量启动任务
- **断点续传** — 每道题自动保存进度到 JSON，中断后可从断点继续
- **Web 可视化界面** — Flask 驱动的单页应用，实时进度条、日志、文件管理
- **命令行模式** — 支持 `python scrape.py <ID>` 直接运行
- **反字体反爬** — 通过 OCR 截图识别绕过考试宝的自定义字体混淆机制
- **响应式 UI** — 适配手机/平板/折叠屏/桌面，支持暗色模式（手动切换或跟随系统）
- **多格式导出** — Excel / CSV / JSON 三种格式，从历史进度一键导出
- **PostgreSQL 存储** — 爬取结果同时保存到数据库，支持连接池和批量插入
- **安全加固** — CSP 头、CSRF 防护、Origin 验证、速率限制、路径穿越防护、可选认证
- **OpenAPI 3.0** — 标准 API 规范，`/api/docs` 端点返回完整 spec
- **CI/CD** — GitHub Actions 自动测试（多版本 Python）+ 代码覆盖率 + ruff lint

## 快速开始

### 方式一：Docker 容器化部署

```bash
docker-compose up -d --build
docker-compose logs -f
```

### 方式二：手动安装

```bash
pip install -r requirements.txt
playwright install chromium
python app.py
```

### 方式三：生产环境部署（gunicorn + nginx）

```bash
pip install -r requirements.txt
gunicorn --bind 0.0.0.0:5678 --workers 1 --timeout 120 app:app
```

### 使用

1. 在 Chrome 中登录考试宝 (kaoshibao.com)
2. 在 Web 界面输入题库 ID，点击"添加任务"
3. 等待爬取完成，下载 Excel 文件

### 服务器远程登录（noVNC）

服务器无桌面环境时，通过 noVNC 在浏览器中远程操作 Chrome 登录：

1. 打开 `http://<服务器IP>:<端口>/vnc/vnc.html`（如 `http://111.229.32.106:9007/vnc/vnc.html`）
2. 输入 VNC 密码，看到 Chrome 浏览器界面
3. 在 Chrome 中登录考试宝（扫码或账号登录）
4. 登录成功后，打开 Web 管理界面 `http://<服务器IP>:<端口>/web/` 开始爬取

## 读取模式

| 模式 | 速度 | 准确度 | 说明 |
|------|------|--------|------|
| **Hybrid（推荐）** | 快 | 高 | DOM 读取结构 + OCR 仅读取题干文字 |
| **OCR** | 慢 | 最高 | 全部通过截图 + RapidOCR 识别，完全绕过字体反爬 |
| **DOM** | 最快 | 低 | 直接读取 DOM，受字体混淆影响，文字可能乱码 |
| **Race** | — | — | 三种模式同时运行，用于对比选择最适合的模式 |

## 文件结构

```
kaoshibao/
├── app.py                        # Flask Web 服务器（路由 + 任务管理 + 安全）
├── scraper_core.py               # 核心爬取模块（浏览器 + OCR + 解析 + 存储）
├── db_store.py                   # PostgreSQL 存储层（连接池 + 批量插入）
├── scrape.py                     # 命令行入口
├── logging_config.py             # 日志配置
├── test_all.py                   # 测试套件（112 个测试用例）
├── templates/
│   └── index.html                # Web 单页应用（响应式 + 暗色模式）
├── .github/workflows/ci.yml      # CI/CD 流水线
├── .coveragerc                   # 代码覆盖率配置
├── .env.example                  # 环境变量示例
├── pyproject.toml                # ruff 代码风格配置
├── Dockerfile                    # 多阶段构建 + gunicorn
├── docker-compose.yml            # 容器编排
├── kaoshibao.service             # systemd 服务文件（依赖 xvfb.service）
├── xvfb.service                  # Xvfb 虚拟显示器服务（Linux Chrome 需要）
├── x11vnc.service                # VNC 服务器服务（连接 Xvfb display :99）
├── novnc.service                 # noVNC WebSocket 代理服务（Web 远程浏览器）
├── nginx_kaoshibao.conf          # nginx 反向代理配置（/web/ + /vnc/）
├── requirements.txt              # Python 依赖
└── OPTIMIZATION.md               # 优化记录文档（9 轮 69 项）
```

## REST API

API 文档通过 OpenAPI 3.0 规范提供，访问 `/api/docs` 获取完整 spec。

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | Web 界面 |
| GET | `/health` | 健康检查（含 ready/tasks_failed 字段） |
| GET | `/api/docs` | OpenAPI 3.0 规范 |
| GET | `/api/stats` | 监控指标 |
| GET | `/api/history` | 已爬取题库历史 |
| GET | `/api/tasks` | 所有任务状态 |
| POST | `/api/start` | 启动爬取任务 |
| POST | `/api/stop/<task_id>` | 停止任务 |
| GET | `/api/files` | Excel 文件列表 |
| GET | `/api/export/<paper_id>?format=` | 导出 xlsx/csv/json |
| POST | `/api/start-parallel` | 分段并行爬取 |
| POST | `/api/merge-segments` | 合并分段结果 |

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `FLASK_SECRET_KEY` | Flask 密钥 | 随机生成 |
| `AUTH_TOKEN` | API 认证 token（空则关闭） | 空 |
| `LOG_LEVEL` | 日志级别 | INFO |
| `CDP_PORT` | Chrome CDP 调试端口 | 9223 |
| `PG_HOST` | PostgreSQL 主机 | localhost |
| `PG_PORT` | PostgreSQL 端口 | 5432 |
| `PG_DATABASE` | 数据库名 | kaoshibao |
| `PG_USER` | 数据库用户 | postgres |
| `PG_PASSWORD` | 数据库密码（空则禁用） | 空 |

## 生产环境部署

### 腾讯云部署示例

```bash
# 1. 上传项目到 /var/www/kaoshibao
# 2. 创建虚拟环境
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
playwright install chromium

# 3. 配置环境变量
cp .env.example .env  # 编辑 .env 填入数据库信息

# 4. 安装 Linux 桌面组件（服务器无GUI时）
apt install -y xvfb x11vnc novnc
x11vnc -storepasswd <你的VNC密码> /etc/x11vnc.pass

# 5. 启动服务（systemd）
sudo cp kaoshibao.service xvfb.service x11vnc.service novnc.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now xvfb x11vnc novnc kaoshibao

# 6. 配置 nginx 反向代理
sudo cp nginx_kaoshibao.conf /etc/nginx/sites-available/kaoshibao
sudo ln -s /etc/nginx/sites-available/kaoshibao /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# 7. 通过 noVNC 远程登录考试宝
#    打开 http://<服务器IP>:<端口>/vnc/vnc.html → 输入VNC密码 → 登录考试宝
```

### Docker 部署

```bash
docker-compose up -d --build
# 含健康检查、资源限制、非 root 用户、gunicorn
```

## 运行测试

```bash
python test_all.py
# 112 个测试用例，覆盖：核心函数、API、安全、模板、配置、数据库
```

### CI/CD

GitHub Actions 自动运行：
- 多版本 Python 测试（3.10/3.11/3.12）
- 代码覆盖率报告（coverage.py）
- 代码风格检查（ruff）

## 技术栈

- **Python 3.10+** / Flask / gunicorn
- **Playwright** (async) — 浏览器自动化 / CDP 协议
- **RapidOCR** (ONNX Runtime) — OCR 引擎
- **Pillow** — 图片预处理
- **openpyxl** — Excel 生成
- **psycopg2** — PostgreSQL 连接池
- **Xvfb** — Linux 虚拟显示器（无 GUI 服务器运行 Chrome）
- **x11vnc + noVNC** — Web 远程浏览器（通过浏览器操作 Chrome）
- **nginx** — 反向代理

## 优化历程

经过 9 轮共 69 项优化，综合评分从 6.5 提升至 9.4/10。详见 [OPTIMIZATION.md](OPTIMIZATION.md)。

| 维度 | 初始 | 最终 |
|------|------|------|
| 代码质量 | 7.0 | 9.0 |
| UX/UI | 5.0 | 9.5 |
| 功能完整性 | 7.0 | 9.5 |
| 测试覆盖 | 6.0 | 9.5 |
| 安全性 | 7.0 | 9.0 |
| 可维护性 | 6.0 | 9.5 |
| 部署运维 | 8.0 | 9.5 |
| 性能 | 6.0 | 9.5 |
| **综合** | **6.5** | **9.4** |

## 许可证

MIT License — 详见 [LICENSE](LICENSE) 文件
