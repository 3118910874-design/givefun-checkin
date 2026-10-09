const BASE = 'https://api.geifun.com.cn/';
const PATHS = [
  'jifeng/sms/sendcode', 'jifeng/user/login', 'jifeng/user/register', 'jifeng/user/verify',
  'jifeng/user/checkinfo', 'jifeng/user/phonestatus', 'jifeng/user/getrealphone',
  'jifeng/user/heartbeat', 'jifeng/token/refresh', 'jifeng/device/info', 'jifeng/device/token',
  'jifeng/device/ctl', 'jifeng/device/getban', 'jifeng/getuserverify',
  'jifeng/videoads/get/progress', 'jifeng/videoads/report/progress', 'jifeng/videoads/history/list',
  'jifeng/vip/consumelog', 'jifeng/vip/givebyact', 'jifeng/vip/consume',
  'jifeng/user/get-coupon-list', 'jifeng/coupon/activity/issue', 'jifeng/user/speed/switch',
  'jifeng/user/anti-addic', 'jifeng/goods/pricelist', 'jifeng/pay/getpayinfo',
];

async function call(method, path, body, headers = {}) {
  const url = BASE + path;
  try {
    const res = await fetch(url, {
      method,
      headers: {
        'Content-Type': 'application/json; charset=utf-8',
        Accept: '*/*',
        'User-Agent': 'okhttp/4.9.0',
        ...headers,
      },
      body: method === 'GET' ? undefined : JSON.stringify(body ?? {}),
    });
    const text = await res.text();
    return `${res.status} ${text.slice(0, 300)}`;
  } catch (e) {
    return `ERR ${e.message}`;
  }
}

for (const p of PATHS) {
  const post = await call('POST', p, {});
  const get = await call('GET', p);
  console.log(`${p}\n  POST -> ${post}\n  GET  -> ${get}`);
}
