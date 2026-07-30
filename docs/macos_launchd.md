# macOS launchd Setup

Language: English | 中文

SlopePing installs two user LaunchAgents:

- `com.slopeping`: runs the checker at 08:00, 13:00, and 20:00.
- `com.slopeping.webhook`: keeps the mobile Webhook service running.

The checked-in shell wrappers resolve runtime paths from `.env`. With the
default configuration, all logs are stored in `var/logs/`.

## English

### Install or update

Test the commands manually first:

```bash
cd /Users/zhang/SlopePing
source .venv/bin/activate
python run_checker.py
python scripts/webhook_server.py
```

Stop the manually started Webhook with `Ctrl+C`, then install both jobs:

```bash
./scripts/install_launchd.sh
```

The installer validates both plist files, replaces older loaded jobs, and
starts the Webhook service. Re-run the same command after changing the checkout
path, runtime directory, or wrapper scripts.

### Verify

```bash
launchctl print gui/$(id -u)/com.slopeping
launchctl print gui/$(id -u)/com.slopeping.webhook
curl http://127.0.0.1:8000/health
tail -f var/logs/checker.log
tail -f var/logs/webhook_server.log
```

The checker normally shows `state = not running` between scheduled runs. The
Webhook should show `state = running`.

### Uninstall

```bash
./scripts/uninstall_launchd.sh
```

This removes only the LaunchAgent plist files. It does not delete `.env` or
anything under `var/`.

### Notes

- `launchd` does not use the interactive shell environment. The wrappers use
  absolute project and virtual-environment paths.
- Use `SKI_HEADLESS=true` only after a successful visible browser test.
- For phone access, `WEBHOOK_HOST=0.0.0.0` is appropriate only on a trusted
  network or behind a secure tunnel.
- `var/logs/` is rotated by the runtime maintenance command before services
  start.

---

## 中文

### 安装或更新

先手动验证：

```bash
cd /Users/zhang/SlopePing
source .venv/bin/activate
python run_checker.py
python scripts/webhook_server.py
```

用 `Ctrl+C` 停止手动启动的 Webhook，然后安装两个任务：

```bash
./scripts/install_launchd.sh
```

安装脚本会校验 plist、卸载旧任务、重新加载并启动 Webhook。仓库路径、
`SLOPEPING_RUNTIME_DIR` 或包装脚本变化后，重新运行同一命令即可。

### 验证

```bash
launchctl print gui/$(id -u)/com.slopeping
launchctl print gui/$(id -u)/com.slopeping.webhook
curl http://127.0.0.1:8000/health
tail -f var/logs/checker.log
tail -f var/logs/webhook_server.log
```

checker 在计划时间之外通常显示 `state = not running`，这是正常的；Webhook 应显示
`state = running`。

### 卸载

```bash
./scripts/uninstall_launchd.sh
```

该命令只删除 LaunchAgent plist，不会删除 `.env` 或 `var/` 中的数据。

### 注意

- launchd 不使用交互式 shell 环境，包装脚本使用项目和虚拟环境的绝对路径。
- 先完成可见浏览器验证，再设置 `SKI_HEADLESS=true`。
- 只有在可信局域网或安全 tunnel 后面才使用 `WEBHOOK_HOST=0.0.0.0`。
- 服务启动前会对 `var/logs/` 执行日志轮转。
