// js/codec.js — QRに入れるデータの作り方・読み方（短くする・圧縮・復元）
// （指示ビラ・レイアウトシミュレータ / MIT License）

function b64urlEnc(bytes) {
    let bin = '';
    bytes.forEach(b => { bin += String.fromCharCode(b); });
    return btoa(bin).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

function b64urlDec(str) {
    str = str.replace(/-/g, '+').replace(/_/g, '/');
    while (str.length % 4) str += '=';
    return Uint8Array.from(atob(str), ch => ch.charCodeAt(0));
}

// 圧縮・展開（端末が対応しているときだけ使う）
async function runStream(StreamClass, bytes) {
    const st = new StreamClass('deflate-raw');
    const w = st.writable.getWriter();
    w.write(bytes);
    w.close();
    return new Uint8Array(await new Response(st.readable).arrayBuffer());
}

// 1枚ぶんを短い形に直す（QRの容量を節約するため）
// 1枚ぶんを短い形に直す（QRの容量を節約するため）。idx は、色コードを「色の番号」に直す関数
function sheetToCompact(sheet, idx) {
    const sizes = { 'text-size-sm': 'sm', 'text-size-md': 'md', 'text-size-lg': 'lg', 'text-size-auto': 'au' };
    const tc = c => (c ? idx(c) : -1); // 指示記号の色「自動」は -1
    return {
        r: sheet.rowCols.slice(),
        f: sizes[sheet.fontSize] || 'md',
        k: sheet.cells.map(x => x.isSplit
            ? [x.name || '', 1, x.leftText, idx(x.leftColor), tc(x.leftTextColor), x.rightText, idx(x.rightColor), tc(x.rightTextColor)]
            : [x.name || '', 0, x.singleText, idx(x.singleColor), tc(x.singleTextColor)])
    };
}

// 受け取ったデータを検査しながら1枚に戻す（不正なデータは例外にする）
// colorOf：色の番号 → 色コード、ver：QRの形式の番号
function compactToSheet(o, colorOf, ver) {
    // r：行ごとの列数の配列（形式2以降）／ 形式1は r=行数・c=列数
    const rowCols = Array.isArray(o.r) ? o.r.map(Number) : Array.from({ length: Number(o.r) }, () => Number(o.c));
    const total = rowCols.reduce((a, b) => a + b, 0);
    if (!(rowCols.length >= 1 && rowCols.length <= 10 && rowCols.every(n => n >= 1 && n <= 10)) ||
        !Array.isArray(o.k) || o.k.length !== total) {
        throw new Error('invalid');
    }
    const str = (v, n) => String(v == null ? '' : v).slice(0, n);
    const tcOf = i => (Number(i) >= 0 ? colorOf(i) : '');
    const cells = o.k.map(a => {
        const cell = newCell();
        cell.name = str(a[0], 60);
        if (a[1]) {
            cell.isSplit = true;
            cell.leftText = str(a[2], 2);
            cell.leftColor = colorOf(a[3]);
            if (ver >= 3) {
                cell.leftTextColor = tcOf(a[4]);
                cell.rightText = str(a[5], 2);
                cell.rightColor = colorOf(a[6]);
                cell.rightTextColor = tcOf(a[7]);
            } else {
                cell.rightText = str(a[4], 2);
                cell.rightColor = colorOf(a[5]);
            }
        } else {
            cell.singleText = str(a[2], 2);
            cell.singleColor = colorOf(a[3]);
            if (ver >= 3) cell.singleTextColor = tcOf(a[4]);
        }
        return cell;
    });
    return { rows: rowCols.length, rowCols: rowCols, fontSize: 'text-size-auto', cells: cells };
}

// QRに入れるURL（アプリのアドレス + #d=データ）を作る
async function buildShareUrl(types) {
    const pal = []; // 使った色コードの一覧（QRの中で、色を番号で表すため）
    const idx = hex => {
        const h = String(hex).replace('#', '').toLowerCase();
        let i = pal.indexOf(h);
        if (i < 0) { pal.push(h); i = pal.length - 1; }
        return i;
    };
    const data = { v: FORMAT_VERSION, n: String(project.processName || '').slice(0, 60), s: {} };
    types.forEach(t => { data.s[t] = sheetToCompact(project.sheets[t], idx); });
    data.p = pal;
    const raw = new TextEncoder().encode(JSON.stringify(data));
    let best = 'r' + b64urlEnc(raw);
    if (typeof CompressionStream !== 'undefined') {
        try {
            const z = 'z' + b64urlEnc(await runStream(CompressionStream, raw));
            if (z.length < best.length) best = z;
        } catch (e) {}
    }
    return location.href.split('#')[0] + '#d=' + best;
}
