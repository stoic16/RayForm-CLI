---
name: run-rayform-cli
description: Run, launch, start, smoke-test, or verify the RayForm / 睿锋平台 CLI (cli-anything-platform-service). Use when asked to run the RayForm CLI, drive the platform-service CLI, smoke-test its commands, or verify token auto-relogin works offline without a live backend.
---

# run-rayform-cli

睿锋智链汽车配件供应链平台 CLI（`cli-anything-platform-service`）的运行与离线验证技能。
该 CLI 基于 Click，调用 Spring Boot 后台 REST API；正常业务命令需要可达的后台，
但本技能提供的 **driver 可在无后台的环境下离线验证 CLI 与核心鉴权逻辑**。

主驱动：`.claude/skills/run-rayform-cli/driver.py`（路径相对仓库根）。

## Prerequisites

仓库根执行一次，注册 `cli-anything-platform-service` 入口点：

```bash
pip install -e .
```

Python ≥ 3.10；依赖 `click` / `prompt_toolkit` / `requests`（`pip install -e .` 自动装）。

## Run (agent path) — driver

在仓库根运行，三种模式，退出码 0 = 全部通过：

```bash
# 全部跑一遍（smoke + auth-test + session-test）
python .claude/skills/run-rayform-cli/driver.py --all

# 只跑某一项
python .claude/skills/run-rayform-cli/driver.py --smoke
python .claude/skills/run-rayform-cli/driver.py --auth-test
python .claude/skills/run-rayform-cli/driver.py --session-test
```

各模式做什么：

- `--smoke`：跑 `cli-anything-platform-service --help`、各命令组 `<group> --help`、
  `config show`（含 `--json`），逐条断言退出码 0。验证 CLI 已正确安装、命令树完整。
- `--auth-test`：**离线**直接调用 `PlatformServiceBackend`，用打桩 session 模拟 token 过期，
  断言两种过期都自动重新登录并重试成功——① 传输层 `HTTP 401`，
  ② 业务信封层 `HTTP 200 + body {"code":401}`（网关常见返回方式）；并验证无凭据时不误触发重登。
- `--session-test`：临时 HOME 下 `Session` 配置往返，验证 token/mobile/password 持久化且文件权限 0600。

`--all` 实测输出（本环境跑通）：

```
== 汇总 ==
  smoke          PASS
  auth-test      PASS
  session-test   PASS
```

## Run (human path)

无 driver 时的人类用法（需先 `config login` 或 `config set` 配好后台才能跑业务命令）：

```bash
# 单命令模式（--json 适合 Agent 消费）
cli-anything-platform-service --json config show

# 交互式 REPL（无参数进入；输入 help / exit）
cli-anything-platform-service
```

登录并启用自动重登（保存 token + 账号密码到 ~/.cli-anything-platform-service/config.json，0600）：

```bash
cli-anything-platform-service config set --env test --base-url <BASE_URL>
cli-anything-platform-service config login --mobile <MOBILE>   # 交互式输入密码
```

## Gotchas

- **无真实后台时业务命令会报连接失败**（`无法连接到平台服务…`）——这是预期的。
  离线验证一律走 driver 的 `--auth-test` / `--session-test`，不要去跑 `product list` 等。
- **token 过期自动重登覆盖两层**：传输层 HTTP 401 与业务信封层 `HTTP 200 + code:401`
  都会触发（见 `cli_anything/platform_service/utils/backend.py` 的 `_AUTH_FAIL_CODES`
  与 `_relogin_and_retry`）。若后台用了其它"未认证"码，把它加入 `_AUTH_FAIL_CODES` 即可。
- **`config login` 必须先有 base-url**：未设 base-url 时直接报错退出，先 `config set --base-url`。
- **正式环境有 SNI 绕过逻辑**（`backend.py` 顶部 `_HOST_IP_MAP` 与 `__init__` 的直连探测），
  仅对 `rfscm.com` / 两个固定 IP 生效；driver 用 `fake.local` 主机名，不触发该分支。

## Troubleshooting

| 症状 | 原因 / 解决 |
|------|------|
| `未找到 cli-anything-platform-service` | 没装入口点 → 仓库根 `pip install -e .` |
| driver `auth-test` 报 `GET 调用次数超出脚本预期` | backend 重试逻辑改动后调用次数变化；对照 `_request` 检查重试路径 |
| `config show` 显示"未配置" | 正常，未登录时的默认状态，不影响 smoke 退出码 |
