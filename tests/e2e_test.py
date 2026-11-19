#!/usr/bin/env python3
"""動作テスト（ブラウザを自動で動かして、アプリの動きを確かめる）。

Playwright（Python版）と、Chromium が必要です。
使い方:  python3 tests/e2e_test.py [--root リポジトリのフォルダ]

何をするか:
  ・リポジトリのコピーを作り（無いアイコン等は、仮のファイルで補う）、簡易サーバーで公開
  ・各テストを、まっさらなブラウザ（保存データ無し）で実行
  ・見た目は、「計算された値」（幅・色・文字の大きさなど）で確かめる
"""
import argparse
import base64
import functools
import http.server
import json
import pathlib
import re
import shutil
import sys
import tempfile
import threading

from playwright.sync_api import sync_playwright

DEFAULT_ROOT = pathlib.Path(__file__).resolve().parent.parent
RESULTS = []


def check(name, cond, detail=''):
    RESULTS.append((name, bool(cond), '' if cond else str(detail)))


# ---------------------------------------------------------------- 準備
PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==')


def prepare_root(root, patch=None):
    """リポジトリを、一時フォルダにコピーし、無いファイル（manifest・アイコン）は、仮のもので補う"""
    tmp = pathlib.Path(tempfile.mkdtemp(prefix='indicator_'))
    dst = tmp / 'site'
    shutil.copytree(root, dst, ignore=shutil.ignore_patterns('.git', 'tests', 'tools', '__pycache__', '*.zip', '*.pdf'))
    for name in ('icon-192.png', 'icon-512.png', 'apple-touch-icon.png'):
        if not (dst / name).exists():
            (dst / name).write_bytes(PNG)
    if not (dst / 'manifest.webmanifest').exists():
        (dst / 'manifest.webmanifest').write_text(json.dumps({'name': 't', 'start_url': './', 'display': 'standalone', 'icons': []}))
    if patch:
        patch(dst)
    return dst


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def start_server(directory):
    handler = functools.partial(Quiet, directory=str(directory))
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f'http://127.0.0.1:{srv.server_address[1]}'


class App:
    def __init__(self, browser, base, width=420, height=900):
        self.base = base
        self.ctx = browser.new_context(viewport={'width': width, 'height': height})
        self.page = self.ctx.new_page()
        self.errors, self.alerts, self.bad = [], [], []
        self.hook(self.page)

    def hook(self, page):
        page.on('pageerror', lambda e: self.errors.append(str(e)))
        page.on('dialog', lambda d: (self.alerts.append(d.message), d.accept()))
        page.on('requestfailed', lambda r: self.bad.append(r.url))
        page.on('response', lambda r: self.bad.append(f'{r.status} {r.url}') if r.status >= 400 else None)

    def open(self, hash_='', page=None):
        page = page or self.page
        page.goto(f'{self.base}/index.html{hash_}')
        page.wait_for_function('typeof renderGrid === "function" && document.querySelectorAll(".cell").length > 0')
        return page

    def new_page(self):
        p = self.ctx.new_page()
        self.hook(p)
        return p

    @property
    def ev(self):
        return self.page.evaluate

    def close(self):
        self.ctx.close()


def names(app, sel):
    return app.ev(f"[...document.querySelectorAll('{sel} .color-btn')].map(b=>b.title)")


def b64url(b):
    return base64.urlsafe_b64encode(b).decode().rstrip('=')


# ---------------------------------------------------------------- テスト
def t_initial(br, base):
    a = App(br, base); p = a.open()
    ver = a.ev('APP_VERSION')
    check('【初期】版の表示が、version.js から作られている', a.ev("document.getElementById('app-version').textContent") == 'ver ' + '.'.join(ver.split('.')[:2]), a.ev("document.getElementById('app-version').textContent"))
    check('【初期】全車型が、2行3列（[3,3]）で始まる', a.ev('TYPES.map(t=>project.sheets[t].rowCols)') == [[3, 3]] * 3)
    check('【初期】文字サイズは「自動」だけ（選択欄が無い）', a.ev("TYPES.every(t=>project.sheets[t].fontSize==='text-size-auto')") and not a.ev("!!document.getElementById('font-size-select')"))
    check('【初期】背景色は、シロ・クロ・アカ・アオ・ミド', names(a, '#palette-single') == ['シロ', 'クロ', 'アカ', 'アオ', 'ミド'], names(a, '#palette-single'))
    check('【初期】指示記号の色は、自動・アカ・アオ・ミド・キイ', names(a, '#palette-single-text') == ['自動', 'アカ', 'アオ', 'ミド', 'キイ'], names(a, '#palette-single-text'))
    check('【初期】行の選択肢は 1〜3 行', a.ev("[...document.getElementById('rows-select').options].map(o=>o.textContent)") == ['1 行', '2 行', '3 行'])
    check('【初期】列の選択肢は「行ごと」と 1〜5 列', a.ev("[...document.getElementById('cols-select').options].map(o=>o.textContent)") == ['行ごと', '1 列', '2 列', '3 列', '4 列', '5 列'])
    check('【初期】行ごとの列数の選択肢も 1〜5 列', a.ev("[...document.querySelector('#row-cols-editor select').options].map(o=>o.value)") == ['1', '2', '3', '4', '5'])
    check('【初期】エラー・読み込み失敗が無い', not a.errors and not a.bad, (a.errors, a.bad))
    a.close()


