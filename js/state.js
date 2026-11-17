// js/state.js — アプリの状態（いま開いている工程・車型・選んでいるマス）
// （指示ビラ・レイアウトシミュレータ / MIT License）

let project = null;      // 1工程ぶん

let activeType = 'L4';   // 表示中の車型

let gridState = null;    // 表示中の1枚（project.sheets[activeType]）

let selectedCellIndex = 0;
