# SlopePing

语言：[English](README.md) | 中文 | [Deutsch](README.de.md)

SlopePing 是为 Neuss Skihalle 教练设计的排班提醒工具。它会登录 Allrounder
教练门户，打开 `Arbeitsplan/Verfügbarkeit` 页面，读取 `Übersicht` 排班表，并在
出现新课程或课程需要确认时通过 ntfy 推送到手机。

第一版保持简单：Python、Playwright、本地 `.env` 配置、本地 `state.json`，以及
ntfy 通知。

## 功能

- 打开 `https://allrounder-jobs.de/login`
- 使用 `SKI_USERNAME` 和 `SKI_PASSWORD` 登录
- 打开 `Meine Daten` -> `Arbeitsplan/Verfügbarkeit`
- 切换到排班页面 `https://anmeldung.allrounder.de/do`
- 解析排班表字段：
  `Tag`, `Von`, `Bis`, `Raum/Ort`, `Trainingsbezeichnung`, `Bestätigung`
- 识别确认状态：
  `confirmed`, `pending`, `unknown`
- 将带有 `Bestätigen` / `Absagen` 下拉操作的课程标记为需要处理
- 每次成功检查后保存截图
- 将当前课程和 `state.json` 里的上次状态对比
- 发现新课程或待确认课程时发送 ntfy 通知
- 通知里带 `Open SlopePing`，可以打开手机控制页
- 手机控制页会在真正确认/拒绝前再次让你确认
- 可以把课程导出为 `.ics` 日历文件
- 测试阶段可以每次运行都发送当前课程报告

SlopePing 只识别并提醒需要处理的课程。它只有在你明确运行 CLI 命令，或在手机控制页
二次确认后，才会点击 `Bestätigen`、`Absagen` 和 `Speichern`。

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

如果要使用手机控制页，填写 webhook：

```dotenv
ACTION_WEBHOOK_TOKEN=your-generated-secure-token
ACTION_WEBHOOK_BASE_URL=http://YOUR_LOCAL_IP:8000
WEBHOOK_HOST=127.0.0.1
WEBHOOK_PORT=8000
```

手机通过局域网访问时，`ACTION_WEBHOOK_BASE_URL` 要写电脑的局域网 IP。只有在可信网络里才把 `WEBHOOK_HOST` 改成 `0.0.0.0`。

测试阶段，如果希望每次成功运行都收到通知：

```dotenv
NOTIFY_ALWAYS_SEND_REPORT=true
```

正常使用时，只在发现新课程或待确认课程时通知：

```dotenv
NOTIFY_ALWAYS_SEND_REPORT=false
```

## 运行

如果要使用手机控制页，先启动 webhook server：

```bash
cd SlopePing
source .venv/bin/activate
python scripts/webhook_server.py
```

然后运行检查：

```bash
cd SlopePing
source .venv/bin/activate
python run_checker.py
```

终端会打印每一步：登录、跳转、解析、截图、对比、通知状态。

如果发现 pending 课程，终端还会直接打印可复制的操作命令。

手机通知里的 `Open SlopePing` 会打开控制页。这里可以查看当前课程、下载日历文件，
也可以进入确认/拒绝页面。确认或拒绝动作需要再点一次确认按钮，不会因为误触 ntfy
通知就直接执行。

## 用 CLI 确认或拒绝

SlopePing 只有在你明确运行下面命令时，才会执行确认/拒绝操作：

```bash
python run_checker.py --accept "LESSON_KEY_OR_ID"
python run_checker.py --decline "LESSON_KEY_OR_ID"
```

推荐使用 ntfy 或 console 消息里的 `lesson_id`，例如：

```text
17.06.2026|14:00|16:00|Skischule|Extraschicht Skischule
```

`--accept` 会选择 `Bestätigen`。`--decline` 会选择 `Absagen`。之后 SlopePing
会点击 `Speichern`，保存操作前后截图，并写入 `actions.log`。

安全规则：

- 只能操作 `pending` 课程。
- 如果找不到课程、下拉框、动作选项或 `Speichern` 按钮，SlopePing 会打印清晰错误并停止。
- ntfy 通知本身不会自动触发任何确认或拒绝动作。
- webhook server 默认只监听本机 `127.0.0.1`。如果手机需要通过局域网访问，可以在可信网络下设置 `WEBHOOK_HOST=0.0.0.0`，并把 `ACTION_WEBHOOK_BASE_URL` 改成电脑的局域网地址。

## 运行时生成的文件

- `state.json`：上一次课程状态
- `actions.log`：手动确认/拒绝操作历史
- `calendar_events/`：webhook 操作生成的日历文件
- `screenshots/`：成功和失败截图

这些文件都已被 Git 忽略。

## 常见问题

- 登录失败：检查 `SKI_USERNAME` 和 `SKI_PASSWORD`。
- 页面打开了但没有解析到课程：看 `screenshots/` 里最新截图。
- 终端显示 ntfy 已发送但手机没响：检查手机通知权限、server、topic 拼写。
- 想测试通知但没有新课程：设置 `NOTIFY_ALWAYS_SEND_REPORT=true`。
- 如果课程需要处理，通知标题会是 `SlopePing: action needed`，正文会显示可选动作。

## 更多说明

实现细节单独放在：

- [Architecture notes, English](docs/architecture.en.md)
- [架构说明，中文](docs/architecture.zh-CN.md)
- [Architekturhinweise, Deutsch](docs/architecture.de.md)