def t_row_frames(br, base):
    a = App(br, base); p = a.open()
    p.select_option('#row-cols-editor label:nth-child(2) select', '1')
    r = a.ev("""(()=>{const g=document.getElementById('sheet-grid');const gs=getComputedStyle(g);
      return {gb:gs.borderTopWidth,gbg:gs.backgroundColor,rows:[...document.querySelectorAll('.sheet-row')].map(r=>({b:getComputedStyle(r).borderTopWidth,w:Math.round(r.getBoundingClientRect().width),cw:[...r.querySelectorAll('.cell')].map(c=>Math.round(c.getBoundingClientRect().width))})),empty:document.querySelectorAll('.cell-empty').length}})()""")
    check('【枠】行ごとの列数 [3,1] が、データに反映される', a.ev('gridState.rowCols') == [3, 1] and a.ev('gridState.cells.length') == 4)
    check('【枠】全体の外枠が無い', r['gb'] == '0px' and r['gbg'] == 'rgba(0, 0, 0, 0)', r)
    check('【枠】各行が、自分の枠（3px）を持つ', all(x['b'] == '3px' for x in r['rows']), r)
    check('【枠】マス1つの幅が、全行で同じ', len({c for x in r['rows'] for c in x['cw']}) == 1, r)
    check('【枠】列が少ない行は、短い枠で、空白のマスは作らない', r['rows'][1]['w'] < r['rows'][0]['w'] and r['empty'] == 0 and len(r['rows'][1]['cw']) == 1, r)
    p.select_option('#cols-select', '2')
    check('【枠】「列（全行まとめて）」で、全行がそろう', a.ev('gridState.rowCols') == [2, 2])
    check('【枠】行を増やすと、直前の行と同じ列数になる', (p.select_option('#rows-select', '3'), a.ev('gridState.rowCols'))[1] == [2, 2, 2])
    check('【枠】エラーが無い', not a.errors, a.errors)
    a.close()


def t_colors_and_clear(br, base):
    a = App(br, base); p = a.open()
    p.fill('#text-single', 'AB'); p.click('#palette-single .color-btn[title="クロ"]')
    col = lambda: a.ev("getComputedStyle(document.querySelector('.cell-single .sym')).color")
    check('【色】黒い背景の「自動」の文字は、白', col() == 'rgb(255, 255, 255)', col())
    p.click('#palette-single-text .color-btn[title="アカ"]')
    check('【色】指示記号の色を指定すると、その色になる', col() == 'rgb(239, 68, 68)', col())
    check('【色】選んだ指示記号の色のボタンが、選択状態になる', a.ev("document.querySelector('#palette-single-text .active').title") == 'アカ')
    p.click('#palette-single-text .color-btn[title="自動"]')
    check('【色】「自動」に戻せる', col() == 'rgb(255, 255, 255)', col())
    p.click('#palette-single-text .color-btn[title="キイ"]')
    p.click('#single-controls .name-row .btn')
    c = a.ev('gridState.cells[0]')
    check('【クリア】指示記号のクリアで、文字・背景色・文字色が初期に戻る', c['singleText'] == '' and c['singleColor'] == '#ffffff' and c['singleTextColor'] == '', c)
    # オールクリア
    p.fill('#process-name', 'A工程'); p.fill('#text-name', '作業'); p.click('#split-lr-btn')
    p.fill('#text-left', 'アカ'); p.click('#palette-left .color-btn[title="アカ"]'); p.click('#palette-left-text .color-btn[title="キイ"]')
    p.click('.tab-btn[data-type="GD"]'); p.fill('#text-single', 'アオ'); p.click('#palette-single .color-btn[title="アオ"]')
    p.evaluate("applyRowCols([3,1])")
    p.click('text=オールクリア')
    st = a.ev("""(()=>({pn:project.processName,inputs:document.getElementById('process-name').value,
       all:TYPES.every(t=>project.sheets[t].cells.every(c=>!c.name&&!c.singleText&&!c.leftText&&!c.rightText&&c.singleColor==='#ffffff'&&c.leftColor==='#ffffff'&&c.rightColor==='#ffffff'&&!c.singleTextColor&&!c.leftTextColor&&!c.rightTextColor)),
       split:project.sheets.L4.cells[0].isSplit,rc:project.sheets.GD.rowCols}))()""")
    check('【オールクリア】工程名・作業名・指示記号・背景色・文字色が、全タブで消える', st['pn'] == '' and st['inputs'] == '' and st['all'], st)
    check('【オールクリア】マスの数と、左右の分割は残る', st['split'] is True and st['rc'] == [3, 1], st)
    check('【オールクリア】確認のメッセージが出る', any('オールクリア' in m or '消します' in m for m in a.alerts), a.alerts)
    check('【色】エラーが無い', not a.errors, a.errors)
    a.close()


