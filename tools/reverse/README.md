# 逆向脚本（可复现）

这些脚本记录了本项目摸清疾风加速器接口协议的完整过程，
结论汇总在 [`../../docs/protocol.md`](../../docs/protocol.md)。

## 步骤

### 1. 拿到官方 APK

官网首页 HTML 里直接有安卓包地址：

```bash
# 从首页提取下载链接
node probe_get.mjs https://www.givefun.cn/
# → https://cdn.geifun.com.cn/jifeng/apk/com.gameaccel.rapid-<ver>.apk
```

### 2. 从 DEX 里提取接口路径与字符串

```bash
python dex_urls.py        <apk>            # 提取所有 URL 与 /xx/yy 形态路径
python dex_strings.py     <apk>            # 导出全部可打印字符串到 strings.txt
python dex_string_pool.py <apk>            # 正确解析 DEX string_ids，导出自身字符串池
```

`dex_urls.py` 会打印出 `jifeng/videoads/get/progress` 等 41 个业务路径，
以及网关 `https://api.geifun.com.cn/`。

### 3. 对线上网关做参数探测

按依赖顺序执行（前两个不需要账号）：

```bash
node probe_endpoint_map.mjs      # 逐接口试 POST/GET，从报错反推必填参数
node probe_param_binding.mjs     # 判定参数该放 query 还是 JSON body
node probe_login.mjs             # 登录链路的字段名（veriStr / verifyCode）
node probe_sendcode.mjs          # 验证码接口的 type 参数
node probe_query.mjs             # 验证 query 形态后各接口的真实返回
node probe_endpoints.mjs         # 综合回归
```

> ⚠️ `probe_sendcode.mjs` 会真的发短信。**请把里面的手机号换成占位号码**，
> 否则会对真实用户造成骚扰。

## 关键发现

| 发现 | 证据 |
|------|------|
| 参数读 query，不读 JSON body | 同一接口 body 传参报 `field "x" is not set`，query 传参进入下一步校验 |
| 登录验证码字段叫 `veriStr` | `?phoneNumber=&veriStr=000000` → `veriStr err`（格式合法、值错误） |
| 注册验证码字段叫 `verifyCode` | `?phoneNumber=` → `field "verifyCode" is not set` |
| 未登录的只读接口返回 200 + `code:3` | `get/progress` → `msg:用户信息错误`，需在客户端规范化成 401 语义 |
| 路径无 `/api` 前缀 | `api/jifeng/...` → 404，`jifeng/...` → 200 |
