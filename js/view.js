// js/view.js — QRを読み取った側：データの復元と、閲覧モード
// （指示ビラ・レイアウトシミュレータ / MIT License）

// 閲覧モード：受け取った車型のタブだけを出し、指示ビラ以外の画面を隠す
// 閲覧モード：受け取った車型のタブだけを出し、指示ビラ以外の画面を隠す
function enterViewMode(types) {
    document.body.classList.add('view-mode');
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('hidden', !types.includes(b.dataset.type)));
    document.getElementById('view-process').textContent = project.processName || '受け取った指示ビラ';
    switchTab(types[0]);
}

// 「編集画面を開く」：通常の画面に戻す（読み取ったデータはそのまま編集できる）
function exitViewMode() {
    document.body.classList.remove('view-mode');
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('hidden'));
    history.replaceState(null, '', location.pathname + location.search);
    syncProcessNameInput();
}

// QRを読み取って開いたとき、アドレスの後ろのデータからレイアウトを復元する
async function loadFromUrlHash() {
    if (!location.hash.startsWith('#d=')) return;
    try {
        const str = location.hash.slice(3);
        let bytes = b64urlDec(str.slice(1));
        if (str[0] === 'z') bytes = await runStream(DecompressionStream, bytes);
        const data = JSON.parse(new TextDecoder().decode(bytes));
        if (!(data.v >= 1 && data.v <= FORMAT_VERSION) || !data.s) throw new Error('version');

        // 形式3以降は、QRの中の色コード一覧を使う。形式1・2は、昔の色番号の表を使う
        const colorOf = data.v >= 3
            ? (i => { const h = String((data.p || [])[i] || ''); return /^[0-9a-f]{6}$/i.test(h) ? '#' + h.toLowerCase() : '#ffffff'; })
            : (i => LEGACY_COLORS[i] || '#ffffff');
        const got = [];
        TYPES.forEach(t => {
            if (data.s[t]) {
                project.sheets[t] = compactToSheet(data.s[t], colorOf, data.v);
                got.push(t);
            }
        });
        if (got.length === 0) throw new Error('empty');

        project.processName = String(data.n || '').slice(0, 60);
        syncProcessNameInput();
        enterViewMode(got);
    } catch (e) {
        alert('QRコードのデータを読み込めませんでした。アプリが古い可能性があります。最新のアプリで開き直してください。');
    }
}
