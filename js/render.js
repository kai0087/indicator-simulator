// js/render.js — ビラを画面に描く（行の枠・マス・指示記号の文字）
// （指示ビラ・レイアウトシミュレータ / MIT License）

// 文字の横幅の目安（全角＝1、半角英数＝0.65）。「自動」の文字サイズの計算に使う
function emWidth(text) {
    let w = 0;
    for (const ch of String(text)) {
        const c = ch.codePointAt(0);
        w += c <= 0x7e ? 0.65 : (c >= 0xff61 && c <= 0xff9f ? 0.5 : 1);
    }
    return Math.max(w, 0.65);
}

function makeSym(text) {
    const span = document.createElement('span');
    span.className = 'sym';
    span.style.setProperty('--em', emWidth(text));
    span.textContent = text;
    return span;
}

// グリッド描画
function renderGrid() {
    const gridEl = document.getElementById('sheet-grid');
    const maxCols = Math.max(...gridState.rowCols);
    gridEl.style.gridTemplateRows = `repeat(${gridState.rows}, 1fr)`;
    gridEl.style.gridTemplateColumns = '1fr';
    gridEl.style.setProperty('--fit', AUTO_FIT_RATIO / 100);
    gridEl.classList.toggle('single-row', gridState.rows === 1);
    gridEl.innerHTML = '';

    let index = 0;
    gridState.rowCols.forEach(n => {
        // 行ごとに、独自の枠を持つ。幅は「その行の列数 ÷ 最大列数」で、マス1つの幅は全行で同じ
        const rowEl = document.createElement('div');
        rowEl.className = 'sheet-row';
        rowEl.style.setProperty('--n', n);
        rowEl.style.setProperty('--maxc', maxCols);
        rowEl.style.gridTemplateColumns = `repeat(${n}, 1fr)`;
        for (let c = 0; c < n; c++, index++) {
            rowEl.appendChild(buildCell(gridState.cells[index], index));
        }
        gridEl.appendChild(rowEl);
    });
}

function buildCell(cellData, index) {
    const cellEl = document.createElement('div');
    cellEl.className = `cell ${index === selectedCellIndex ? 'selected' : ''}`;
    cellEl.onclick = () => selectCell(index);

    // 上部1/5：作業名、下部4/5：指示記号と背景色
    const nameEl = document.createElement('div');
    nameEl.className = 'cell-name';
    const nameTextEl = document.createElement('span');
    nameTextEl.className = 'cell-name-text';
    nameTextEl.textContent = cellData.name || '';
    nameEl.appendChild(nameTextEl);
    const bodyEl = document.createElement('div');
    bodyEl.className = 'cell-body';

    // 背景色・指示記号の文字・文字色を設定した1区画を作る
    const makeBox = (cls, text, bg, textColor) => {
        const box = document.createElement('div');
        box.className = `${cls} ${gridState.fontSize} ${getTextColorClass(bg)}`;
        box.style.backgroundColor = bg;
        box.style.color = textColorFor(bg, textColor);
        box.appendChild(makeSym(text));
        return box;
    };

    if (!cellData.isSplit) {
        bodyEl.appendChild(makeBox('cell-single', cellData.singleText, cellData.singleColor, cellData.singleTextColor));
    } else {
        const splitEl = document.createElement('div');
        splitEl.className = 'cell-split';
        splitEl.appendChild(makeBox('cell-left', cellData.leftText, cellData.leftColor, cellData.leftTextColor));
        splitEl.appendChild(makeBox('cell-right', cellData.rightText, cellData.rightColor, cellData.rightTextColor));
        bodyEl.appendChild(splitEl);
    }

    cellEl.appendChild(nameEl);
    cellEl.appendChild(bodyEl);
    return cellEl;
}
