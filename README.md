# 疾风加速器每日自动领取加速时长

用 GitHub Actions 每天自动帮你完成 **疾风加速器（givefun.cn）** 的「看视频领加速时长」任务，
结果通过微信 / 钉钉 / 飞书 / Telegram / Bark 等渠道推送到手机。

参照项目：[develop202/kgcheckin](https://github.com/develop202/kgcheckin)（酷狗概念 VIP 自动签到）的组织方式，
本项目同样采用「**先手动登录拿令牌 → 令牌存 Secret → 每天定时跑**」的两段式设计。

> **免责声明**
> 1. 本项目仅供学习与交流，接口协议通过官网公开下载的 APK 分析得出，未使用任何非公开手段。
> 2. 使用自动化脚本可能违反服务商用户协议，存在账号被限制的风险，**请自行评估并承担后果**。
> 3. 脚本不会伪造广告回调，也不会绕过付费，只做「调用官方 App 本来就会调用的接口」。
> 4. 请勿将本项目用于商业用途或倒卖。

---

## 目录

- [它能做什么](#它能做什么)
- [快速开始（5 分钟）](#快速开始5-分钟)
- [配置项一览](#配置项一览)
- [推送通知渠道](#推送通知渠道)
- [本地运行](#本地运行)
- [项目结构](#项目结构)
- [接口协议与已知边界](#接口协议与已知边界)
- [常见问题](#常见问题)
- [致谢](#致谢)

---

## 它能做什么

| 能力 | 状态 |
|------|------|
| 短信验证码登录、自动把令牌写回仓库 Secrets | ✅ 已实现 |
| 每天定时运行（北京时间 01:10），手动触发亦可 | ✅ 已实现 |
| 查询今日剩余可领取次数、加速时长到期时间 | ✅ 已实现 |
| 扫描并逐条上报可领取的任务凭据 | ✅ 已实现（依赖服务端下发凭据，见下文说明） |
| 账号封禁状态检测 | ✅ 已实现 |
| 多渠道结果推送 | ✅ 已实现（7 个渠道） |
| 仓库保活，避免 60 天无活动导致定时任务被停用 | ✅ 已实现 |
| 抓包校准工具（mitmproxy） | ✅ 已实现 |

### ⚠️ 使用前请先读这一段

「看视频领加速时长」的领取凭据 `watch_ad_key` 由服务端下发。本项目会**自动扫描**
`get/progress` 返回里的凭据字段并逐条上报；如果服务端要求「广告平台的完成回调」才计发时长，
那么纯接口调用无法领取 —— 这种情况脚本会如实报告「今日暂无可领取任务」，**不会伪造成功**。

请先按 [快速开始](#快速开始5-分钟) 跑一次 `dry-run`，确认输出里的任务进度符合预期，
再开启每日定时。

---

## 快速开始（5 分钟）

### 1. Fork 本仓库

点右上角 **Fork**，得到你自己的副本（例如 `https://github.com/<你的用户名>/givefun-checkin`）。

### 2. 创建访问令牌 PAT（用于自动写回 Secret）

打开 <https://github.com/settings/personal-access-tokens/new>：

| 配置项 | 值 |
|--------|-----|
| Token name | 随意，如 `givefun-checkin` |
| Expiration | 建议自定义有效期（如 1 年） |
| Repository access | 只选你刚 Fork 的这个仓库 |
| Repository permissions → **Secrets** | **Read and write** |
| Repository permissions → **Metadata** | Read（默认已选） |

生成后复制，去到你的仓库：**Settings → Secrets and variables → Actions → New repository secret**，
名称填 `GH_PAT`，值粘贴刚才的令牌。

### 3. 登录拿令牌

1. 进入 **Actions** 标签页 → 左侧选 **疾风登录（获取令牌）** → **Run workflow**
2. `mode` 选 **send**，`phone` 填你的手机号 → 运行
3. 等手机收到短信验证码（一般 10 秒内）
4. 再次 **Run workflow**，`mode` 选 **login**，`code` 填刚收到的验证码 → 运行

成功后日志会显示：

```
[GitHub] ✅ GIVEFUN_TOKEN -> 201
[3/3] 请把下面的值填入仓库 Settings → Secrets and variables → Actions：
  GIVEFUN_TOKEN = xxxxxxxx
```

令牌已自动写入仓库 Secret，**不需要手动复制**。

> 如果手里已经有可用令牌（例如从官方 App 抓包得到），可以跳过这一步，
> 直接手动添加 `GIVEFUN_TOKEN` Secret 即可。
>
> 未注册的手机号：第一次请把 `mode` 的 `send` 换成注册流程
> （本地运行 `python login_helper.py --phone <号码> --send-only --register`），
> 或在官方 App 注册后再用本流程登录。

### 4. 试跑一次

**Actions → 疾风每日领取 → Run workflow**，把 `dry_run` 勾上 → 运行。

查看日志确认：

```
[OK] 账号状态: 正常
[OK] 登录校验: 令牌有效
[OK] 读取任务进度: 今日可看 3 次；加速时长到期 2025-06-01 12:00:00
```

### 5. 完成

默认每天 **北京时间 01:10** 自动运行（在 `.github/workflows/checkin.yml` 里改 cron 即可）。
仓库保活工作流每周一自动提交一次时间戳，防止定时任务被 GitHub 停用。

---

## 配置项一览

全部通过环境变量 / Secrets 传入，**只有 `GIVEFUN_TOKEN` 是必需的**。

### 账号与鉴权

| 变量 | 必需 | 说明 |
|------|:---:|------|
| `GIVEFUN_TOKEN` | ✅ | 登录令牌，等价于账号密码 |
| `GIVEFUN_DEVICE_ID` | | 设备号，登录响应里有就一起配上 |
| `GIVEFUN_USER_ID` | | 用户 ID，同上 |
| `GIVEFUN_PHONE` | | 手机号，仅用于日志脱敏展示与注册状态查询 |
| `GIVEFUN_EXTRA_HEADERS` | | 额外请求头，格式 `K1:V1;K2:V2`，协议微调时的应急逃生口 |
| `GH_PAT` | | 仅登录工作流需要，用于把令牌写回 Secrets |

### 行为开关

| 变量 | 默认 | 说明 |
|------|------|------|
| `GIVEFUN_WARMUP` | `1` | 领取前先发一次心跳，更接近真实客户端 |
| `GIVEFUN_MAX_CLAIM` | `0` | 单次最多领取几个任务，`0` 表示不限 |
| `GIVEFUN_RETRIES` | `2` | 网络错误重试次数 |
| `GIVEFUN_TIMEOUT` | `20` | 单请求超时（秒） |
| `GIVEFUN_DEBUG` | `0` | 打印请求 / 响应明细 |

---

## 推送通知渠道

在仓库 **Settings → Secrets and variables → Actions** 里按需添加，
**配置了几个就会同时推送到几个**，一个都不配就只在日志里输出。

| 渠道 | Secret | 备注 |
|------|--------|------|
| PushPlus | `PUSHPLUS_TOKEN` | 可选 `PUSHPLUS_TOPIC` 指定群组 |
| Server 酱 | `SERVERCHAN_SENDKEY` | SendKey，兼容 `sctp` 新版 |
| 企业微信机器人 | `WECOM_BOT_KEY` | webhook URL 里的 `key=` 后面那串 |
| 钉钉机器人 | `DINGTALK_BOT_KEY` | 可选 `DINGTALK_SECRET` 开启加签 |
| 飞书机器人 | `FEISHU_BOT_KEY` | webhook 路径最后一段 |
| Bark（iOS） | `BARK_KEY` | 可填完整 URL，或仅填 key；可选 `BARK_GROUP` |
| Telegram | `TG_BOT_TOKEN` + `TG_CHAT_ID` | 两个都要配 |

推送内容示例：

```
执行日期：2025-05-20 01:12:33
账号：138****8888

结果：4/5 步成功

✅ 账号状态：正常
✅ 登录校验：令牌有效
✅ 读取任务进度：今日可看 3 次；加速时长到期 2025-06-01 12:00:00
✅ 领取任务：成功 1/1 个任务
✅ 复核余额：{"speed_time_end": 1748764800}

剩余加速时长：到期时间 2025-06-01 12:00:00

—— 由 GitHub Actions 自动执行
```

---

## 本地运行

需要 Python 3.9+，主流程**零第三方依赖**。

```bash
git clone https://github.com/<你的用户名>/givefun-checkin.git
cd givefun-checkin

# 接口连通性自检（不需要账号）
python tools/selftest.py

# 查看手机号注册状态
python login_helper.py --phone 13800000000 --status

# 发送验证码（type=1 登录 / type=2 注册）
python login_helper.py --phone 13800000000 --send-only

# 用验证码登录，并把令牌写入本地 state.json（已 gitignore）
python login_helper.py --phone 13800000000 --code 123456 --write-state

# 只查询不领取（推荐第一次这么跑）
GIVEFUN_TOKEN=<你的令牌> python checkin.py --dry-run

# 正式执行
GIVEFUN_TOKEN=<你的令牌> python checkin.py

# 带请求明细，便于校准协议
GIVEFUN_TOKEN=<你的令牌> python checkin.py --debug
```

### 抓包校准协议

如果 `--debug` 显示没扫到可领取凭据，用官方 App 抓一次完整流程来对比：

```bash
pip install mitmproxy
mitmdump -s tools/capture.py
# 手机 Wi-Fi 代理指向电脑:8080，安装 mitmproxy 证书，
# 在 App 里点一次「看视频领时长」，工具目录下就会生成 capture.jsonl
```

把 `capture.jsonl` 里 `report/progress` 的请求参数与响应贴到 Issue 里即可帮助完善。

---

## 项目结构

```
givefun-checkin/
├── checkin.py                  # 每日领取入口
├── login_helper.py             # 登录入口
├── requirements.txt            # 仅登录/抓包需要第三方依赖
├── src/
│   ├── config.py               # 环境变量配置 + 日志脱敏
│   ├── client.py               # 接口客户端（信封解析、鉴权、错误规范化）
│   ├── login.py                # 短信登录、注册、写回 GitHub Secrets
│   ├── daily.py                # 每日主流程（状态→进度→领取→复核→通知）
│   ├── notify.py               # 7 个推送渠道
│   └── crypto.py               # AES / MD5 签名工具（协议微调时备用）
├── tools/
│   ├── selftest.py             # 连通性自检
│   └── capture.py              # mitmproxy 抓包脚本
├── docs/protocol.md            # 接口协议纪要（含实测证据）
└── .github/workflows/
    ├── checkin.yml             # 每日领取（cron 17:10 UTC）
    ├── login.yml               # 短信登录并同步 Secrets
    └── keepalive.yml           # 仓库保活
```

---

## 接口协议与已知边界

完整纪要见 **[docs/protocol.md](docs/protocol.md)**，要点：

* 网关 `https://api.geifun.com.cn/`，路径形如 `jifeng/<module>/<action>`，**无 `/api` 前缀**；
* 响应统一信封 `{"code":1,"msg":"success","data":{...}}`，`code=3` 为业务错误，HTTP 401 为未登录；
* **参数放在 query string，服务端不解析 JSON body**（这是最大的坑）；
* 登录接口参数名是 `veriStr`（就是短信验证码），注册接口是 `verifyCode`；
* 「未登录」在只读接口里可能表现为 HTTP 200 + `code:3 msg:用户信息错误`，代码已规范化处理。

**两个需要真实账号才能最终闭环的点**（详见协议文档第 3 节）：

1. `watch_ad_key` 的确切来源 —— 现在用递归扫描 + 逐条尝试，扫不到会如实报告；
2. 奖励是否要求广告平台回调 —— 若要求，则纯接口方案无法领取，本项目不会伪造回调。

---

## 常见问题

**Q：日志报 `未配置 GIVEFUN_TOKEN`？**
A：还没登录。先跑「疾风登录（获取令牌）」工作流，或手动添加 `GIVEFUN_TOKEN` Secret。

**Q：日志报 `令牌有效 → 401`？**
A：令牌过期了，重新跑一次登录工作流即可。服务端令牌有效期由官方决定，一般数月。

**Q：Actions 里定时任务不触发？**
A：GitHub 会在仓库 60 天无提交活动后停用 schedule。本仓库的「仓库保活」工作流每周一自动提交一次；
若你改过它，请确保仍处于启用状态。

**Q：登录工作流报 `获取公钥失败：401`？**
A：`GH_PAT` 没配或权限不足。需要「Secrets: Read and write」权限，且 Repository access 包含本仓库。

**Q：不想用 GitHub Actions，只想本地定时？**
A：用系统计划任务调用 `python checkin.py`，令牌通过环境变量传入即可。

**Q：接口突然全部 404 / 405？**
A：站点可能改了协议。按 `docs/protocol.md` 第 4 节重新提取一次 APK 对照更新。

---

## 致谢

* [develop202/kgcheckin](https://github.com/develop202/kgcheckin) —— 本项目的工作流组织、通知渠道设计与其一脉相承；
* GitHub Actions 提供的免费定时执行能力。

## 许可

[MIT](LICENSE)
