#!/usr/bin/env python3
"""すべての確認（静的チェック＋動作テスト）を、まとめて実行します。

使い方:  python3 tests/run_all.py [--root リポジトリのフォルダ]
  ・すべて成功すると、終了コード 0。1件でも失敗すると、1
  ・Node.js（文法チェック用）と、Playwright（Python版）＋Chromium（動作テスト用）が必要です
"""
import argparse
import pathlib
import shutil
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import e2e_test
import static_check

DEFAULT_ROOT = pathlib.Path(__file__).resolve().parent.parent


def show(results):
    fails = 0
    for name, ok, detail in results:
        print(('  OK  ' if ok else '  NG  ') + name + ('' if ok or not detail else f'\n        → {detail}'))
        fails += 0 if ok else 1
    return fails


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default=str(DEFAULT_ROOT))
    args = ap.parse_args()
    root = pathlib.Path(args.root).resolve()

    print('■ 静的チェック（ファイルの中身を調べる）')
    site = e2e_test.prepare_root(root)      # アイコン等が無い場所でも調べられるよう、仮のファイルで補ったコピーを使う
    try:
        s_res = static_check.run_checks(site)
    finally:
        shutil.rmtree(site.parent, ignore_errors=True)
    f1 = show(s_res)
    print(f'  → {len(s_res) - f1}/{len(s_res)} 件が成功\n')

    print('■ 動作テスト（ブラウザを自動で動かす）')
    e_res = e2e_test.run(root)
    f2 = show(e_res)
    print(f'  → {len(e_res) - f2}/{len(e_res)} 件が成功\n')

    total = len(s_res) + len(e_res)
    fails = f1 + f2
    print(('すべて成功' if not fails else f'失敗あり：{fails} 件') + f'（全 {total} 件）')
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
