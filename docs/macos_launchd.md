# macOS launchd Setup

Language: English | 中文

This guide shows how to run SlopePing automatically on macOS with `launchd`.
It covers two jobs:

- A scheduled checker job that runs `python run_checker.py`
- A webhook server job that keeps `python scripts/webhook_server.py` running

Paths below assume the project is here:

```text
/Users/zhang/SlopePing
```

Adjust the paths if your local checkout moves.

## English

### 1. Check The Project Manually First

Before using `launchd`, make sure both commands work in Terminal:

```bash
cd /Users/zhang/SlopePing
source .venv/bin/activate
python run_checker.py
python scripts/webhook_server.py
```

Stop the webhook server with `Ctrl+C` after the manual test.

### 2. Scheduled Checker Job

Create this file:

```text
~/Library/LaunchAgents/com.slopeping.checker.plist
```

Content:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.slopeping.checker</string>

  <key>WorkingDirectory</key>
  <string>/Users/zhang/SlopePing</string>

  <key>ProgramArguments</key>
  <array>
    <string>/Users/zhang/SlopePing/.venv/bin/python</string>
    <string>/Users/zhang/SlopePing/run_checker.py</string>
  </array>

  <key>StartInterval</key>
  <integer>900</integer>

  <key>StandardOutPath</key>
  <string>/Users/zhang/SlopePing/logs/checker.out.log</string>

  <key>StandardErrorPath</key>
  <string>/Users/zhang/SlopePing/logs/checker.err.log</string>
</dict>
</plist>
```

`StartInterval=900` means every 15 minutes.

Create the log directory:

```bash
mkdir -p /Users/zhang/SlopePing/logs
```

Load the job:

```bash
launchctl load ~/Library/LaunchAgents/com.slopeping.checker.plist
```

Run it once immediately:

```bash
launchctl start com.slopeping.checker
```

Check logs:

```bash
tail -f /Users/zhang/SlopePing/logs/checker.out.log
tail -f /Users/zhang/SlopePing/logs/checker.err.log
```

Unload it:

```bash
launchctl unload ~/Library/LaunchAgents/com.slopeping.checker.plist
```

### 3. Webhook Server Job

Create this file:

```text
~/Library/LaunchAgents/com.slopeping.webhook.plist
```

Content:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.slopeping.webhook</string>

  <key>WorkingDirectory</key>
  <string>/Users/zhang/SlopePing</string>

  <key>ProgramArguments</key>
  <array>
    <string>/Users/zhang/SlopePing/.venv/bin/python</string>
    <string>/Users/zhang/SlopePing/scripts/webhook_server.py</string>
  </array>

  <key>RunAtLoad</key>
  <true/>

  <key>KeepAlive</key>
  <true/>

  <key>StandardOutPath</key>
  <string>/Users/zhang/SlopePing/logs/webhook.out.log</string>

  <key>StandardErrorPath</key>
  <string>/Users/zhang/SlopePing/logs/webhook.err.log</string>
</dict>
</plist>
```

Load it:

```bash
launchctl load ~/Library/LaunchAgents/com.slopeping.webhook.plist
```

Check that it is running:

```bash
curl http://localhost:8000/health
tail -f /Users/zhang/SlopePing/logs/webhook.out.log
```

Unload it:

```bash
launchctl unload ~/Library/LaunchAgents/com.slopeping.webhook.plist
```

### 4. Important Notes

- `launchd` does not automatically use your interactive shell environment.
  Use absolute paths, as shown above.
- If phone access is needed, `.env` must contain a reachable
  `ACTION_WEBHOOK_BASE_URL` and usually `WEBHOOK_HOST=0.0.0.0` on a trusted
  local network.
- Keep `.env` private.
- If the checker opens a visible browser, make sure the Mac is logged in. For
  unattended use, consider `SKI_HEADLESS=true` after you have tested the flow.

---

## 中文

### 1. 先手动确认项目可运行

配置 `launchd` 之前，先在终端确认这两个命令能跑：

```bash
cd /Users/zhang/SlopePing
source .venv/bin/activate
python run_checker.py
python scripts/webhook_server.py
```

手动测试 webhook server 后，用 `Ctrl+C` 停止。

### 2. 定时检查课程

创建这个文件：

```text
~/Library/LaunchAgents/com.slopeping.checker.plist
```

内容：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.slopeping.checker</string>

  <key>WorkingDirectory</key>
  <string>/Users/zhang/SlopePing</string>

  <key>ProgramArguments</key>
  <array>
    <string>/Users/zhang/SlopePing/.venv/bin/python</string>
    <string>/Users/zhang/SlopePing/run_checker.py</string>
  </array>

  <key>StartInterval</key>
  <integer>900</integer>

  <key>StandardOutPath</key>
  <string>/Users/zhang/SlopePing/logs/checker.out.log</string>

  <key>StandardErrorPath</key>
  <string>/Users/zhang/SlopePing/logs/checker.err.log</string>
</dict>
</plist>
```

`StartInterval=900` 表示每 15 分钟运行一次。

创建日志目录：

```bash
mkdir -p /Users/zhang/SlopePing/logs
```

加载任务：

```bash
launchctl load ~/Library/LaunchAgents/com.slopeping.checker.plist
```

立刻运行一次：

```bash
launchctl start com.slopeping.checker
```

查看日志：

```bash
tail -f /Users/zhang/SlopePing/logs/checker.out.log
tail -f /Users/zhang/SlopePing/logs/checker.err.log
```

停止并卸载任务：

```bash
launchctl unload ~/Library/LaunchAgents/com.slopeping.checker.plist
```

### 3. 保持 webhook server 运行

创建这个文件：

```text
~/Library/LaunchAgents/com.slopeping.webhook.plist
```

内容：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.slopeping.webhook</string>

  <key>WorkingDirectory</key>
  <string>/Users/zhang/SlopePing</string>

  <key>ProgramArguments</key>
  <array>
    <string>/Users/zhang/SlopePing/.venv/bin/python</string>
    <string>/Users/zhang/SlopePing/scripts/webhook_server.py</string>
  </array>

  <key>RunAtLoad</key>
  <true/>

  <key>KeepAlive</key>
  <true/>

  <key>StandardOutPath</key>
  <string>/Users/zhang/SlopePing/logs/webhook.out.log</string>

  <key>StandardErrorPath</key>
  <string>/Users/zhang/SlopePing/logs/webhook.err.log</string>
</dict>
</plist>
```

加载任务：

```bash
launchctl load ~/Library/LaunchAgents/com.slopeping.webhook.plist
```

检查是否运行：

```bash
curl http://localhost:8000/health
tail -f /Users/zhang/SlopePing/logs/webhook.out.log
```

停止并卸载任务：

```bash
launchctl unload ~/Library/LaunchAgents/com.slopeping.webhook.plist
```

### 4. 注意事项

- `launchd` 不会自动使用你平时终端里的 shell 环境，所以 plist 里要使用绝对路径。
- 如果手机要访问 webhook，`.env` 里要设置手机能访问到的
  `ACTION_WEBHOOK_BASE_URL`。在可信局域网下通常还需要
  `WEBHOOK_HOST=0.0.0.0`。
- `.env` 要保密，不要提交。
- 如果 checker 会打开可见浏览器，Mac 需要处于已登录状态。确认流程稳定后，可以考虑设置
  `SKI_HEADLESS=true` 做无人值守运行。
