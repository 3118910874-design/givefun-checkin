import re, zipfile, sys, collections

APK = r'C:\Users\hcy\Documents\deepseek-harness\default-workspace\_probe\givefun.apk'
z = zipfile.ZipFile(APK)

KEYWORDS = ['api', 'givefun', 'geifun', 'jifeng', 'sign', 'token', 'login', 'sms',
            'accel', 'reward', 'task', 'advert', 'video', 'duration', 'checkin',
            'check-in', 'signin', 'clock', 'user/', '/v1/', '/v2/', '/api/']

URL_RE = re.compile(rb'(?:https?://|wss?://)[A-Za-z0-9_\-.:/%?=&@#~+]{4,160}')
PATH_RE = re.compile(rb'/(?:api|v1|v2|user|acc|jf|open|client|app|h5|m)/[A-Za-z0-9_\-/{}]{2,80}')

targets = sys.argv[1:] or ['classes.dex', 'classes2.dex', 'classes3.dex', 'classes4.dex']
for name in targets:
    try:
        data = z.read(name)
    except KeyError:
        print('missing', name); continue
    print(f'########## {name} ({len(data)} bytes)')
    urls = collections.Counter(m.group(0).decode('utf-8', 'replace') for m in URL_RE.finditer(data))
    print('--- URLs ---')
    for u, c in urls.most_common(200):
        if any(x in u for x in ('google', 'facebook', 'gstatic', 'schemas.android', 'w3.org',
                                'apache.org', 'json-schema', 'github.com', 'qq.com', 'umeng',
                                'bugly', 'doubleclick', 'googlesyndication', 'android.com',
                                'example.com', 'opensource', 'sqlite', 'adobe', 'purl.org')):
            continue
        print(f'{c:5d}  {u}')
    print('--- paths ---')
    paths = collections.Counter(m.group(0).decode('utf-8', 'replace') for m in PATH_RE.finditer(data))
    for p, c in paths.most_common(120):
        print(f'{c:5d}  {p}')
