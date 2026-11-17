// js/config.js — 定数（上限・初期の色・形式の番号など）。ここを直すと、アプリ全体の標準値が変わります
// （指示ビラ・レイアウトシミュレータ / MIT License）

// 定数定義：カラーパレット設定
// 色の一覧の「最初の色」。アプリの「色の設定」で、追加・削除・変更ができる（端末に保存される）
const DEFAULT_BG_COLORS = [
    { name: 'シロ', code: '#ffffff' },
    { name: 'クロ', code: '#111827' },
    { name: 'アカ', code: '#ef4444' },
    { name: 'アオ', code: '#3b82f6' },
    { name: 'ミド', code: '#10b981' }
];

const DEFAULT_TEXT_COLORS = [ // 「自動」は、これとは別に常に先頭に出る
    { name: 'アカ', code: '#ef4444' },
    { name: 'アオ', code: '#3b82f6' },
    { name: 'ミド', code: '#10b981' },
    { name: 'キイ', code: '#facc15' }
];

// QR形式1・2（古いQR）が使っていた色番号の表。読み込み専用で、変更しない
const LEGACY_COLORS = ['#ffffff', '#ef4444', '#3b82f6', '#10b981', '#facc15', '#f97316', '#a855f7', '#ec4899', '#6b7280', '#111827'];

const COLOR_STORE_KEY = 'indicator_colors_v2'; // v1.3.0までの保存（indicator_colors）は使わない

const MAX_COLORS = 20;

const MAX_ROWS = 3;  // 行の選択肢の上限

const MAX_COLS = 5;  // 列の選択肢の上限

const AUTO_FIT_RATIO = 60; // 指示記号の文字サイズ：マスの何%に収めるか

// 車型と、1工程ぶんのデータ（L4・V6・GDの3枚）
const TYPES = ['L4', 'V6', 'GD'];

const DEFAULT_ROWCOLS = { L4: [3, 3], V6: [3, 3], GD: [3, 3] }; // 行ごとの列数（[3, 3]＝2行3列）。最初の値で、いつでも変更可

// --- QRコード共有（送りたい車型だけ選んで、本物のQRコードにする） ---
const FORMAT_VERSION = 3; // 3：色を色コードで送る・指示記号の色を追加（1・2の古いQRも読み込める）
