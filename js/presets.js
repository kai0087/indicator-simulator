// js/presets.js — 保存・読込・削除と、保存前の確認（文字と背景色の食い違い）
// （指示ビラ・レイアウトシミュレータ / MIT License）

// --- 保存前の最終チェック（表示文字と背景色の食い違い・全車型） ---
let pendingSaveName = null;

let firstIssue = null;

function findColorMismatches() {
    const issues = [];
    TYPES.forEach(type => {
        const sheet = project.sheets[type];
        sheet.cells.forEach((cell, index) => {
            const rc = rcOf(sheet, index);
            const r = rc.r + 1;
            const c = rc.c + 1;
            const checks = cell.isSplit
                ? [
                    { side: ' 左側', text: cell.leftText, color: cell.leftColor },
                    { side: ' 右側', text: cell.rightText, color: cell.rightColor }
                  ]
                : [{ side: '', text: cell.singleText, color: cell.singleColor }];

            checks.forEach(ch => {
                const text = (ch.text || '').trim();
                const expected = COLOR_PRESETS.find(p => p.name === text);
                if (!expected) return;
                if (expected.code.toLowerCase() === ch.color.toLowerCase()) return;
                const actual = COLOR_PRESETS.find(p => p.code.toLowerCase() === ch.color.toLowerCase());
                issues.push({
                    type: type,
                    index: index,
                    place: `${type} ${r}行-${c}列目${ch.side}`,
                    text: text,
                    actualName: actual ? actual.name : '不明'
                });
            });
        });
    });
    return issues;
}

function showSaveWarn(issues, name) {
    pendingSaveName = name;
    firstIssue = issues[0];

    const list = document.getElementById('warn-list');
    list.innerHTML = '';
    issues.slice(0, 5).forEach(issue => {
        const li = document.createElement('li');
        li.textContent = issue.actualName === 'シロ'
            ? `${issue.place}：「${issue.text}」なのに、背景色が未設定（シロ）です`
            : `${issue.place}：「${issue.text}」なのに、背景色が「${issue.actualName}」です`;
        list.appendChild(li);
    });
    if (issues.length > 5) {
        const more = document.createElement('li');
        more.textContent = `ほか ${issues.length - 5} 件`;
        list.appendChild(more);
    }
    document.getElementById('warn-modal').classList.add('active');
}

// save が true →「このまま保存」 / false →「修正する」
function closeWarnModal(save) {
    document.getElementById('warn-modal').classList.remove('active');
    if (save) {
        if (pendingSaveName) doSavePreset(pendingSaveName);
    } else if (firstIssue) {
        switchTab(firstIssue.type);
        selectCell(firstIssue.index);
        document.getElementById('sheet-grid').scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
    pendingSaveName = null;
}

// --- LocalStorage 保存・読み込み機能 ---

function readPresets() {
    try {
        return JSON.parse(localStorage.getItem('indicator_presets') || '{}');
    } catch (e) {
        return {};
    }
}

function writePresets(presets) {
    try {
        localStorage.setItem('indicator_presets', JSON.stringify(presets));
    } catch (e) {
        alert('この環境では保存ができませんでした。');
    }
}

function savePreset() {
    // 保存名が空なら、工程名を使う。どちらも空なら、入力のポップアップを出す
    const name = document.getElementById('preset-name').value.trim() || (project.processName || '').trim();
    if (!name) {
        document.getElementById('save-name-input').value = '';
        document.getElementById('save-name-msg').textContent = '';
        document.getElementById('save-name-modal').classList.add('active');
        return;
    }
    startSave(name);
}

function closeSaveNameModal(ok) {
    if (!ok) {
        document.getElementById('save-name-modal').classList.remove('active');
        return;
    }
    const v = document.getElementById('save-name-input').value.trim();
    if (!v) {
        document.getElementById('save-name-msg').textContent = '保存名を入力してください。';
        return;
    }
    document.getElementById('save-name-modal').classList.remove('active');
    document.getElementById('preset-name').value = v;
    startSave(v);
}

// 保存前に、文字と背景色が合っているか最終確認してから保存する
function startSave(name) {
    const issues = findColorMismatches();
    if (issues.length > 0) {
        showSaveWarn(issues, name);
        return;
    }
    doSavePreset(name);
}

function doSavePreset(name) {
    const presets = readPresets();
    presets[name] = project;
    writePresets(presets);

    document.getElementById('preset-name').value = '';
    loadPresetList();
    alert(`「${name}」を保存しました。`);
}

function loadPresetList() {
    const listEl = document.getElementById('preset-list');
    listEl.innerHTML = '';
    const presets = readPresets();

    const keys = Object.keys(presets);
    if (keys.length === 0) {
        listEl.innerHTML = '<div style="padding: 10px; font-size: 0.8rem; color: #9ca3af; text-align: center;">保存された設定はありません</div>';
        return;
    }

    keys.forEach(name => {
        const item = document.createElement('div');
        item.className = 'preset-item';
        item.innerHTML = `
                    <span class="preset-item-name" onclick="applyPreset('${name}')">${name}</span>
                    <div class="preset-actions">
                        <button class="btn btn-icon btn-primary" onclick="applyPreset('${name}')">読込</button>
                        <button class="btn btn-icon btn-danger" onclick="deletePreset('${name}')">削除</button>
                    </div>
                `;
        listEl.appendChild(item);
    });
}

function applyPreset(name) {
    const preset = readPresets()[name];
    if (!preset) return;

    if (preset.sheets) {
        project = preset;
    } else {
        // 旧形式（1枚だけ）の保存データは、最初の車型（L4）として読み込む
        project = createProject();
        project.sheets[TYPES[0]] = preset;
    }
    normalizeProject(project);
    syncProcessNameInput();
    switchTab(activeType);
}

function deletePreset(name) {
    if (!confirm(`「${name}」を削除してもよろしいですか？`)) return;
    const presets = readPresets();
    delete presets[name];
    writePresets(presets);
    loadPresetList();
}
