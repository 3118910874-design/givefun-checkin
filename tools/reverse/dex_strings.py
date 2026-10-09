import re, zipfile, sys

APK = r'C:\Users\hcy\Documents\deepseek-harness\default-workspace\_probe\givefun.apk'
OUT = r'C:\Users\hcy\Documents\deepseek-harness\default-workspace\_probe\strings.txt'
z = zipfile.ZipFile(APK)

# printable ASCII runs >= 4 (latin-1 decode so bytes survive)
RUN = re.compile(rb'[\x20-\x7e]{4,}')
# also UTF-8 CJK-ish runs are skipped here; handled by latin-1 runs

names = [n for n in z.namelist() if n.endswith('.dex')] + [
    'resources.arsc', 'AndroidManifest.xml',
]

with open(OUT, 'w', encoding='utf-8', errors='replace') as fh:
    for name in names:
        try:
            data = z.read(name)
        except KeyError:
            continue
        fh.write(f'\n########## {name}\n')
        for m in RUN.finditer(data):
            s = m.group(0).decode('latin-1')
            fh.write(s + '\n')

print('written', OUT)
