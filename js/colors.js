// js/colors.js — 色の一覧（背景色・指示記号の色）、色ボタン、「色の設定」画面
// （指示ビラ・レイアウトシミュレータ / MIT License）

const cloneColors = list => list.map(c => ({ name: c.name, code: c.code }));

function sanitizeColors(a) {
    if (!Array.isArray(a)) return null;
    const ok = a.filter(c => c && /^#[0-9a-f]{6}$/i.test(c.code))
        .map(c => ({ name: String(c.name || '').slice(0, 6), code: c.code.toLowerCase() }));
    return ok.length ? ok : null;
}

function loadColors() {
    try {
        const o = JSON.parse(localStorage.getItem(COLOR_STORE_KEY) || 'null');
        if (o) return { bg: sanitizeColors(o.bg) || cloneColors(DEFAULT_BG_COLORS), text: sanitizeColors(o.text) || cloneColors(DEFAULT_TEXT_COLORS) };
    } catch (e) {}
    return { bg: cloneColors(DEFAULT_BG_COLORS), text: cloneColors(DEFAULT_TEXT_COLORS) };
}

function saveColors() {
    try { localStorage.setItem(COLOR_STORE_KEY, JSON.stringify({ bg: COLOR_PRESETS, text: TEXT_COLORS })); } catch (e) {}
}

const savedColors = loadColors();

const COLOR_PRESETS = savedColors.bg;   // 背景色の一覧

const TEXT_COLORS = savedColors.text;   // 指示記号の色の一覧

// 背景が黒のときは、文字を白にする
// 指示記号の文字色：指定があればその色。「自動」のときは、背景がとても暗い色なら白、それ以外は標準の暗い色
function textColorFor(bg, textColor) {
    if (textColor) return textColor;
    return luminance(bg) < 0.15 ? '#ffffff' : '';
}


// 色の明るさ（0＝真っ暗〜1＝真っ白）
function luminance(hex) {
    const m = /^#?([0-9a-f]{6})$/i.exec(String(hex));
    if (!m) return 1;
    const v = [0, 2, 4].map(k => {
        const c = parseInt(m[1].substr(k, 2), 16) / 255;
        return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
    });
    return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2];
}

// カラーパレットボタンの生成
function renderColorPalettes() {
    const setter = key => color => {
        gridState.cells[selectedCellIndex][key] = color;
        updateCellData();
    };
    SYMBOL_FIELDS.forEach(f => {
        createPalette(`palette-${f.key}`, setter(`${f.key}Color`), COLOR_PRESETS);
        createPalette(`palette-${f.key}-text`, setter(`${f.key}TextColor`), TEXT_COLORS, true);
    });
}

// 選んでいるマスの色を、色ボタンの選択状態に反映する
function syncPalettes(data) {
    SYMBOL_FIELDS.forEach(f => {
        updatePaletteSelection(`palette-${f.key}`, data[`${f.key}Color`]);
        updatePaletteSelection(`palette-${f.key}-text`, data[`${f.key}TextColor`] || '');
    });
}

// --- 色の設定（色の追加・削除・変更） ---
function refreshPalettes() {
    renderColorPalettes();
    syncPalettes(gridState.cells[selectedCellIndex]);
}

function openColorModal() {
    renderColorList();
    document.getElementById('color-modal').classList.add('active');
}

function closeColorModal() {
    document.getElementById('color-modal').classList.remove('active');
}

function renderColorList() {
    renderColorSection('color-list-bg', COLOR_PRESETS);
    renderColorSection('color-list-text', TEXT_COLORS);
}

function renderColorSection(boxId, list) {
    const box = document.getElementById(boxId);
    box.innerHTML = '';
    list.forEach((c, i) => {
        const row = document.createElement('div');
        row.className = 'color-row';

        const picker = document.createElement('input');
        picker.type = 'color';
        picker.value = c.code;
        picker.oninput = () => { c.code = picker.value.toLowerCase(); saveColors(); refreshPalettes(); };

        const name = document.createElement('input');
        name.type = 'text';
        name.className = 'input-text';
        name.maxLength = 6;
        name.value = c.name;
        name.placeholder = '色の名前';
        name.oninput = () => { c.name = name.value; saveColors(); refreshPalettes(); };

        const del = document.createElement('button');
        del.className = 'btn btn-danger';
        del.textContent = '✕';
        del.onclick = () => deleteColor(list, i);

        row.appendChild(picker);
        row.appendChild(name);
        row.appendChild(del);
        box.appendChild(row);
    });
}

function addColor(which) {
    const list = which === 'text' ? TEXT_COLORS : COLOR_PRESETS;
    if (list.length >= MAX_COLORS) {
        alert(`色は最大${MAX_COLORS}色までです。`);
        return;
    }
    list.push({ name: '新色', code: '#888888' });
    saveColors();
    renderColorList();
    refreshPalettes();
}

function deleteColor(list, i) {
    if (list.length <= 1) {
        alert('色は1つ以上必要です。');
        return;
    }
    if (!confirm(`「${list[i].name}」を削除しますか？\n（すでに塗ったマスの色は、そのまま残ります）`)) return;
    list.splice(i, 1);
    saveColors();
    renderColorList();
    refreshPalettes();
}

function resetColors() {
    if (!confirm('背景色と指示記号の色の一覧を、最初の色に戻しますか？\n（すでに塗ったマスの色は、そのまま残ります）')) return;
    COLOR_PRESETS.splice(0, COLOR_PRESETS.length, ...cloneColors(DEFAULT_BG_COLORS));
    TEXT_COLORS.splice(0, TEXT_COLORS.length, ...cloneColors(DEFAULT_TEXT_COLORS));
    saveColors();
    renderColorList();
    refreshPalettes();
}

function createPalette(containerId, onSelectColor, list, withAuto) {
    const container = document.getElementById(containerId);
    container.innerHTML = '';
    const make = (label, code, bg) => {
        const btn = document.createElement('button');
        btn.className = 'color-btn';
        btn.dataset.color = code;
        btn.title = label;
        btn.style.backgroundColor = bg || '#f3f4f6';
        btn.style.color = bg ? (luminance(bg) < 0.4 ? '#ffffff' : '#000000') : '#374151';
        btn.textContent = label;
        btn.onclick = () => {
            onSelectColor(code);
            updatePaletteSelection(containerId, code);
        };
        container.appendChild(btn);
    };
    if (withAuto) make('自動', '', null);
    list.forEach(c => make(c.name, c.code, c.code));
}

function updatePaletteSelection(containerId, activeColor) {
    const active = String(activeColor || '').toLowerCase();
    document.querySelectorAll(`#${containerId} .color-btn`).forEach(btn => {
        btn.classList.toggle('active', (btn.dataset.color || '').toLowerCase() === active);
    });
}