def t_name_sync(br, base):
    a = App(br, base); p = a.open()
    p.evaluate("applyRowCols([3,1])")                                        # L4：1行目3列・2行目1列
    p.click('.tab-btn[data-type="GD"]'); p.select_option('#rows-select', '2'); p.click('.tab-btn[data-type="L4"]')
    p.evaluate("selectCell(3)")                                              # 2行1列目
    check('【作業名】選んだマスのラベルが「2行 - 1列目」', p.inner_text('#target-cell-label') == '2行 - 1列目', p.inner_text('#target-cell-label'))
    p.fill('#text-name', 'A'); 
    check('【作業名】チェック無しでは、他の車型は変わらない', a.ev("['V6','GD'].every(t=>project.sheets[t].cells.every(c=>c.name===''))"))
    p.check('#name-sync'); p.fill('#text-name', 'ナット')
    pos = a.ev("['V6','GD'].map(t=>{const s=project.sheets[t];return s.cells[indexOfRC(s,1,0)].name})")
    check('【作業名】チェックありで、他の車型の同じ位置（行・列）に反映される', pos == ['ナット', 'ナット'], pos)
    p.click('text=✕ クリア')
    check('【作業名】クリアも、他の車型に反映される', a.ev("['V6','GD'].map(t=>{const s=project.sheets[t];return s.cells[indexOfRC(s,1,0)].name})") == ['', ''])
    p.evaluate("selectCell(0)")
    check('【作業名】別のマスを選ぶと、チェックが外れる', a.ev("document.getElementById('name-sync').checked") is False)
    # 相手に行・列が無い車型は、何もしない
    p.click('.tab-btn[data-type="GD"]'); p.select_option('#rows-select', '1'); p.click('.tab-btn[data-type="L4"]'); p.evaluate("selectCell(3)")
    p.check('#name-sync'); p.fill('#text-name', 'X')
    check('【作業名】相手に位置が無い車型は、何もしない（エラーも出ない）', a.ev("project.sheets.GD.cells.every(c=>c.name==='')") and not a.errors, a.errors)
    a.close()


def t_save_flow(br, base):
    a = App(br, base); p = a.open()
    presets = lambda: a.ev("Object.keys(JSON.parse(localStorage.getItem('indicator_presets')||'{}'))")
    p.fill('#process-name', '工程A'); p.click('text=現在の配置を保存')
    check('【保存】保存名が空なら、工程名が保存名になる', presets() == ['工程A'], presets())
    p.fill('#preset-name', '別名'); p.click('text=現在の配置を保存')
    check('【保存】保存名があれば、そちらを優先する', sorted(presets()) == ['別名', '工程A'], presets())
    p.fill('#process-name', ''); p.evaluate("onProcessNameInput()"); p.fill('#preset-name', '')
    p.click('text=現在の配置を保存')
    check('【保存】保存名も工程名も空なら、入力のポップアップが出る', a.ev("document.getElementById('save-name-modal').classList.contains('active')"))
    btn = p.locator('#save-name-modal button.btn-primary'); btn.click()
    check('【保存】空のまま確定すると、入力を促すメッセージが出る', p.inner_text('#save-name-msg') == '保存名を入力してください。', p.inner_text('#save-name-msg'))
    p.fill('#save-name-input', '新規'); btn.click()
    check('【保存】入力した名前で保存される', '新規' in presets(), presets())
    check('【保存】保存データに、工程名と3車型が入る', a.ev("(()=>{const o=JSON.parse(localStorage.getItem('indicator_presets'))['工程A'];return o.processName==='工程A'&&Object.keys(o.sheets).join()==='L4,V6,GD'})()"))
    check('【保存】エラーが無い', not a.errors, a.errors)
    a.close()


def t_mismatch(br, base):
    a = App(br, base); p = a.open()
    p.evaluate("selectCell(1)"); p.fill('#text-single', 'アカ'); p.click('#palette-single .color-btn[title="アオ"]')
    p.click('.tab-btn[data-type="GD"]'); p.evaluate("selectCell(2)"); p.fill('#text-single', 'ミド')   # 背景は白のまま
    issues = a.ev('findColorMismatches().map(i=>i.place+"|"+i.text+"|"+i.actualName)')
    check('【保存前確認】文字と背景色の食い違いを、場所つきで検出する', issues == ['L4 1行-2列目|アカ|アオ', 'GD 1行-3列目|ミド|シロ'], issues)
    check('【保存前確認】色名ではない文字は、対象にならない', (p.fill('#text-single', 'A1'), len(a.ev('findColorMismatches()')))[1] == 1)
    p.fill('#preset-name', 'T'); p.click('text=現在の配置を保存')
    check('【保存前確認】警告のポップアップが出る', a.ev("document.getElementById('warn-modal').classList.contains('active')"))
    p.click('#warn-modal >> text=修正する')
    check('【保存前確認】「修正する」で、問題のあるタブ・マスに移動する', a.ev('[activeType, selectedCellIndex]') == ['L4', 1], a.ev('[activeType, selectedCellIndex]'))
    p.click('text=現在の配置を保存'); p.click('#warn-modal >> text=このまま保存')
    check('【保存前確認】「このまま保存」で保存される', a.ev("Object.keys(JSON.parse(localStorage.getItem('indicator_presets')||'{}'))") == ['T'])
    a.close()


