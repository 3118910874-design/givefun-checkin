// Probe helper: fetch URLs with a mobile UA and dump interesting bits.
const MOBILE_UA =
  'Mozilla/5.0 (Linux; Android 13; SM-S9180 Build/TP1A.220624.014) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36';

const targets = process.argv.slice(2);
if (!targets.length) {
  console.log('usage: node probe.mjs <url> [url...]');
  process.exit(1);
}

for (const url of targets) {
  try {
    const res = await fetch(url, {
      redirect: 'follow',
      headers: {
        'User-Agent': MOBILE_UA,
        Accept: '*/*',
        'Accept-Language': 'zh-CN,zh;q=0.9',
      },
    });
    const text = await res.text();
    console.log(`===== ${url}`);
    console.log(`status=${res.status} final=${res.url} type=${res.headers.get('content-type')} len=${text.length}`);
    const found = new Set();
    for (const m of text.matchAll(/["'`(]((?:https?:\/\/|\/\/|\/)[A-Za-z0-9_\-./?=&%:]{2,120})["'`)]/g)) {
      const v = m[1];
      if (/\.(png|jpe?g|webp|gif|css|svg|ico|woff2?|ttf)(\?|$)/i.test(v)) continue;
      found.add(v);
    }
    console.log('--- urls ---');
    console.log([...found].slice(0, 120).join('\n'));
    if (/<html/i.test(text)) {
      const js = [...text.matchAll(/<script[^>]+src=["']([^"']+)["']/gi)].map((m) => m[1]);
      console.log('--- scripts ---');
      console.log(js.join('\n'));
    } else {
      console.log('--- body head ---');
      console.log(text.slice(0, 3000));
    }
  } catch (e) {
    console.log(`===== ${url}\nERROR ${e.message}`);
  }
}
