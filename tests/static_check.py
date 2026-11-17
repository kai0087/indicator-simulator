#!/usr/bin/env python3
"""静的チェック（ブラウザを動かさずに、ファイルの中身だけで調べる）。

調べる内容:
  1. index.html が読み込むファイルが、すべて存在する
  2. sw.js の保存一覧（FILES）に、必要なファイルがすべて入っていて、存在しないファイルが無い
  3. 版の数字が、version.js・sw.js・index.html・README.md・CHANGELOG.md で、そろっている
  4. JavaScriptの文法が正しい（Node.js があるとき）
  5. 同じ名前の関数・変数が、複数のファイルで二重に定義されていない
  6. index.html の onclick などが呼ぶ関数が、すべて定義されている
  7. JavaScriptが getElementById で探す id が、index.html に存在する
  8. js/ の全ファイルが、index.html から読み込まれ、sw.js の一覧にも入っている

使い方:  python3 tests/static_check.py [--root リポジトリのフォルダ]
"""
import argparse
import pathlib
import re
import shutil
import subprocess
import sys

DEFAULT_ROOT = pathlib.Path(__file__).resolve().parent.parent


def read(root, rel):
    return (root / rel).read_text(encoding='utf-8')


def run_checks(root):
    """戻り値: [(項目名, 成功か, 詳細)]"""
    results = []

    def ok(name, cond, detail=''):
        results.append((name, bool(cond), detail))

    html = read(root, 'index.html')
    sw = read(root, 'sw.js')

    # 1. index.html が読み込むファイル
    refs = re.findall(r'<link[^>]+href="([^"#?]+)"', html) + re.findall(r'<script[^>]+src="([^"#?]+)"', html)
    local = [r[2:] if r.startswith('./') else r for r in refs if not re.match(r'https?:', r)]
    missing = [r for r in local if not (root / r).exists()]
    ok('index.html が読み込むファイルが、すべて存在する', not missing, f'無いファイル: {missing}')

    # 2. sw.js の保存一覧
    m = re.search(r'const FILES = \[(.*?)\];', sw, re.S)
    files = re.findall(r"'\./?([^']*)'", m.group(1)) if m else []
    files = [f for f in files if f]  # './'（トップページ）は、index.html と同じなので、数えない
    ok('sw.js に、保存一覧（FILES）がある', bool(files))
    ok('sw.js の保存一覧に、存在しないファイルが無い', not [f for f in files if not (root / f).exists()],
       f'{[f for f in files if not (root / f).exists()]}')
    needed = set(local) | {'index.html'}
    not_cached = sorted(n for n in needed if n not in files)
    ok('index.html が読み込むファイルが、すべて sw.js の保存一覧に入っている', not not_cached, f'一覧に無い: {not_cached}')
    ok('sw.js の保存一覧に、重複が無い', len(files) == len(set(files)))

    # 3. 版の数字
    ver = re.search(r"const APP_VERSION = '([^']+)'", read(root, 'js/version.js'))
    ver = ver.group(1) if ver else None
    ok('js/version.js に、版の数字がある', ver)
    if ver:
        swv = re.search(r"const VERSION = 'v([^']+)'", sw)
        ok('sw.js の VERSION が、version.js と同じ', swv and swv.group(1) == ver, f'sw.js={swv and swv.group(1)} / version.js={ver}')
        hv = re.search(r'ver (\d+\.\d+\.\d+) / MIT License', html)
        ok('index.html の先頭コメントの版が、version.js と同じ', hv and hv.group(1) == ver, f'index.html={hv and hv.group(1)}')
        rv = re.search(r'version-(\d+\.\d+\.\d+)-blue', read(root, 'README.md'))
        ok('README.md の版のバッジが、version.js と同じ', rv and rv.group(1) == ver, f'README={rv and rv.group(1)}')
        cl = re.search(r'^## \[(\d+\.\d+\.\d+)\]', read(root, 'CHANGELOG.md'), re.M)
        ok('CHANGELOG.md の一番上の版が、version.js と同じ', cl and cl.group(1) == ver, f'CHANGELOG={cl and cl.group(1)}')

    # 4. JavaScriptの文法
    js_files = sorted((root / 'js').glob('*.js'))
    if shutil.which('node'):
        bad = []
        for f in js_files:
            r = subprocess.run(['node', '--check', str(f)], capture_output=True, text=True)
            if r.returncode != 0:
                bad.append(f'{f.name}: {r.stderr.strip().splitlines()[0] if r.stderr else ""}')
        ok('JavaScriptの文法が、すべて正しい（node --check）', not bad, '; '.join(bad))
    else:
        ok('JavaScriptの文法チェック（Node.js が無いので、省略）', True)

    # 5. 二重定義
    seen, dup = {}, []
    for f in js_files:
        for line in f.read_text(encoding='utf-8').splitlines():
            m2 = re.match(r'^(?:async\s+)?function\s+(\w+)\s*\(', line) or re.match(r'^(?:const|let|var)\s+(\w+)', line)
            if m2:
                name = m2.group(1)
                if name in seen:
                    dup.append(f'{name}（{seen[name]} と {f.name}）')
                seen[name] = f.name
    ok('同じ名前の関数・変数が、二重に定義されていない', not dup, '; '.join(dup))

    # 6. onclick などが呼ぶ関数
    handlers = set(re.findall(r'\son\w+="\s*(?:[\w.]+\()?\s*(\w+)\(', html))
    handlers |= set(re.findall(r'\son(?:click|input|change)="(\w+)\(', html))
    defined = set(seen)
    undefined = sorted(h for h in handlers if h not in defined and h not in {'event', 'window'})
    # window.print() など標準の関数は除く
    undefined = [h for h in undefined if h not in {'print'}]
    ok('index.html の onclick などが呼ぶ関数が、すべて定義されている', not undefined, f'未定義: {undefined}')

    # 7. getElementById の id
    ids_in_html = set(re.findall(r'\sid="([^"]+)"', html))
    used = set()
    for f in js_files:
        used |= set(re.findall(r"getElementById\('([^']+)'\)", f.read_text(encoding='utf-8')))
    ok('JavaScriptが getElementById で探す id が、すべて index.html にある', not (used - ids_in_html), f'無いid: {sorted(used - ids_in_html)}')

    # 8. js/ の全ファイルが読み込まれている
    loaded = {pathlib.PurePosixPath(r).name for r in local if r.startswith('js/')}
    orphan = [f.name for f in js_files if f.name not in loaded]
    ok('js/ の全ファイルが、index.html から読み込まれている', not orphan, f'読み込まれていない: {orphan}')
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default=str(DEFAULT_ROOT))
    args = ap.parse_args()
    results = run_checks(pathlib.Path(args.root))
    fails = 0
    for name, passed, detail in results:
        print(('  OK  ' if passed else '  NG  ') + name + ('' if passed or not detail else f'\n        → {detail}'))
        fails += 0 if passed else 1
    print(f'静的チェック: {len(results) - fails}/{len(results)} 件が成功')
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