def t_presets_legacy(br, base):
    a = App(br, base); p = a.open()
    old = {'rows': 2, 'cols': 3, 'fontSize': 'text-size-lg', 'cells': [{'name': '旧', 'isSplit': False, 'singleText': 'アオ', 'singleColor': '#3b82f6'}] * 6}
    newer = {'processName': '旧工程', 'sheets': {t: {'rows': 2, 'cols': 2, 'fontSize': 'text-size-md', 'cells': [{'name': t, 'isSplit': False, 'singleText': '', 'singleColor': '#ffffff'}] * 4} for t in ('L4', 'V6', 'GD')}}
    p.evaluate("o=>localStorage.setItem('indicator_presets',JSON.stringify(o))", {'旧1枚': old, '旧3枚': newer})
    p.evaluate("applyPreset('旧1枚')")
    check('【旧データ】1枚だけの旧形式は、L4として読み込まれ、行ごとの列数に変換される', a.ev('project.sheets.L4.rowCols') == [3, 3] and a.ev('project.sheets.L4.cells[0].name') == '旧')
    check('【旧データ】文字サイズ（大）は、自動になる', a.ev("TYPES.every(t=>project.sheets[t].fontSize==='text-size-auto')"))
    p.evaluate("applyPreset('旧3枚')")
    check('【旧データ】rows/cols 形式の3車型データも、読み込める', a.ev('project.sheets.GD.rowCols') == [2, 2] and a.ev('project.processName') == '旧工程' and p.input_value('#process-name') == '旧工程')
    check('【旧データ】エラーが無い', not a.errors, a.errors)
    a.close()


def t_qr_roundtrip(br, base):
    a = App(br, base); p = a.open()
    p.evaluate("applyRowCols([3,1])"); p.fill('#process-name', 'B工程')
    p.fill('#text-name', 'ボルト'); p.fill('#text-single', 'アカ'); p.click('#palette-single .color-btn[title="アカ"]'); p.click('#palette-single-text .color-btn[title="キイ"]')
    p.evaluate("selectCell(1)"); p.click('#split-lr-btn'); p.fill('#text-left', 'ミド'); p.evaluate("gridState.cells[1].leftColor='#00bcd4'; gridState.cells[1].rightTextColor='#a855f7'; renderGrid()")
    p.click('.tab-btn[data-type="GD"]'); p.fill('#text-name', 'GD作業')
    url = a.ev("buildShareUrl(['L4','GD'])")
    check('【QR】URLに #d= のデータが付く', '#d=' in url)
    v = App(br, base); vp = v.open(url[url.index('#'):])
    st = v.ev("({pn:project.processName,rc:gridState.rowCols,act:activeType,cell:project.sheets.L4.cells[1],c0:project.sheets.L4.cells[0],gd:project.sheets.GD.cells[0].name,v6:project.sheets.V6.cells.every(c=>!c.name)})")
    check('【QR】工程名・行ごとの列数が、受け取り側に届く', st['pn'] == 'B工程' and st['rc'] == [3, 1] and st['act'] == 'L4', st)
    check('【QR】背景色・指示記号の色が、色の一覧に無い色も含めて、届く', st['cell']['leftColor'] == '#00bcd4' and st['cell']['rightTextColor'] == '#a855f7' and st['c0']['singleTextColor'] == '#facc15', st)
    check('【QR】送っていない車型は、空のまま', st['v6'] is True and st['gd'] == 'GD作業')
    vis = lambda sel: v.ev(f"(()=>{{const e=document.querySelector('{sel}');return !!e&&getComputedStyle(e).display!=='none'}})()")
    check('【閲覧モード】編集パネル・行列の設定・ヘッダーが隠れる', not vis('.control-panel') and not vis('.grid-config-bar') and not vis('header'))
    check('【閲覧モード】案内バーに、工程名が出る', vis('.view-bar') and vp.inner_text('#view-process') == 'B工程', vp.inner_text('#view-process'))
    check('【閲覧モード】受け取った車型のタブだけが出る', [vis(f'.tab-btn[data-type="{t}"]') for t in ('L4', 'V6', 'GD')] == [True, False, True])
    ring = v.ev("getComputedStyle(document.querySelector('.cell.selected'),'::after').display")
    bar = v.ev("getComputedStyle(document.querySelector('.cell.selected .cell-name')).backgroundColor")
    check('【閲覧モード】選択の黒枠・黒い作業名欄は、出ない', ring == 'none' and bar != 'rgb(0, 0, 0)', (ring, bar))
    vp.click('text=編集画面を開く')
    check('【閲覧モード】「編集画面を開く」で、通常の画面に戻り、データは残る', vis('.control-panel') and vp.input_value('#process-name') == 'B工程' and v.ev('location.hash') == '')
    check('【QR】エラーが無い', not a.errors and not v.errors, (a.errors, v.errors))
    # QR画像（共有画面）
    p.click('text=🔗 共有/QR')
    p.wait_for_function("getComputedStyle(document.getElementById('qr-canvas')).display==='block'", timeout=5000)
    check('【QR】共有画面で、QRが描かれる', a.ev("document.getElementById('qr-canvas').width") > 100)
    p.uncheck('#share-types input:checked')
    p.wait_for_function("getComputedStyle(document.getElementById('qr-canvas')).display==='none'", timeout=5000)
    check('【QR】車型を1つも選ばないと、QRは出ず、案内が出る', 'チェック' in p.inner_text('#share-msg'), p.inner_text('#share-msg'))
    v.close(); a.close()


