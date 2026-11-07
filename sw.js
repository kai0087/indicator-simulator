// ===== 更新するときは、下の VERSION の数字を上げてから置き換える =====
const VERSION = 'v1.1.1';
const CACHE_NAME = 'indicator-simulator-' + VERSION;
const FILES = [
  './',
  './index.html',
  './manifest.webmanifest',
  './icon-192.png',
  './icon-512.png',
  './apple-touch-icon.png'
];

// インストール時：必要なファイルを端末に保存
self.addEventListener('install', function (event) {
  event.waitUntil(
    caches.open(CACHE_NAME).then(function (cache) { return cache.addAll(FILES); })
  );
  self.skipWaiting();
});

// 有効化時：古いバージョンの保存データを削除
self.addEventListener('activate', function (event) {
  event.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(
        keys.filter(function (k) { return k !== CACHE_NAME; })
            .map(function (k) { return caches.delete(k); })
      );
    }).then(function () { return self.clients.claim(); })
  );
});

// 通信時：まず端末の保存分を即表示 → 裏で最新版を取得して保存（電波が弱くても待たされない）
self.addEventListener('fetch', function (event) {
  if (event.request.method !== 'GET') return;
  event.respondWith(
    caches.match(event.request).then(function (cached) {
      var network = fetch(event.request).then(function (res) {
        if (res && res.ok && new URL(event.request.url).origin === self.location.origin) {
          var copy = res.clone();
          caches.open(CACHE_NAME).then(function (cache) { cache.put(event.request, copy); });
        }
        return res;
      }).catch(function () { return cached; });
      return cached || network;
    })
  );
});
