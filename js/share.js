// js/share.js — QR共有の画面（送りたい車型の選択・QRを描く）
// （指示ビラ・レイアウトシミュレータ / MIT License）

let qrToken = 0;

function drawQr(text) {
    let qr = null;
    for (const level of ['M', 'L']) {
        try { qr = qrcode(0, level); qr.addData(text); qr.make(); break; } catch (e) { qr = null; }
    }
    if (!qr) return false;

    const canvas = document.getElementById('qr-canvas');
    const n = qr.getModuleCount();
    const quiet = 4;
    const cell = Math.max(3, Math.floor(340 / (n + quiet * 2)));
    const size = (n + quiet * 2) * cell;
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, size, size);
    ctx.fillStyle = '#000000';
    for (let r = 0; r < n; r++) {
        for (let c = 0; c < n; c++) {
            if (qr.isDark(r, c)) ctx.fillRect((c + quiet) * cell, (r + quiet) * cell, cell, cell);
        }
    }
    return true;
}

function openShareModal() {
    const box = document.getElementById('share-types');
    box.innerHTML = '';
    TYPES.forEach(t => {
        const label = document.createElement('label');
        label.className = 'share-check';
        const cb = document.createElement('input');
        cb.type = 'checkbox';
        cb.value = t;
        cb.checked = (t === activeType); // 最初は表示中の車型だけチェック
        cb.onchange = updateQr;
        label.appendChild(cb);
        label.appendChild(document.createTextNode(t));
        box.appendChild(label);
    });
    document.getElementById('share-modal').classList.add('active');
    updateQr();
}

function closeShareModal() {
    document.getElementById('share-modal').classList.remove('active');
}

async function updateQr() {
    const token = ++qrToken;
    const types = Array.from(document.querySelectorAll('#share-types input:checked')).map(x => x.value);
    const msg = document.getElementById('share-msg');
    const canvas = document.getElementById('qr-canvas');
    canvas.style.display = 'none';

    if (!/^https?:$/.test(location.protocol)) {
        msg.textContent = 'QRコードは、GitHub Pagesのアドレスで開いたアプリでだけ作れます。';
        return;
    }
    if (types.length === 0) {
        msg.textContent = '送りたい車型にチェックを入れてください。';
        return;
    }
    const url = await buildShareUrl(types);
    if (token !== qrToken) return; // チェックが切り替わった後の古い結果は捨てる
    if (drawQr(url)) {
        canvas.style.display = 'block';
        msg.textContent = '受け取る人は、スマホのカメラでこのQRコードを読み取ってください。';
    } else {
        msg.textContent = 'データが大きすぎてQRコードにできません。チェックする車型を減らしてください。';
    }
}
