# Windows 本地运行

## 安装

```powershell
python -m venv venv
.\venv\Scripts\python -m pip install -r requirements.txt
.\venv\Scripts\playwright install chromium
```

## 启动与停止

```powershell
.\start-local.ps1
.\stop-local.ps1
```

服务默认只监听 `127.0.0.1:5678`，不会暴露到局域网。运行日志位于 `logs/`。

## 浏览器连接

Chrome/Edge 136 及以上版本会忽略默认用户目录上的远程调试参数，因此项目为
Windows 浏览器使用独立配置目录：

```text
data/browser-profiles/
```

首次使用时在工具页面点击“启动Chrome”，然后在打开的浏览器中登录考试宝。
登录态会保存在独立配置目录中。

## 支持输入的题库地址

- `https://www.kaoshibao.com/e_classify/paper/<id>`
- `https://www.kaoshibao.com/ti/<id>/`
- `https://www.kaoshibao.com/paperInfo/<id>`
- 纯数字题库 ID

分类页会自动解析到真实练习试卷 ID；解析失败时会回退到直接访问原始试卷 ID。
