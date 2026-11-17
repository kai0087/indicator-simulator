// js/layout.js — 車型タブの切り替えと、行・列の設定
// （指示ビラ・レイアウトシミュレータ / MIT License）

// セレクトボックスの選択肢（1~10）を動的生成
// 行は1〜MAX_ROWS、列（全行まとめて）は「行ごと」と1〜MAX_COLS
function initSelectOptions() {
    const rowsSelect = document.getElementById('rows-select');
    const colsSelect = document.getElementById('cols-select');
    const blank = document.createElement('option');
    blank.value = '';
    blank.textContent = '行ごと';
    colsSelect.appendChild(blank);

    for (let i = 1; i <= MAX_ROWS; i++) {
        const optR = document.createElement('option');
        optR.value = i;
        optR.textContent = `${i} 行`;
        rowsSelect.appendChild(optR);
    }
    for (let i = 1; i <= MAX_COLS; i++) {
        const optC = document.createElement('option');
        optC.value = i;
        optC.textContent = `${i} 列`;
        colsSelect.appendChild(optC);
    }
}

// 上限を超える古いデータを開いたときも、その値が選択欄に出るようにする
function ensureOption(sel, v, label) {
    if (![...sel.options].some(o => o.value === String(v))) {
        const o = document.createElement('option');
        o.value = v;
        o.textContent = label;
        sel.appendChild(o);
    }
}

// 行・列・文字サイズの選択欄を、表示中の1枚に合わせる
// 行・列・文字サイズの選択欄を、表示中の1枚に合わせる
// 行・列の選択欄を、表示中の1枚に合わせる
function syncControls() {
    const rowsSel = document.getElementById('rows-select');
    const colsSel = document.getElementById('cols-select');
    ensureOption(rowsSel, gridState.rows, `${gridState.rows} 行`);
    rowsSel.value = gridState.rows;
    const same = gridState.rowCols.every(n => n === gridState.rowCols[0]);
    if (same) ensureOption(colsSel, gridState.rowCols[0], `${gridState.rowCols[0]} 列`);
    colsSel.value = same ? gridState.rowCols[0] : '';
    renderRowColsEditor();
}

// 「1行目 3列」「2行目 1列」…の、行ごとの列数の選択欄
function renderRowColsEditor() {
    const box = document.getElementById('row-cols-editor');
    box.innerHTML = '';
    gridState.rowCols.forEach((n, r) => {
        const label = document.createElement('label');
        label.className = 'row-col-item';
        label.appendChild(document.createTextNode(`${r + 1}行目`));
        const sel = document.createElement('select');
        for (let i = 1; i <= Math.max(MAX_COLS, n); i++) {
            const o = document.createElement('option');
            o.value = i;
            o.textContent = `${i} 列`;
            if (i === n) o.selected = true;
            sel.appendChild(o);
        }
        sel.onchange = () => changeRowCols(r, parseInt(sel.value));
        label.appendChild(sel);
        box.appendChild(label);
    });
}

// 車型タブの切り替え
function switchTab(type) {
    activeType = type;
    gridState = project.sheets[type];
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('active', b.dataset.type === type));
    syncControls();
    selectedCellIndex = 0;
    renderGrid();
    selectCell(0);
}

// 行・列の変更処理
// 新しい「行ごとの列数」に合わせてマスを作り直す。同じ（行, 列）にある入力済みのマスは残す
function applyRowCols(newRowCols) {
    const newCells = [];
    newRowCols.forEach((n, r) => {
        for (let c = 0; c < n; c++) {
            const oi = indexOfRC(gridState, r, c);
            newCells.push(oi >= 0 ? gridState.cells[oi] : newCell());
        }
    });
    gridState.rowCols = newRowCols;
    gridState.rows = newRowCols.length;
    gridState.cells = newCells;
    syncControls();
    selectCell(0);
    renderGrid();
}

// 行数の変更：増えた行は、直前の行と同じ列数にする
function changeRows() {
    const rows = parseInt(document.getElementById('rows-select').value);
    const cur = gridState.rowCols;
    const next = [];
    for (let r = 0; r < rows; r++) next.push(r < cur.length ? cur[r] : cur[cur.length - 1]);
    applyRowCols(next);
}

// 「列 (全行まとめて)」：すべての行を同じ列数にそろえる
function changeAllCols() {
    const v = parseInt(document.getElementById('cols-select').value);
    if (!v) return;
    applyRowCols(gridState.rowCols.map(() => v));
}

// 行ごとの列数の変更（例：2行目だけ1列にする）
function changeRowCols(r, v) {
    const next = gridState.rowCols.slice();
    next[r] = v;
    applyRowCols(next);
}
