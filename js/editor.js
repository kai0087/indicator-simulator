// js/editor.js — マスの編集（選ぶ・入力を反映・分割・作業名・クリア・オールクリア）と工程名
// （指示ビラ・レイアウトシミュレータ / MIT License）

// --- 工程名・オールクリア・指示記号のクリア ---
function onProcessNameInput() {
    project.processName = document.getElementById('process-name').value;
}

function syncProcessNameInput() {
    document.getElementById('process-name').value = project.processName || '';
}

// 指示記号のクリア：文字・背景色・指示記号の色を、最初の状態に戻す
function clearSymbol(field) {
    const map = {
        single: ['text-single', 'singleColor', 'singleTextColor'],
        left: ['text-left', 'leftColor', 'leftTextColor'],
        right: ['text-right', 'rightColor', 'rightTextColor']
    };
    const [inputId, bgKey, tcKey] = map[field];
    document.getElementById(inputId).value = '';
    const cell = gridState.cells[selectedCellIndex];
    cell[bgKey] = '#ffffff';
    cell[tcKey] = '';
    updateCellData();
    syncPalettes(cell);
}

// 全タブの、工程名・作業名・指示記号を消す（背景色とマスの数は、そのまま）
// 全タブの、工程名・作業名・指示記号（文字・背景色・指示記号の色）を消す。マスの数と分割は、そのまま
function allClear() {
    if (!confirm('全てのタブ（L4・V6・GD）の、工程名・作業名・指示記号（背景色を含む）をすべて消します。よろしいですか？\n（マスの数と、左右の分割は、そのままです）')) return;
    project.processName = '';
    TYPES.forEach(t => project.sheets[t].cells.forEach(c => {
        c.name = '';
        c.singleText = '';
        c.singleColor = '#ffffff';
        c.singleTextColor = '';
        c.leftText = '';
        c.leftColor = '#ffffff';
        c.leftTextColor = '';
        c.rightText = '';
        c.rightColor = '#ffffff';
        c.rightTextColor = '';
    }));
    syncProcessNameInput();
    renderGrid();
    selectCell(selectedCellIndex);
}

// セルの選択処理
function selectCell(index) {
    if (index < 0 || index >= gridState.cells.length) index = 0;
    selectedCellIndex = index;

    // 選択枠表示の更新
    const cells = document.querySelectorAll('.cell');
    cells.forEach((c, idx) => {
        if (idx === index) c.classList.add('selected');
        else c.classList.remove('selected');
    });

    // ラベル表示設定
    const rc = rcOf(gridState, index);
    document.getElementById('target-cell-label').textContent = `${rc.r + 1}行 - ${rc.c + 1}列目`;

    // 編集パネルへデータを反映
    const data = gridState.cells[index];
    setSplitUI(data.isSplit);

    document.getElementById('text-name').value = data.name || '';
    document.getElementById('name-sync').checked = false;
    document.getElementById('text-single').value = data.singleText;
    document.getElementById('text-left').value = data.leftText;
    document.getElementById('text-right').value = data.rightText;

    syncPalettes(data);
}

// 分割UIの切り替え
function setSplitMode(isSplit) {
    gridState.cells[selectedCellIndex].isSplit = isSplit;
    setSplitUI(isSplit);
    renderGrid();
}

function setSplitUI(isSplit) {
    const btnNone = document.getElementById('split-none-btn');
    const btnLR = document.getElementById('split-lr-btn');
    const singleCtrl = document.getElementById('single-controls');
    const splitCtrl = document.getElementById('split-controls');

    if (!isSplit) {
        btnNone.classList.add('active');
        btnLR.classList.remove('active');
        singleCtrl.style.display = 'block';
        splitCtrl.style.display = 'none';
    } else {
        btnNone.classList.remove('active');
        btnLR.classList.add('active');
        singleCtrl.style.display = 'none';
        splitCtrl.style.display = 'block';
    }
}

// 入力フォームの内容をグリッド状態へ反映
function updateCellData() {
    const data = gridState.cells[selectedCellIndex];
    data.name = document.getElementById('text-name').value;
    data.singleText = document.getElementById('text-single').value;
    data.leftText = document.getElementById('text-left').value;
    data.rightText = document.getElementById('text-right').value;
    renderGrid();
}

// --- 作業名：クリアと、他の車型への反映 ---
function onNameInput() {
    updateCellData();
    syncNameToOthers();
}

function clearName() {
    document.getElementById('text-name').value = '';
    onNameInput();
}

// チェックが入っているとき、他の車型の「同じ行・同じ列」のマスにも作業名を反映する
// （相手の行・列が足りないときは、その車型だけ何もしない）
// チェックが入っているとき、他の車型の「同じ行・同じ列」のマスにも作業名を反映する
// （相手にその行・列がないときは、その車型だけ何もしない）
function syncNameToOthers() {
    if (!document.getElementById('name-sync').checked) return;
    const name = gridState.cells[selectedCellIndex].name;
    const rc = rcOf(gridState, selectedCellIndex);
    TYPES.forEach(t => {
        if (t === activeType) return;
        const sheet = project.sheets[t];
        const i = indexOfRC(sheet, rc.r, rc.c);
        if (i >= 0) sheet.cells[i].name = name;
    });
}
