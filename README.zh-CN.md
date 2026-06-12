# SlopePing

语言：[English](README.md) | 中文 | [Deutsch](README.de.md)

SlopePing 是为 Neuss Skihalle 教练设计的排班提醒工具。它会登录 Allrounder
教练门户，打开 `Arbeitsplan/Verfügbarkeit` 页面，读取 `Übersicht` 排班表，并在
出现新课程时通过 ntfy 推送到手机。

第一版保持简单：Python、Playwright、本地 `.env` 配置、本地 `state.json`，以及
ntfy 通知。

## 功能

- 打开 `https://allrounder-jobs.de/login`
- 使用 `SKI_USERNAME` 和 `SKI_PASSWORD` 登录
- 打开 `Meine Daten` -> `Arbeitsplan/Verfügbarkeit`
- 切换到排班页面 `https://anmeldung.allrounder.de/do`
- 解析排班表字段：
  `Tag`, `Von`, `Bis`, `Raum/Ort`, `Trainingsbezeichnung`, `Bestätigung`
- 每次成功检查后保存截图
- 将当前课程和 `state.json` 里的上次状态对比
- 发现新课程时发送 ntfy 通知
- 测试阶段可以每次运行都发送当前课程报告

## 需要准备

- Python 3.11+
- Neuss Skihalle 教练系统的 Allrounder 教练门户账号
- 手机上安装 ntfy app，或使用其他 ntfy 客户端

## 安装

```bash
cd SlopePing
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
cp .env.example .env
```

## 配置 `.env`

编辑：

```bash
nano .env
```

填写登录信息：

```dotenv
SKI_USERNAME=your_username
SKI_PASSWORD=your_password
```

填写 ntfy：

```dotenv
NOTIFY_CHANNEL=ntfy
NTFY_SERVER=https://ntfy.sh
NTFY_TOPIC=your-long-private-topic
```

手机 ntfy app 里订阅同一个 `NTFY_SERVER` 和 `NTFY_TOPIC`。topic 要保密；知道
topic 的人都可以订阅。

测试阶段，如果希望每次成功运行都收到通知：

```dotenv
NOTIFY_ALWAYS_SEND_REPORT=true
```

正常使用时，只在发现新课程时通知：

```dotenv
NOTIFY_ALWAYS_SEND_REPORT=false
```

## 运行

```bash
cd SlopePing
source .venv/bin/activate
python run_checker.py
```

终端会打印每一步：登录、跳转、解析、截图、对比、通知状态。

## 运行时生成的文件

- `state.json`：上一次课程状态
- `screenshots/`：成功和失败截图

这些文件都已被 Git 忽略。

## 常见问题

- 登录失败：检查 `SKI_USERNAME` 和 `SKI_PASSWORD`。
- 页面打开了但没有解析到课程：看 `screenshots/` 里最新截图。
- 终端显示 ntfy 已发送但手机没响：检查手机通知权限、server、topic 拼写。
- 想测试通知但没有新课程：设置 `NOTIFY_ALWAYS_SEND_REPORT=true`。

## 更多说明

实现细节单独放在：

- [Architecture notes, English](docs/architecture.en.md)
- [架构说明，中文](docs/architecture.zh-CN.md)
- [Architekturhinweise, Deutsch](docs/architecture.de.md)
