const BASE = 'https://api.geifun.com.cn/';
const H = { Accept: '*/*', 'User-Agent': 'okhttp/4.9.0' };

async function req(method, path, body, extra = {}) {
  const res = await fetch(BASE + path, {
    method,
    headers: { ...H, ...(body ? { 'Content-Type': 'application/json; charset=utf-8' } : {}), ...extra },
    body: body ? JSON.stringify(body) : undefined,
  });
  const t = await res.text();
  console.log(`${method} ${path} -> ${res.status}\n  ${t.slice(0, 600)}\n`);
}

// is there a version prefix?
await req('POST', 'jifeng/game/category/list', {});
await req('POST', 'api/jifeng/game/category/list', {});
await req('POST', 'v1/jifeng/game/category/list', {});

// what does the app send for app headers?
await req('GET', 'jifeng/videoads/get/progress', null, { 'App-Id': '1', 'App-Ver': '1.0.0', 'x-device-id': 'abc', 'accept-time': String(Date.now()) });
await req('POST', 'jifeng/videoads/report/progress', { watch_ad_key: 'test' });
await req('POST', 'jifeng/videoads/report/progress', { watch_ad_key: 'test', progress: 100, type: 1, ad_id: 'x' });
await req('GET', 'jifeng/videoads/history/list');
await req('GET', 'jifeng/device/getban');
await req('POST', 'jifeng/user/login', { phoneNumber: '13800000000' });
await req('POST', 'jifeng/sms/sendcode', { phoneNumber: '13800000000' });
await req('POST', 'jifeng/user/verify', { phoneNumber: '13800000000', code: '123456' });
await req('POST', 'jifeng/token/refresh', {});
