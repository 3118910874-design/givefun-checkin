const BASE = 'https://api.geifun.com.cn/';
const H = { Accept: '*/*', 'User-Agent': 'okhttp/4.9.0' };

async function show(label, path, { method = 'POST', body, query } = {}) {
  let url = BASE + path;
  if (query) url += '?' + new URLSearchParams(query).toString();
  try {
    const res = await fetch(url, {
      method,
      headers: { ...H, ...(body ? { 'Content-Type': 'application/json; charset=utf-8' } : {}) },
      body: body ? JSON.stringify(body) : undefined,
    });
    const t = await res.text();
    console.log(`${label.padEnd(46)} -> ${res.status} ${t.slice(0, 160)}`);
  } catch (e) {
    console.log(`${label.padEnd(46)} -> ERR ${e.message}`);
  }
}

const P = '13800000000';
console.log('--- sendcode: body field variants ---');
await show('body {phoneNumber}', 'jifeng/sms/sendcode', { body: { phoneNumber: P } });
await show('body {phone}', 'jifeng/sms/sendcode', { body: { phone: P } });
await show('body {mobile}', 'jifeng/sms/sendcode', { body: { mobile: P } });
await show('body {phoneNumber,mobile}', 'jifeng/sms/sendcode', { body: { phoneNumber: P, mobile: P } });
await show('body {PhoneNumber}', 'jifeng/sms/sendcode', { body: { PhoneNumber: P } });
await show('body {phone_number}', 'jifeng/sms/sendcode', { body: { phone_number: P } });
await show('query ?phoneNumber=', 'jifeng/sms/sendcode', { body: {}, query: { phoneNumber: P } });
await show('body {phoneNumber} form-encoded', 'jifeng/sms/sendcode', { body: { phoneNumber: P } });

console.log('\n--- login: body field variants ---');
await show('login {phoneNumber}', 'jifeng/user/login', { body: { phoneNumber: P } });
await show('login {phoneNumber,code}', 'jifeng/user/login', { body: { phoneNumber: P, code: '000000' } });
await show('login {phone,code}', 'jifeng/user/login', { body: { phone: P, code: '000000' } });
await show('login {mobile,code}', 'jifeng/user/login', { body: { mobile: P, code: '000000' } });
await show('login {phoneNumber,password}', 'jifeng/user/login', { body: { phoneNumber: P, password: 'x' } });

console.log('\n--- verify / phonestatus ---');
await show('verify {phoneNumber,code}', 'jifeng/user/verify', { body: { phoneNumber: P, code: '000000' } });
await show('verify {phoneNumber,verifyCode}', 'jifeng/user/verify', { body: { phoneNumber: P, verifyCode: '000000' } });
await show('phonestatus {phoneNumber}', 'jifeng/user/phonestatus', { body: { phoneNumber: P } });