def t_legacy_qr(br, base):
    cells3 = [['作', 0, 'アカ', 1]] * 3
    v1 = {'v': 1, 's': {'L4': {'r': 2, 'c': 3, 'f': 'md', 'k': [['作', 0, 'アカ', 1]] * 6}}}
    v2 = {'v': 2, 'n': '旧V2', 's': {'L4': {'r': [3, 1], 'f': 'lg', 'k': cells3 + [['作', 1, 'アオ', 2, 'キ', 4]]}}}
    for label, data in (('形式1', v1), ('形式2', v2)):
        a = App(br, base); p = a.open('#d=r' + b64url(json.dumps(data, ensure_ascii=False).encode()))
        rc = a.ev('gridState.rowCols'); fs = a.ev('gridState.fontSize'); c0 = a.ev('gridState.cells[0].singleColor')
        check(f'【旧QR】{label}のQRも読み込める（色は、昔の10色の表で復元）', c0 == '#ef4444' and rc == ([3, 3] if label == '形式1' else [3, 1]), (rc, c0))
        check(f'【旧QR】{label}の文字サイズ（中・大）は、自動になる', fs == 'text-size-auto', fs)
        if label == '形式2':
            check('【旧QR】形式2の工程名が、受け取り側に出る', p.inner_text('#view-process') == '旧V2' and a.ev('gridState.cells[3].leftColor') == '#3b82f6' and a.ev('gridState.cells[3].rightColor') == '#facc15')
        check(f'【旧QR】{label}でエラーが無い', not a.errors, a.errors)
        a.close()
    # 不正なデータ
    a = App(br, base); a.open('#d=rAAAA'); 
    check('【旧QR】壊れたQRは、エラー画面にならず、メッセージが出る', any('読み込めませんでした' in m for m in a.alerts) and not a.errors, (a.alerts, a.errors))
    a.close()
    # 上限を超える旧データ（4行×7列）
    big = {'v': 3, 'n': '', 'p': ['ffffff'], 's': {'L4': {'r': [7] * 4, 'f': 'md', 'k': [['', 0, '', 0, -1]] * 28}}}
    a = App(br, base); a.open('#d=r' + b64url(json.dumps(big).encode()))
    check('【上限】4行×7列の古いデータも開け、選択欄に、その値が出る', a.ev('gridState.rowCols') == [7] * 4 and a.ev("document.getElementById('rows-select').value") == '4' and a.ev("document.getElementById('cols-select').value") == '7')
    a.close()


def t_auto_font(br, base):
    a = App(br, base); p = a.open()
    p.fill('#text-single', 'アカ')
    m = a.ev("""(sel)=>{const b=document.querySelector(sel);const s=b.querySelector('.sym');const cs=getComputedStyle(b);
      const W=b.clientWidth-parseFloat(cs.paddingLeft)-parseFloat(cs.paddingRight),H=b.clientHeight-parseFloat(cs.paddingTop)-parseFloat(cs.paddingBottom);
      const em=parseFloat(s.style.getPropertyValue('--em'));return {fs:parseFloat(getComputedStyle(s).fontSize),exp:Math.min(.6*H,.6*W/em)}}""", '.cell-single')
    check('【自動サイズ】分割なしのマスで、文字の大きさが、マスの約60%', abs(m['fs'] - m['exp']) < 0.6, m)
    p.click('#split-lr-btn'); p.fill('#text-left', 'アカ')
    m2 = a.ev("""(sel)=>{const b=document.querySelector(sel);const s=b.querySelector('.sym');const cs=getComputedStyle(b);
      const W=b.clientWidth-parseFloat(cs.paddingLeft)-parseFloat(cs.paddingRight),H=b.clientHeight-parseFloat(cs.paddingTop)-parseFloat(cs.paddingBottom);
      const em=parseFloat(s.style.getPropertyValue('--em'));return {fs:parseFloat(getComputedStyle(s).fontSize),exp:Math.min(.6*H,.6*W/em)}}""", '.cell-left')
    check('【自動サイズ】左右に分割した縦長のマスでも、約60%に収まる', abs(m2['fs'] - m2['exp']) < 0.6 and m2['fs'] < m['fs'], (m, m2))
    check('【自動サイズ】エラーが無い', not a.errors, a.errors)
    a.close()


def t_selected_style(br, base):
    a = App(br, base, width=390, height=844); p = a.open()
    p.select_option('#rows-select', '3'); p.evaluate("selectCell(1)"); p.fill('#text-name', 'ナット仮止め')
    st = a.ev("""(()=>{const c=document.querySelector('.cell.selected');const r=getComputedStyle(c,'::after');const n=getComputedStyle(c.querySelector('.cell-name'));
       return {bw:[r.borderTopWidth,r.borderRightWidth,r.borderBottomWidth,r.borderLeftWidth],bc:r.borderTopColor,nbg:n.backgroundColor,nc:n.color,nz:n.zIndex,rz:r.zIndex}})()""")
    check('【選択】選択中のマスは、4辺とも黒の太線（4px）', st['bw'] == ['4px'] * 4 and st['bc'] == 'rgb(0, 0, 0)', st)
    check('【選択】作業名の欄は、黒地・白文字で、枠線より手前に出る（隠れない）', st['nbg'] == 'rgb(0, 0, 0)' and st['nc'] == 'rgb(255, 255, 255)' and int(st['nz']) > int(st['rz']), st)
    p.evaluate("selectCell(0)")
    other = a.ev("getComputedStyle(document.querySelectorAll('.cell')[1].querySelector('.cell-name')).backgroundColor")
    check('【選択】選ばれていないマスの作業名欄は、通常の色', other == 'rgb(243, 244, 246)', other)
    p.evaluate("selectCell(1)")
    p.emulate_media(media='print')
    pr = a.ev("(()=>{const c=document.querySelector('.cell.selected');return [getComputedStyle(c,'::after').display,getComputedStyle(c.querySelector('.cell-name')).backgroundColor]})()")
    check('【選択】印刷では、黒枠も黒い作業名欄も出ない', pr[0] == 'none' and pr[1] != 'rgb(0, 0, 0)', pr)
    p.emulate_media(media='screen')
    try:
        from PIL import Image
        import io
        png = p.locator('.cell.selected .cell-name').screenshot()
        im = Image.open(io.BytesIO(png)).convert('RGB'); w, h = im.size
        white = sum(1 for x in range(w) for y in range(h) if min(im.getpixel((x, y))) > 200)
        check('【選択】スマホの幅で、作業名の白い文字が、実際に画面に描かれている', white > 20, f'白い画素: {white}')
    except ImportError:
        pass
    check('【選択】エラーが無い', not a.errors, a.errors)
    a.close()


