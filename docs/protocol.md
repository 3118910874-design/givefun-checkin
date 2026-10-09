# 接口协议纪要

本文档记录对 **疾风加速器**（givefun.cn / `com.gameaccel.rapid`）服务端接口的逆向结果。
所有标注「✅ 实测」的结论都由本项目对线上网关的真实请求验证过；
标注「⚠️ 待实测」的部分需要真实账号才能闭环，代码里已做兼容与降级处理。

* 网关：`https://api.geifun.com.cn/`（Go 服务，证书正常）
* 客户端版本：`com.gameaccel.rapid` v1.2.2.0030（APK 取自官网 CDN）
* 逆向手段：官网下载 APK → 解包提取 `classes*.dex` 字符串与接口路径 → 对线上网关做参数探测

---

## 1. 通用约定

### 1.1 路径

```
https://api.geifun.com.cn/jifeng/<module>/<action>
```

注意：**没有** 前导斜杠，也 **没有** `/api` 或 `/v1` 前缀（加前缀会 404）。

### 1.2 响应信封 ✅ 实测

```json
{"code": 1, "msg": "success", "data": { ... }}
```

| code | 含义 |
|------|------|
| `1`  | 成功 |
| `3`  | 参数或业务错误，原因在 `msg` 中（如 `field "phoneNumber" is not set`） |
| `401`（HTTP 状态码） | 未登录 / 令牌失效，响应体为空 |

### 1.3 参数位置：查询字符串 ✅ 实测

这是最容易踩坑的一点：

> **服务端主要从 query string 读取参数，不解析 JSON 请求体。**

示例（同为登录接口）：

```bash
# ❌ 放进 JSON body → field "phoneNumber" is not set
curl -X POST 'https://api.geifun.com.cn/jifeng/user/login' \
     -H 'Content-Type: application/json' \
     -d '{"phoneNumber":"13800000000","veriStr":"000000"}'

# ✅ 放进 query string → 进入下一步校验
curl -X POST 'https://api.geifun.com.cn/jifeng/user/login?phoneNumber=13800000000&veriStr=000000'
```

只有 `user/heartbeat` 等少数接口两种都认，统一用 query 最稳妥。

### 1.4 鉴权 ⚠️ 待实测

登录/注册成功后服务端下发令牌，随请求头回传。未登录访问受保护接口会得到 HTTP 401。
客户端同时会带设备类请求头（`x-device-id` 等）。

代码当前策略：同时注入 `Token` / `token` / `Authorization` / `accessToken` 四个同名值，
服务端只会识别其中一个，多带无副作用。若实测发现真实头名不同，
可用 `GIVEFUN_EXTRA_HEADERS` 覆盖，无需改代码。

---

## 2. 接口清单（节选）

从 `classes*.dex` 中提取到的全部 41 个业务路径中，与「登录 / 领取加速时长」相关的如下。

### 2.1 登录链路

| 接口 | 方法 | 实测行为 |
|------|------|----------|
| `jifeng/user/phonestatus` | POST | ✅ 免登录。`?phoneNumber=` → `{"isRegister":0,"isSetPwd":0}` |
| `jifeng/sms/sendcode` | POST | ✅ `?phoneNumber=&type=1` → `{"code":1}`；缺 `type` 报 `field "type" is not set` |
| `jifeng/user/login` | POST | ✅ `?phoneNumber=&veriStr=<短信验证码>`；验证码错误返回 `veriStr err` |
| `jifeng/user/register` | POST | ✅ `?phoneNumber=&verifyCode=<短信验证码>`（缺则 `field "verifyCode" is not set`） |
| `jifeng/user/checkinfo` | POST | ✅ 受保护，未登录 401 |
| `jifeng/token/refresh` | POST | ✅ 受保护，未登录 401 |

> `veriStr` 就是用户收到的短信验证码本身。用 `000000` 探测时服务端返回 `veriStr err`
> 而不是「字段缺失」，说明字段格式已被接受、只差正确值。

注册流程还会要求 `jifeng/user/verify`（实名/年龄校验，返回 `is_real`/`isAdult`/`age`）。

### 2.2 领取加速时长链路

