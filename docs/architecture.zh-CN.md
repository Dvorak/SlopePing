# 架构说明

语言：[English](architecture.en.md) | 中文 | [Deutsch](architecture.de.md)

本文说明项目实现细节。日常使用请看 [README.zh-CN.md](../README.zh-CN.md)。

SlopePing 聚焦 Neuss Skihalle 教练在 Allrounder 教练门户里的排班查看和课程提醒流程。

## 模块概览

- `run_checker.py`
  兼容入口。把 `src/` 加入 `sys.path`，然后调用 `slopeping.cli.main()`。
- `scripts/webhook_server.py`
  webhook 服务的兼容入口，调用 `slopeping.server.main()`。
- `src/slopeping/cli.py`
  定义 checker CLI 参数并将动作分发给 `slopeping.checker.run()`。
- `src/slopeping/server.py`
  读取并校验 webhook server 配置，然后启动 Uvicorn。
- `src/slopeping/config.py`
  读取 `.env`，生成类型化配置和统一的 `var/` 运行路径。
- `src/slopeping/browser.py`
  负责 Playwright 启动、登录、页面跳转、新页面切换和截图。
- `src/slopeping/parser.py`
  找到排班表，把表格行转换成课程记录。
- `src/slopeping/state.py`
  定义课程记录，读写 `var/state.json` 及备份，并对比本次和上次课程。
- `src/slopeping/notify.py`
  通过 ntfy 发送通知，并保留 console fallback。
- `src/slopeping/webhook.py`
  定义 FastAPI 路由，协调缓存读取、日历导出和二次确认后的远程操作。
- `src/slopeping/web_views.py`
  生成手机控制页、确认页、结果页和日历页 HTML。
- `src/slopeping/execution_lock.py`
  为 checker、CLI 和 Webhook 提供共用的跨进程浏览器锁。
- `src/slopeping/health.py` 与 `src/slopeping/retry.py`
  保存运行健康状态，并只重试允许恢复的瞬时错误。
- `src/slopeping/maintenance.py`
  清理过期截图和日历文件，并轮转超大日志。
- `src/slopeping/security.py` 与 `src/slopeping/replay.py`
  签发短期 HMAC token，并阻止最终动作表单重复提交。
- `src/slopeping/runtime_migration.py`
  将旧根目录运行数据安全迁移到 `var/`。
- `src/slopeping/ui_preview.py`
  用匿名课程调用同一套页面模板，生成离线 HTML 和手机尺寸截图；不会访问门户。
- `scripts/generate_ui_previews.py`
  开发与文档使用的 UI 预览入口，不是生产服务。
- `src/slopeping/ics_generator.py`
  为课程生成 Europe/Berlin 时区的 `.ics` 日历事件。

正式运行入口只有 `run_checker.py` 和 `scripts/webhook_server.py`。
`scripts/run_checker.sh` 与 `scripts/run_webhook_server.sh` 仅负责 launchd 环境、
日志路径和虚拟环境检查。

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
11. 从 `var/state.json` 读取上次记录。
12. 对比本次和上次记录。
13. 根据需要通过 ntfy 通知。
14. 将当前记录写回 `var/state.json`，并保留上一版备份。

如果传入 `--accept` 或 `--decline`，SlopePing 会执行动作流程，而不是普通的通知和保存流程：

1. 登录并打开排班页。
2. 解析表格记录及对应 DOM 行。
3. 通过 `lesson_id`、完整 hash key 或 hash 前缀匹配课程。
4. 如果课程不是 `pending`，拒绝执行。
5. 选择 `Bestätigen` 或 `Absagen`。
6. 点击 `Speichern`。
7. 保存操作前后截图。
8. 向 `var/actions.log` 追加一行 JSON 日志。

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

如果这个 key 不存在于 `var/state.json`，就是新课程。

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

如果配置了 `ACTION_WEBHOOK_BASE_URL` 和 `ACTION_WEBHOOK_TOKEN`，ntfy 会签发
默认 24 小时有效的 HMAC 安全链接：

- `Open SlopePing`：打开 `/control?token=...`
- `Open calendar page`：打开 `/calendar?token=...`

通知不会直接执行确认或拒绝。控制页和日历页默认读取上一次保存的 `var/state.json`
快照，所以打开页面不会启动 Playwright。`/actions/execute` 会在二次确认后登录并
重新检查实时 Allrounder 页面，确认成功后再保存。

二次确认页会签发默认 10 分钟有效、绑定课程和动作的执行 token。nonce 在执行前
持久记录，同一表单不能重复提交。所有浏览器入口共用跨进程文件锁，同一时间只允许
一个 checker、CLI 或 Webhook 动作运行。

## 可靠性保护

- 上一次有课程而本次为 0 条时，第一次保留旧状态；连续第二次结构完整的空表才接受。
- 存在数据行但缺少日期、时间、地点或课程名时 parser 直接失败。
- 普通检查只对 Playwright 和网络类瞬时错误有限重试；课程动作不自动重试。
- `var/health.json` 记录开始时间、耗时、课程数量、连续失败和错误分类。
- 首次失败、达到阈值和故障后恢复分别发送状态通知。
- 截图和日历按天数与数量保留，日志按大小轮转。

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

## 质量基线

- `tests/fixtures/` 保存匿名化排班表 HTML，不包含真实账号或课程数据。
- parser fixture 测试使用本机无头 Chromium，不访问 Allrounder。
- 动作安全测试验证非 pending、动作不可用和直接远程动作不会触发页面修改。
- `./scripts/check.sh` 统一运行 Ruff 格式、Ruff lint、mypy 和 pytest。
- `.github/workflows/ci.yml` 在 Python 3.11 上运行相同检查。
- `requirements.txt` 和 `requirements-dev.txt` 固定直接依赖版本。

## 运行时文件

- `.env`
  本地密钥和用户配置。Git 忽略。
- `var/state.json` 与 `var/state.json.bak`
  上一次成功解析的课程状态及上一版备份。Git 忽略。
- `var/screenshots/`
  成功和失败截图。Git 忽略。
- `var/actions.log`
  CLI 和 webhook 操作历史，JSON lines 格式。Git 忽略。
- `var/calendar_events/`
  webhook 操作生成的 `.ics` 文件。Git 忽略。
- `var/health.json`
  最近运行结果与连续异常状态。Git 忽略。
- `var/logs/`
  checker、Webhook 和 launchd 日志。Git 忽略。

## 安全说明

- 不要提交 `.env`。
- `NTFY_TOPIC` 要设置得长且私密。
- 公共 `ntfy.sh` 默认不会给 topic 加密码保护。
- 程序会打印运行步骤，但不会打印密码。
- webhook server 默认监听 `127.0.0.1`。只有在可信网络或安全 tunnel 后面，才建议使用 `0.0.0.0`。
- URL 里只有短期签名 token，长期 `ACTION_WEBHOOK_TOKEN` 只保存在 `.env`。
- 短期 token 仍属于敏感凭据；公网访问依然必须使用 HTTPS 和额外认证层。