def t_color_settings(br, base):
    a = App(br, base); p = a.open()
    p.click('text=🎨 色の設定')
    check('【色の設定】背景色5・指示記号の色4が、一覧に出る', a.ev("[document.querySelectorAll('#color-list-bg .color-row').length,document.querySelectorAll('#color-list-text .color-row').length]") == [5, 4])
    p.click('text=＋ 背景色を追加'); p.click('text=＋ 指示記号の色を追加'); p.click('text=＋ 指示記号の色を追加')
    check('【色の設定】追加で、色ボタンが増える（背景色・指示記号の色が別々）', a.ev("[document.querySelectorAll('#palette-single .color-btn').length,document.querySelectorAll('#palette-single-text .color-btn').length]") == [6, 7])
    p.fill('#color-list-bg .color-row:last-child .input-text', 'ミズ')
    p.evaluate("(()=>{const i=document.querySelector('#color-list-bg .color-row:last-child input[type=color]');i.value='#00bcd4';i.dispatchEvent(new Event('input'))})()")
    check('【色の設定】名前・色の変更が、すぐ反映される', a.ev("COLOR_PRESETS[5].name+COLOR_PRESETS[5].code") == 'ミズ#00bcd4' and names(a, '#palette-left')[-1] == 'ミズ')
    p.click('#color-list-bg .color-row:nth-child(1) .btn-danger')
    check('【色の設定】削除で、一覧から消える（確認が出る）', a.ev('COLOR_PRESETS.length') == 5 and any('削除' in m for m in a.alerts), a.alerts)
    p.click('#color-modal >> text=閉じる'); p.reload(); p.wait_for_function('document.querySelectorAll(".cell").length>0')
    check('【色の設定】再読込しても、保持される', names(a, '#palette-single')[-1] == 'ミズ' and a.ev('COLOR_PRESETS.length') == 5)
    # 塗ったマスの色は、一覧の変更で変わらない
    p.click('#palette-single .color-btn[title="ミズ"]')
    p.click('text=🎨 色の設定'); p.click('#color-list-bg .color-row:last-child .btn-danger'); p.click('#color-modal >> text=閉じる')
    check('【色の設定】色を削除しても、塗ったマスの色は、そのまま', a.ev('gridState.cells[0].singleColor') == '#00bcd4')
    p.click('text=🎨 色の設定'); p.click('#color-modal >> text=最初の色に戻す')
    check('【色の設定】「最初の色に戻す」で、初期の色になる', names(a, '#palette-single') == ['シロ', 'クロ', 'アカ', 'アオ', 'ミド'] and names(a, '#palette-single-text') == ['自動', 'アカ', 'アオ', 'ミド', 'キイ'])
    # 上限・下限
    for _ in range(16):
        p.click('text=＋ 背景色を追加')
    check('【色の設定】色は、最大20色まで', a.ev('COLOR_PRESETS.length') == 20 and any('最大20色' in m for m in a.alerts), (a.ev('COLOR_PRESETS.length'), a.alerts))
    a.ev("COLOR_PRESETS.splice(1, COLOR_PRESETS.length - 1); renderColorList()")
    p.click('#color-list-bg .color-row .btn-danger')
    check('【色の設定】色は、1つ以上必要', a.ev('COLOR_PRESETS.length') == 1 and any('1つ以上' in m for m in a.alerts))
    # 旧版の色の設定（indicator_colors）は使わない
    b = App(br, base); b.open(); b.ev("localStorage.setItem('indicator_colors', JSON.stringify([{name:'旧',code:'#123456'}]))"); b.page.reload(); b.page.wait_for_function('document.querySelectorAll(".cell").length>0')
    check('【色の設定】旧版の色の設定は、使われず、初期の色になる', names(b, '#palette-single') == ['シロ', 'クロ', 'アカ', 'アオ', 'ミド'])
    check('【色の設定】エラーが無い', not a.errors and not b.errors, (a.errors, b.errors))
    b.close(); a.close()


