import struct, zipfile, io, re, collections, sys

APK = r'C:\Users\hcy\Documents\deepseek-harness\default-workspace\_probe\givefun.apk'
z = zipfile.ZipFile(APK)

def uleb128(buf, off):
    result = 0
    shift = 0
    while True:
        b = buf[off]
        off += 1
        result |= (b & 0x7F) << shift
        if not (b & 0x80):
            break
        shift += 7
    return result, off

def parse_strings(data):
    buf = io.BytesIO(data)
    # header: magic(8) checksum(4) sig(20) file_size(4) header_size(4) endian(4) ...
    buf.seek(0)
    hdr = buf.read(0x70)
    string_ids_size, string_ids_off = struct.unpack_from('<II', hdr, 0x38)
    out = []
    for i in range(string_ids_size):
        off = struct.unpack_from('<I', data, string_ids_off + i * 4)[0]
        n, p = uleb128(data, off)
        raw = data[p:p + n]
        try:
            s = raw.decode('utf-8')
        except UnicodeDecodeError:
            s = raw.decode('utf-8', 'replace')
        out.append(s)
    return out

SKIP_SUB = ('bytedance', 'bykv', 'toutiao', 'pglstatp', 'pangle', 'snssdk', 'volces',
            'gemlink', 'chinatelecom', 'csjplatform', 'ttmplayer', 'alipay', 'taobao',
            'umeng', 'bugly', 'kxqp', 'zmvmp', 'pglbizssdk', 'gdt', 'tencent', 'huawei',
            'hihonor', 'xiaomi', 'oppo', 'vivo', 'soboten', 'ourplay', 'multiopen',
            'zztfly', 'gamestream', 'iqiyi', 'baidu', 'oceanengine', 'bytesfield',
            'androidx', 'android.', 'java.', 'kotlin', 'okhttp', 'retrofit', 'glide',
            'exoplayer', 'gson', 'fastjson', 'org.json', 'apache', 'json', 'w3.org',
            'schemas', 'slf4j', 'guava', 'reactivex', 'rxjava', 'squareup', 'bumptech',
            'libcore', 'dalvik', 'com.google', 'firebase', 'gms', 'amap', 'ta.utdid',
            'utdid', 'umid', 'miui', 'honor', 'meizu', 'push', 'sina', 'weibo', 'qq.com',
            'wechat', 'unionpay', 'alipay', 'cmb', 'wangyin')

allstrings = []
for name in [n for n in z.namelist() if n.endswith('.dex')]:
    allstrings.extend(parse_strings(z.read(name)))

print('total strings:', len(allstrings), file=sys.stderr)

def is_own(s):
    low = s.lower()
    return not any(k in low for k in SKIP_SUB)

# 1. print strings that look like keys/params/headers (short, snake/camel, no spaces)
INTEREST = re.compile(r'^(?:[a-z][A-Za-z0-9_\-]{2,30}|[A-Z][A-Za-z0-9_]{3,30}|[a-z_]+(?:/[a-z0-9_\-]+)+)$')
pool = sorted({s for s in allstrings if is_own(s) and INTEREST.match(s)})
print(f'=== candidate identifiers: {len(pool)} ===')
with open(r'C:\Users\hcy\Documents\deepseek-harness\default-workspace\_probe\own_strings.txt', 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(sorted({s for s in allstrings if is_own(s)})))
print('written own_strings.txt')
