#!/usr/bin/env python3
"""版の数字を、使っているすべての場所で、まとめて更新します。

使い方:  python3 tools/bump_version.py 2.1.1

更新する場所:
  js/version.js   … APP_VERSION（画面の「ver」表示は、ここから作られます）
  sw.js           … VERSION（端末に「新しい版が来た」と気づかせる目印）
  index.html      … 先頭のコメント
  README.md       … 版のバッジ
確認だけする場所:
  CHANGELOG.md    … 「## [新しい版]」の見出しがあるか（無ければ、追加を促します）
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def replace_once(rel, pattern, repl):
    path = ROOT / rel
    text = path.read_text(encoding='utf-8')
    new, n = re.subn(pattern, repl, text, count=1)
    if n != 1:
        sys.exit(f'エラー: {rel} に、更新する場所が見つかりません（{pattern}）')
    path.write_text(new, encoding='utf-8')
    print(f'  更新: {rel}')


def main():
    if len(sys.argv) != 2 or not re.fullmatch(r'\d+\.\d+\.\d+', sys.argv[1]):
        sys.exit('使い方: python3 tools/bump_version.py 2.1.1   （数字3つを、ドットでつなぐ）')
    v = sys.argv[1]
    print(f'版を {v} に更新します')
    replace_once('js/version.js', r"const APP_VERSION = '[^']*';", f"const APP_VERSION = '{v}';")
    replace_once('sw.js', r"const VERSION = '[^']*';", f"const VERSION = 'v{v}';")
    replace_once('index.html', r"ver \d+\.\d+\.\d+ / MIT License", f"ver {v} / MIT License")
    replace_once('README.md', r"version-\d+\.\d+\.\d+-blue", f"version-{v}-blue")
    changelog = (ROOT / 'CHANGELOG.md').read_text(encoding='utf-8')
    if f'## [{v}]' not in changelog:
        print(f'  注意: CHANGELOG.md に「## [{v}]」の見出しがありません。変更内容を書き足してください')
    print('完了。続けて、python3 tests/run_all.py で、確認してください')


if __name__ == '__main__':
    main()
