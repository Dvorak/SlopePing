# 架构说明

语言：[English](architecture.en.md) | 中文 | [Deutsch](architecture.de.md)

本文说明项目实现细节。日常使用请看 [README.zh-CN.md](../README.zh-CN.md)。

SlopePing 聚焦 Neuss Skihalle 教练在 Allrounder 教练门户里的排班查看和课程提醒流程。

## 模块概览

- `run_checker.py`
  入口文件。把 `src/` 加入 `sys.path`，然后调用
  `ski_checker.checker.run()`。
- `src/ski_checker/config.py`
  读取 `.env`，生成类型化配置。
- `src/ski_checker/browser.py`
  负责 Playwright 启动、登录、页面跳转、新页面切换和截图。
- `src/ski_checker/parser.py`
  找到排班表，把表格行转换成课程记录。
- `src/ski_checker/state.py`
  定义课程记录，读写 `state.json`，并对比本次和上次课程。
- `src/ski_checker/notify.py`
  通过 ntfy 发送通知，并保留 console fallback。

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

如果 `table#TAB` 不可见，会尝试找 `Übersicht` 附近的表格，再 fallback 到按表头扫描所有表格。

## 变化检测

每条课程的稳定 key 来自：

```text
Tag + Von + Bis + Raum/Ort + Trainingsbezeichnung
```

如果这个 key 不存在于 `state.json`，就是新课程。

如果 key 已存在，但完整记录变化了，例如 `Bestätigung` 变了，就是状态变化。

正常模式只通知新课程。测试阶段可以设置：

```dotenv
NOTIFY_ALWAYS_SEND_REPORT=true
```

这样每次成功运行都会发送当前课程报告。

## ntfy 通知

程序会 POST 纯文本到：

```text
{NTFY_SERVER}/{NTFY_TOPIC}
```

通知内容包含：

- 测试报告模式下的当前全部课程
- 待确认的新课程
- `Tag`, `Von`, `Bis`, `Raum/Ort`, `Trainingsbezeichnung`, `Bestätigung`

如果 ntfy 配置缺失或发送失败，程序会把同样内容打印到 console，并继续运行。

## 运行时文件

- `.env`
  本地密钥和用户配置。Git 忽略。
- `state.json`
  上一次成功解析的课程状态。Git 忽略。
- `screenshots/`
  成功和失败截图。Git 忽略。

## 安全说明

- 不要提交 `.env`。
- `NTFY_TOPIC` 要设置得长且私密。
- 公共 `ntfy.sh` 默认不会给 topic 加密码保护。
- 程序会打印运行步骤，但不会打印密码。