def t_symbol_controls(br, base):
    a = App(br, base); p = a.open()
    ids_ok = all(a.ev(f"!!document.getElementById('{i}')") for k in ('single', 'left', 'right') for i in (f'text-{k}', f'palette-{k}', f'palette-{k}-text'))
    check('【入力欄】指示記号の入力欄と色ボタンが、全体・左・右の3組、作られる', ids_ok)
    check('【入力欄】各入力欄は、2文字まで・クリアボタン付き', a.ev("[...document.querySelectorAll('#single-controls input,#split-controls input')].every(i=>i.maxLength===2)") and a.ev("document.querySelectorAll('#single-controls .name-row .btn,#split-controls .name-row .btn').length") == 3)
    check('【入力欄】ラベル・入力例の文字が、定義どおり', p.inner_text('label[for="text-left"]') == '左側 指示記号 (最大2文字)' and a.ev("document.getElementById('text-right').placeholder") == '右' and a.ev("document.getElementById('text-single').placeholder") == '例: A1')
    acc = a.ev("[...document.querySelectorAll('#split-controls > div')].map(d=>getComputedStyle(d).borderLeftColor)")
    check('【入力欄】左右の欄に、青・緑の線が付く', acc == ['rgb(59, 130, 246)', 'rgb(16, 185, 129)'], acc)
    vis = lambda: a.ev("[getComputedStyle(document.getElementById('single-controls')).display,getComputedStyle(document.getElementById('split-controls')).display]")
    v1 = vis(); p.click('#split-lr-btn'); v2 = vis()
    check('【入力欄】分割の切り替えで、全体用／左右用の欄が入れ替わる', v1 == ['block', 'none'] and v2 == ['none', 'block'], (v1, v2))
    for k, txt in (('left', 'ア'), ('right', 'イ')):
        p.fill(f'#text-{k}', txt); p.click(f'#palette-{k} .color-btn[title="アカ"]'); p.click(f'#palette-{k}-text .color-btn[title="キイ"]')
    c = a.ev('gridState.cells[0]')
    check('【入力欄】左・右の文字・背景色・文字色が、それぞれ正しい項目に入る', c['leftText'] == 'ア' and c['rightText'] == 'イ' and c['leftColor'] == '#ef4444' and c['rightTextColor'] == '#facc15' and c['singleText'] == '', c)
    check('【入力欄】別のマスを選ぶと、入力欄の中身が入れ替わる', (p.evaluate('selectCell(1)'), p.input_value('#text-left'))[1] == '')
    check('【入力欄】エラーが無い', not a.errors, a.errors)
    a.close()


def t_tabs(br, base):
    a = App(br, base); p = a.open()
    cols = a.ev("getComputedStyle(document.getElementById('tab-bar')).gridTemplateColumns.split(' ').length")
    check('【タブ】車型タブが、TYPES の並びから作られる', a.ev("[...document.querySelectorAll('.tab-btn')].map(b=>b.dataset.type+':'+b.textContent).join()") == 'L4:L4,V6:V6,GD:GD')
    check('【タブ】最初のタブが選択状態で、タブの数だけ列が並ぶ', a.ev("document.querySelector('.tab-btn.active').dataset.type") == 'L4' and cols == 3, cols)
    p.click('.tab-btn[data-type="V6"]')
    check('【タブ】タブを押すと、表示する車型と、選択状態が切り替わる', a.ev('activeType') == 'V6' and a.ev("document.querySelector('.tab-btn.active').dataset.type") == 'V6')
    check('【タブ】エラーが無い', not a.errors, a.errors)
    a.close()


def t_add_type(br, base):
    """車型を、config.js の TYPES に1つ足しただけで、タブ・保存・QR・共有が、すべて対応するか"""
    a = App(br, base); p = a.open()
    check('【車型の追加】タブが4つになり、4列に並ぶ', a.ev("document.querySelectorAll('.tab-btn').length") == 4 and a.ev("getComputedStyle(document.getElementById('tab-bar')).gridTemplateColumns.split(' ').length") == 4)
    check('【車型の追加】新しい車型は、2行3列（[3,3]）で始まる', a.ev('project.sheets.XX.rowCols') == [3, 3])
    p.click('.tab-btn[data-type="XX"]'); p.evaluate('applyRowCols([2])'); p.fill('#text-name', 'XX作業'); p.fill('#text-single', 'アカ'); p.click('#palette-single .color-btn[title="アカ"]')
    check('【車型の追加】新しい車型を、編集できる（行ごとの列数も）', a.ev('activeType') == 'XX' and a.ev('gridState.rowCols') == [2] and a.ev('gridState.cells[0].name') == 'XX作業')
    p.evaluate("selectCell(1)"); p.check('#name-sync'); p.fill('#text-name', '共通')
    check('【車型の追加】作業名の反映が、新しい車型にも届く', a.ev("project.sheets.L4.cells[1].name") == '共通')
    p.fill('#preset-name', 'X'); p.click('text=現在の配置を保存')
    check('【車型の追加】保存に、新しい車型が入る', a.ev("Object.keys(JSON.parse(localStorage.getItem('indicator_presets')).X.sheets).join()") == 'L4,V6,GD,XX')
    p.evaluate("o=>localStorage.setItem('indicator_presets',JSON.stringify({旧:o}))", {'processName': '旧', 'sheets': {t: {'rows': 1, 'cols': 2, 'fontSize': 'text-size-md', 'cells': [{'name': t, 'isSplit': False, 'singleText': '', 'singleColor': '#ffffff'}] * 2} for t in ('L4', 'V6', 'GD')}})
    p.evaluate("applyPreset('旧')")
    check('【車型の追加】3車型のときに保存したデータを読むと、新しい車型は初期値で補われる', a.ev('project.sheets.XX.rowCols') == [3, 3] and a.ev('project.sheets.GD.rowCols') == [2])
    p.click('text=🔗 共有/QR'); p.wait_for_function("document.querySelectorAll('#share-types input').length>0")
    check('【車型の追加】QR共有の選択肢が、4車型になる', a.ev("document.querySelectorAll('#share-types input').length") == 4)
    p.click('#share-modal >> text=閉じる')
    p.click('.tab-btn[data-type="XX"]'); p.fill('#text-name', 'ダケ')
    url = a.ev("buildShareUrl(['XX'])")
    v = App(br, base); vp = v.open(url[url.index('#'):])
    vis = lambda t: v.ev(f"(()=>{{const e=document.querySelector('.tab-btn[data-type=\"{t}\"]');return getComputedStyle(e).display!=='none'}})()")
    check('【車型の追加】QRで受け取ると、新しい車型だけが、閲覧モードで表示される', v.ev('activeType') == 'XX' and v.ev('gridState.cells[0].name') == 'ダケ' and [vis(t) for t in ('L4', 'V6', 'GD', 'XX')] == [False, False, False, True])
    # 3車型だけの旧アプリが作るQR（XXを含まない）も、読める
    old = {'v': 3, 'n': '', 'p': ['ffffff'], 's': {'L4': {'r': [3], 'f': 'au', 'k': [['', 0, '', 0, -1]] * 3}}}
    w = App(br, base); w.open('#d=r' + b64url(json.dumps(old).encode()))
    check('【車型の追加】3車型の頃のQRも、そのまま読める', w.ev('activeType') == 'L4' and w.ev('project.sheets.XX.rowCols') == [3, 3])
    p.click('text=オールクリア')
    check('【車型の追加】オールクリアが、新しい車型にも効く', a.ev("project.sheets.XX.cells.every(c=>!c.name&&!c.singleText&&c.singleColor==='#ffffff')"))
    check('【車型の追加】エラーが無い', not a.errors and not v.errors and not w.errors, (a.errors, v.errors, w.errors))
    v.close(); w.close(); a.close()


