const BASE = 'https://api.geifun.com.cn/';
const H = { Accept: '*/*', 'User-Agent': 'okhttp/4.9.0' };

async function call(label, path, { query, body, method = 'POST', headers = {} } = {}) {
  let url = BASE + path;
  if (query) url += '?' + new URLSearchParams(query).toString();
  try {
    const res = await fetch(url, {
      method,
      headers: { ...H, ...(body ? { 'Content-Type': 'application/json; charset=utf-8' } : {}), ...headers },
      body: body ? JSON.stringify(body) : undefined,
    });
    const t = await res.text();
    console.log(`${label.padEnd(50)} -> ${res.status} ${t.slice(0, 150)}`);
  } catch (e) {
    console.log(`${label.padEnd(50)} -> ERR ${e.message}`);
  }
}

const P = '13800000000';
console.log('== query vs json binding, per endpoint ==');
const eps = [
  ['user/verify', { phoneNumber: P, code: '000000' }],
  ['getuserverify', { phoneNumber: P }],
  ['user/heartbeat', { operateClient: 'android' }],
  ['user/anti-addic', { phoneNumber: P }],
  ['user/deleteuser', { phoneNumber: P }],
  ['user/modifypwd', { phoneNumber: P }],
  ['token/refresh', {}],
  ['device/token', {}],
  ['vip/givebyact', {}],
  ['user/get-coupon-list', {}],
  ['coupon/activity/issue', {}],
  ['user/speed/switch', { switch: '1' }],
  ['pay/getpayinfo', { goodsId: '1' }],
];
for (const [path, params] of eps) {
  await call(`${path} [query]`, `jifeng/${path}`, { query: params });
  await call(`${path} [json] `, `jifeng/${path}`, { body: params });
}

console.log('\n== method check for videoads ==');
await call('get/progress GET query', 'jifeng/videoads/get/progress', { method: 'GET', query: {} });
await call('get/progress GET query+t', 'jifeng/videoads/get/progress', { method: 'GET', query: { t: Date.now() } });
await call('history/list GET query', 'jifeng/videoads/history/list', { method: 'GET', query: {} });
await call('report/progress query', 'jifeng/videoads/report/progress', { query: { watch_ad_key: 'k1234567890' } });
