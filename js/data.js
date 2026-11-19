// js/data.js — データの形（1マス・1枚・1工程）と、マス番号⇔（行,列）の変換
// （指示ビラ・レイアウトシミュレータ / MIT License）

function newCell() {
    const cell = { name: '', isSplit: false };
    SYMBOL_FIELDS.forEach(f => {
        cell[`${f.key}Text`] = '';
        cell[`${f.key}Color`] = '#ffffff';
        cell[`${f.key}TextColor`] = '';
    });
    return cell;
}

// rowCols：行ごとの列数（例 [3, 1]＝1行目3列・2行目1列）
function newSheet(rowCols) {
    const total = rowCols.reduce((a, b) => a + b, 0);
    return { rows: rowCols.length, rowCols: rowCols.slice(), fontSize: 'text-size-auto', cells: Array.from({ length: total }, newCell) };
}

// 車型ごとの、行ごとの列数の初期値（config.js に無い車型は、2行3列）
function defaultRowCols(type) {
    return DEFAULT_ROWCOLS[type] || [3, 3];
}

function createProject() {
    const sheets = {};
    TYPES.forEach(t => { sheets[t] = newSheet(defaultRowCols(t)); });
    return { processName: '', sheets: sheets };
}

// 旧形式（行数×列数が全行同じ）のシートを、行ごとの列数の形に直す
function normalizeSheet(sheet) {
    if (!Array.isArray(sheet.rowCols)) sheet.rowCols = Array.from({ length: sheet.rows }, () => sheet.cols);
    sheet.rows = sheet.rowCols.length;
    sheet.fontSize = 'text-size-auto'; // 文字サイズは「自動」だけ（旧データの小・中・大も自動にする）
    delete sheet.cols;
    return sheet;
}

function normalizeProject(proj) {
    proj.processName = String(proj.processName || '');
    TYPES.forEach(t => { proj.sheets[t] = proj.sheets[t] ? normalizeSheet(proj.sheets[t]) : newSheet(defaultRowCols(t)); });
}

// マス番号 ⇔ （行, 列）の変換（どちらも0始まり）
function rcOf(sheet, index) {
    let r = 0;
    while (r < sheet.rowCols.length - 1 && index >= sheet.rowCols[r]) { index -= sheet.rowCols[r]; r++; }
    return { r: r, c: index };
}

function indexOfRC(sheet, r, c) {
    if (r >= sheet.rows || c >= sheet.rowCols[r]) return -1;
    let idx = 0;
    for (let i = 0; i < r; i++) idx += sheet.rowCols[i];
    return idx + c;
}