| 接口 | 方法 | 实测行为 |
|------|------|----------|
| `jifeng/device/getban` | GET | ✅ 免登录。`{"ttl":0,"banned_id":"","tips":""}` —— 可用于检测账号封禁 |
| `jifeng/videoads/get/progress` | GET | ✅ 未登录返回 `code:3 msg:用户信息错误`，`data` 结构：`watch_video_progress` / `new_watch_video_progress` / `popup_copy` / `speed_end_time` / `now_time` / `watch_num` |
| `jifeng/videoads/report/progress` | POST | ✅ 未登录返回 `code:3 msg:用户信息错误`；`data` 结构：`watch_ad_key_status` / `watch_num`。必填参数 `watch_ad_key` |
| `jifeng/videoads/history/list` | GET | ✅ 未登录返回 `code:3 msg:用户信息错误`，`data`：`speed_time_task` / `speed_end_time` |

调用形态示例：

```bash
# 查询今日任务进度
curl 'https://api.geifun.com.cn/jifeng/videoads/get/progress' -H 'Token: <TOKEN>'

# 上报/领取一条任务
curl -X POST 'https://api.geifun.com.cn/jifeng/videoads/report/progress?watch_ad_key=<KEY>' \
     -H 'Token: <TOKEN>'

# 复核加速时长余额
curl 'https://api.geifun.com.cn/jifeng/videoads/history/list' -H 'Token: <TOKEN>'
```

### 2.3 其他已探明接口

```
jifeng/user/heartbeat          operateClient 必填（保持在线）
jifeng/user/speed/switch       加速开关，需登录
jifeng/vip/consumelog          VIP 消耗记录，需登录
jifeng/vip/givebyact           活动赠送 VIP，需登录
jifeng/coupon/activity/issue   领券，需登录
jifeng/user/get-coupon-list    券列表，需登录
jifeng/pay/getpayinfo          支付信息
jifeng/pay/addvip/list         会员商品列表
jifeng/goods/pricelist         商品价格（免登录）
jifeng/game/category/list      游戏分类（免登录）
jifeng/device/info             ⚠️ 参数需 base64/AES，未配置时返回 400 illegal base64 data
jifeng/device/ctl              ⚠️ 同上
```

### 2.4 `device/info` 的加密参数 ⚠️ 待补全

客户端里有 `AES128Encode` / `AES128Decode`（`AES/CBC/PKCS7Padding`）与
`mAESKey` 等符号，`device/info`、`device/ctl` 的入参为 AES + Base64。
密钥/IV 未能在静态分析中确认（关键字符串被混淆，且部分逻辑在原生库中）。
`src/crypto.py` 已备好加解密与 `appsign` 计算函数，拿到密钥即可直接接上。

---

## 3. 尚未闭环的两点

诚实起见，以下两点需要**真实账号**才能最终确认，代码已按最合理假设实现并做了降级：

### 3.1 `watch_ad_key` 的来源

`report/progress` 必填 `watch_ad_key`。从数据结构看它应由服务端在
`get/progress`（或观看广告过程中的某个步骤）下发，`report/progress` 返回的
`watch_ad_key_status` 用于表示该凭据是否有效。

代码的处理方式：**递归扫描 `get/progress` 的整个响应体**，收集所有形如
`*_key` 的字符串字段并逐个尝试上报；若一个都没扫到，会明确记为
「今日暂无可领取任务」而不是假装成功。跑一次 `python checkin.py --debug`
即可看到真实的字段名，据此调整 `src/daily.py` 的 `KEY_FIELD_HINTS`。

### 3.2 奖励是否必须真实观看广告

如果服务端要求「广告平台的完成回调」才记发时长，那么纯 HTTP 调用无法领取，
本项目也不会伪造广告回调（那属于欺骗广告主，已超出合理范围）。

**验证方法**：用 `tools/capture.py` 抓一次官方 App 的完整流程，
对比 `report/progress` 请求的入参与返回，即可判定。

---

## 4. 复现逆向过程

```bash
# 1) 下载官网 APK（链接在首页 HTML 中）
#    https://cdn.geifun.com.cn/jifeng/apk/com.gameaccel.rapid-<ver>.apk

# 2) 提取接口路径与字符串
python - <<'PY'
import re, zipfile
z = zipfile.ZipFile('givefun.apk')
for n in [x for x in z.namelist() if x.endswith('.dex')]:
    data = z.read(n)
    for m in re.finditer(rb'jifeng/[a-z0-9/]+', data):
        print(n, m.group(0).decode())
PY

# 3) 抓包校准（需要一台安卓设备 / 模拟器）
pip install mitmproxy
mitmdump -s tools/capture.py
```

---

## 5. 变更风险

* 网关为国内 Go 服务，接口路径带 `jifeng` 前缀（历史品牌名），未来可能调整；
* 参数名（如 `veriStr`、`watch_ad_key`）随客户端版本可能变化；
* 若某天接口集体返回 404/405，请按本文第 4 节重新提取一次 APK 对照更新。
