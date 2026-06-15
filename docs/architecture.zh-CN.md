# 架构说明

语言：[English](architecture.en.md) | 中文 | [Deutsch](architecture.de.md)

本文说明项目实现细节。日常使用请看 [README.zh-CN.md](../README.zh-CN.md)。

SlopePing 聚焦 Neuss Skihalle 教练在 Allrounder 教练门户里的排班查看和课程提醒流程。

## 模块概览

- `run_checker.py`
  入口文件。把 `src/` 加入 `sys.path`，然后调用
  `slopeping.checker.run()`。
- `scripts/webhook_server.py`
  启动 FastAPI webhook / 手机控制页服务。
- `src/slopeping/config.py`
  读取 `.env`，生成类型化配置。
- `src/slopeping/browser.py`
  负责 Playwright 启动、登录、页面跳转、新页面切换和截图。
- `src/slopeping/parser.py`
  找到排班表，把表格行转换成课程记录。
- `src/slopeping/state.py`
  定义课程记录，读写 `state.json`，并对比本次和上次课程。
- `src/slopeping/notify.py`
  通过 ntfy 发送通知，并保留 console fallback。
- `src/slopeping/webhook.py`
  提供手机控制页、日历导出和需要二次确认的远程操作。
- `src/slopeping/ics_generator.py`
  为课程生成 Europe/Berlin 时区的 `.ics` 日历事件。

## 运行流程

1. 从 `.env` 读取配置。
2. 启动 Playwright Chromium。
3. 打开登录页。
4. 填入用户名和密码。
5. 点击 `Anmelden`。
6. 打开 `Meine Daten` -> `Arbeitsplan/Verfügbarkeit`。
7. 检测并切换到新打开的排班页面/tab。
8. 等待 `table#TAB` 或 `Übersicht` 文本。
9. 解析课程。
10. 保存截图。
11. 从 `state.json` 读取上次记录。
12. 对比本次和上次记录。
13. 根据需要通过 ntfy 通知。
14. 将当前记录写回 `state.json`。

如果传入 `--accept` 或 `--decline`，SlopePing 会执行动作流程，而不是普通的通知和保存流程：

1. 登录并打开排班页。
2. 解析表格记录及对应 DOM 行。
3. 通过 `lesson_id`、完整 hash key 或 hash 前缀匹配课程。
4. 如果课程不是 `pending`，拒绝执行。
5. 选择 `Bestätigen` 或 `Absagen`。
6. 点击 `Speichern`。
7. 保存操作前后截图。
8. 向 `actions.log` 追加一行 JSON 日志。

## 排班表解析

优先使用选择器：

```text
table#TAB
```

解析器期望这些列：

- `Tag`
- `Von`
- `Bis`
- `Raum/Ort`
- `Trainingsbezeichnung`
- `Bestätigung`

每条解析出的课程还会带上：

- `confirmation_status`：`confirmed`、`pending` 或 `unknown`
- `available_actions`：从该行下拉框读取到的可选动作

状态识别规则：

- `confirmed`：确认单元格文本包含 `Bestätigt`
- `pending`：确认单元格里有 `select`，并且选项包含 `Bestätigen` 和 `Absagen`
- `unknown`：以上规则都不匹配

如果 `table#TAB` 不可见，会尝试找 `Übersicht` 附近的表格，再 fallback 到按表头扫描所有表格。

## 变化检测

每条课程的稳定 key 来自：

```text
Tag + Von + Bis + Raum/Ort + Trainingsbezeichnung
```

如果这个 key 不存在于 `state.json`，就是新课程。

如果 key 已存在，但完整记录变化了，例如 `Bestätigung` 变了，就是状态变化。

正常模式会通知新课程，以及需要处理的 pending 课程。测试阶段可以设置：

```dotenv
NOTIFY_ALWAYS_SEND_REPORT=true
```

这样每次成功运行都会发送当前课程报告。

如果被通知的课程里有 pending 状态，通知标题会是：

```text
SlopePing: action needed
```

SlopePing 不会自动选择 `Bestätigen` 或 `Absagen`，也不会点击 `Speichern`。

普通检查运行时，pending 课程会在终端打印可复制命令：

```bash
python run_checker.py --accept "LESSON_ID"
python run_checker.py --decline "LESSON_ID"
```

## 手机控制流程

如果配置了 `ACTION_WEBHOOK_BASE_URL` 和 `ACTION_WEBHOOK_TOKEN`，ntfy 会增加安全链接：

- `Open SlopePing`：打开 `/control?token=...`
- `Open calendar page`：打开 `/calendar?token=...`

通知不会直接执行确认或拒绝。控制页和日历页默认读取上一次保存的 `state.json`
快照，所以打开页面不会启动 Playwright。`/actions/execute` 会在二次确认后登录并
重新检查实时 Allrounder 页面，确认成功后再保存。

webhook 动作路径带有进程内锁，同一时间只允许一个远程操作运行。

## ntfy 通知

程序会 POST 纯文本到：

```text
{NTFY_SERVER}/{NTFY_TOPIC}
```

通知内容包含：

- 测试报告模式下的当前全部课程
- 待确认的新课程
- `Tag`, `Von`, `Bis`, `Raum/Ort`, `Trainingsbezeichnung`, `Bestätigung`
- `confirmation_status`
- `available_actions`

如果 ntfy 配置缺失或发送失败，程序会把同样内容打印到 console，并继续运行。

## 运行时文件

- `.env`
  本地密钥和用户配置。Git 忽略。
- `state.json`
  上一次成功解析的课程状态。Git 忽略。
- `screenshots/`
  成功和失败截图。Git 忽略。
- `actions.log`
  CLI 和 webhook 操作历史，JSON lines 格式。Git 忽略。
- `calendar_events/`
  webhook 操作生成的 `.ics` 文件。Git 忽略。

## 安全说明

- 不要提交 `.env`。
- `NTFY_TOPIC` 要设置得长且私密。
- 公共 `ntfy.sh` 默认不会给 topic 加密码保护。
- 程序会打印运行步骤，但不会打印密码。
- webhook server 默认监听 `127.0.0.1`。只有在可信网络或安全 tunnel 后面，才建议使用 `0.0.0.0`。
- webhook token 仍然会出现在 URL 中，所以不要在没有 HTTPS 和更强认证的情况下暴露到公网。
