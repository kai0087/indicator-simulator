// js/main.js — 起動（アプリを開いたときの最初の処理と、オフライン用の登録）
// （指示ビラ・レイアウトシミュレータ / MIT License）

// 初期化ロード処理
window.onload = function() {
    document.getElementById('app-version').textContent = 'ver ' + APP_VERSION.split('.').slice(0, 2).join('.');
    initSelectOptions();
    renderTabs();
    buildSymbolControls();
    project = createProject();
    gridState = project.sheets[activeType];
    syncControls();
    renderGrid();
    renderColorPalettes();
    selectCell(0);
    loadPresetList();
    syncProcessNameInput();
    loadFromUrlHash();
};

// オフライン対応（Service Worker）の登録
if ('serviceWorker' in navigator) {
    window.addEventListener('load', function () {
        navigator.serviceWorker.register('./sw.js').catch(function () {});
    });
}
