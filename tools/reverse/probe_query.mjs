const BASE = 'https://api.geifun.com.cn/';
const H = { Accept: '*/*', 'User-Agent': 'okhttp/4.9.0' };

async function q(label, path, params, method = 'POST') {
  const url = BASE + path + '?' + new URLSearchParams(params).toString();
  try {
    const res = await fetch(url, { method, headers: H });
    const t = await res.text();
    console.log(`${label.padEnd(52)} -> ${res.status} ${t.slice(0, 170)}`);
  } catch (e) {
    console.log(`${label.padEnd(52)} -> ERR ${e.message}`);
  }
}

const P = '13800000000';
await q('sendcode ?phoneNumber&type=1', 'jifeng/sms/sendcode', { phoneNumber: P, type: '1' });
await q('sendcode ?phoneNumber&type=2', 'jifeng/sms/sendcode', { phoneNumber: P, type: '2' });
await q('sendcode ?phoneNumber only', 'jifeng/sms/sendcode', { phoneNumber: P });
await q('login ?phoneNumber&code', 'jifeng/user/login', { phoneNumber: P, code: '000000' });
await q('login ?phoneNumber&password', 'jifeng/user/login', { phoneNumber: P, password: 'x' });
await q('phonestatus ?phoneNumber', 'jifeng/user/phonestatus', { phoneNumber: P });
await q('verify ?phoneNumber&code', 'jifeng/user/verify', { phoneNumber: P, code: '000000' });
await q('getuserverify ?phoneNumber', 'jifeng/getuserverify', { phoneNumber: P });
await q('getprog ?(none)', 'jifeng/videoads/get/progress', {});
await q('goods/pricelist ?goodsType=1', 'jifeng/goods/pricelist', { goodsType: '1' });
await q('report/progress ?watch_ad_key', 'jifeng/videoads/report/progress', { watch_ad_key: 'test-key' });