def t_offline(br, base, root):
    a = App(br, base); p = a.open()
    p.evaluate('navigator.serviceWorker.ready.then(()=>1)'); p.wait_for_timeout(1500)
    keys = a.ev('caches.keys()')
    sw = (root / 'sw.js').read_text(encoding='utf-8')
    expect = re.findall(r"'\./?([^']*)'", re.search(r'const FILES = \[(.*?)\];', sw, re.S).group(1))
    cached = a.ev("n=>caches.open(n).then(c=>c.keys()).then(r=>r.map(x=>new URL(x.url).pathname))", keys[0]) if keys else []
    missing = [f for f in expect if f and '/' + f not in cached]
    check('【オフライン】Service Worker が、保存一覧の全ファイルを、端末に保存する', keys and not missing, (keys, missing))
    a.ctx.set_offline(True)
    q = a.new_page(); q.goto(f'{base}/index.html'); q.wait_for_timeout(800)
    ok = q.evaluate('typeof renderGrid === "function" && document.querySelectorAll(".cell").length')
    check('【オフライン】電波なしで開き直しても、アプリが動く', ok and ok > 0, ok)
    q.click('text=🔗 共有/QR'); q.wait_for_timeout(500)
    check('【オフライン】電波なしでも、QRが作れる', q.evaluate("getComputedStyle(document.getElementById('qr-canvas')).display") == 'block')
    check('【オフライン】読み込み失敗・エラーが無い', not a.errors, (a.errors, a.bad))
    a.close()


TESTS = [t_initial, t_symbol_controls, t_tabs, t_row_frames, t_colors_and_clear, t_name_sync, t_save_flow, t_mismatch, t_presets_legacy,
         t_qr_roundtrip, t_legacy_qr, t_auto_font, t_selected_style, t_color_settings]


def run(root):
    site = prepare_root(root)
    srv, base = start_server(site)
    try:
        with sync_playwright() as pw:
            br = pw.chromium.launch()
            for t in TESTS:
                try:
                    t(br, base)
                except Exception as e:  # テスト自体が止まった
                    check(f'{t.__name__}（テストが途中で止まった）', False, repr(e)[:300])
            try:
                def add_type(d):
                    cfg = d / 'js' / 'config.js'
                    t = cfg.read_text(encoding='utf-8')
                    assert "const TYPES = ['L4', 'V6', 'GD'];" in t, 'config.js の TYPES の書き方が変わりました（テストを直してください）'
                    cfg.write_text(t.replace("const TYPES = ['L4', 'V6', 'GD'];", "const TYPES = ['L4', 'V6', 'GD', 'XX'];"), encoding='utf-8')
                site2 = prepare_root(root, patch=add_type)
                srv2, base2 = start_server(site2)
                try:
                    t_add_type(br, base2)
                finally:
                    srv2.shutdown(); shutil.rmtree(site2.parent, ignore_errors=True)
            except Exception as e:
                check('t_add_type（テストが途中で止まった）', False, repr(e)[:300])
            try:
                t_offline(br, base, site)
            except Exception as e:
                check('t_offline（テストが途中で止まった）', False, repr(e)[:300])
            br.close()
    finally:
        srv.shutdown()
        shutil.rmtree(site.parent, ignore_errors=True)
    return RESULTS


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default=str(DEFAULT_ROOT))
    args = ap.parse_args()
    res = run(pathlib.Path(args.root))
    fails = [r for r in res if not r[1]]
    for name, ok, detail in res:
        print(('  OK  ' if ok else '  NG  ') + name + ('' if ok else f'\n        → {detail}'))
    print(f'動作テスト: {len(res) - len(fails)}/{len(res)} 件が成功')
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
