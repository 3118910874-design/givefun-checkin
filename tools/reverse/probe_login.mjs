const BASE = 'https://api.geifun.com.cn/';
const H = { Accept: '*/*', 'User-Agent': 'okhttp/4.9.0', 'Content-Type': 'application/json; charset=utf-8' };

async function call(label, path, { query, body, method = 'POST', headers = {} } = {}) {
  let url = BASE + path;
  if (query) url += '?' + new URLSearchParams(query).toString();
  try {
    const res = await fetch(url, {
      method,
      headers: { ...H, ...headers },
      body: body ? JSON.stringify(body) : undefined,
    });
    const t = await res.text();
    console.log(`${label.padEnd(60)} -> ${res.status} ${t.slice(0, 170)}`);
  } catch (e) {
    console.log(`${label.padEnd(60)} -> ERR ${e.message}`);
  }
}

const P = '13800000000';

console.log('--- login: what is veriStr? ---');
await call('login ?phoneNumber&code', 'jifeng/user/login', { query: { phoneNumber: P, code: '000000' } });
await call('login ?phoneNumber&veriStr=000000', 'jifeng/user/login', { query: { phoneNumber: P, veriStr: '000000' } });
await call('login JSON {phoneNumber,veriStr}', 'jifeng/user/login', { body: { phoneNumber: P, veriStr: '000000' } });
await call('login JSON {phoneNumber,veriStr,mobile,code}',
  'jifeng/user/login', { body: { phoneNumber: P, veriStr: '000000', mobile: P, code: '000000' } });
await call('login ?phoneNumber JSON {veriStr}', 'jifeng/user/login',
  { query: { phoneNumber: P }, body: { veriStr: '000000' } });
await call('login ?phoneNumber&veriStr + JSON phoneNumber',
  'jifeng/user/login', { query: { phoneNumber: P, veriStr: '000000' }, body: { phoneNumber: P } });
await call('login ?phoneNumber&veriStr&code&password',
  'jifeng/user/login',
  { query: { phoneNumber: P, veriStr: '000000', code: '000000', password: 'x' } });
await call('login ?phoneNumber&veriStr&type=1',
  'jifeng/user/login', { query: { phoneNumber: P, veriStr: '000000', type: '1' } });

console.log('\n--- register ---');
await call('register ?phoneNumber&veriStr', 'jifeng/user/register',
  { query: { phoneNumber: P, veriStr: '000000' } });
await call('register ?phoneNumber&code', 'jifeng/user/register',
  { query: { phoneNumber: P, code: '000000' } });

console.log('\n--- claim endpoint with fake token (query params) ---');
await call('report/progress ?watch_ad_key (fake token)', 'jifeng/videoads/report/progress',
  { query: { watch_ad_key: 'test-key-12345678' }, headers: { Token: 'invalid-token' } });
await call('report/progress ?watch_ad_key&progress&type', 'jifeng/videoads/report/progress',
  { query: { watch_ad_key: 'test-key-12345678', progress: '100', type: '1' }, headers: { Token: 'invalid-token' } });
await call('get/progress (fake token)', 'jifeng/videoads/get/progress',
  { query: {}, headers: { Token: 'invalid-token' } });
