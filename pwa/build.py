# -*- coding: utf-8 -*-
"""把 ../公众号快速排版工具.html 构建成可安装的 PWA 站点。

源文件保持"单文件、双击即用、离线可用"的形态不变；
本脚本生成 pwa/ 目录下的部署产物：index.html、manifest.webmanifest、sw.js。

为什么要传 sharecode：
  workbuddy.host 的分享链接靠 ?sharecode= 鉴权，且浏览器在获取
  <link rel=manifest> 时按规范不发送 Cookie。若清单 / 图标 / start_url
  的 URL 不带 sharecode，浏览器会拿到 403，安装资格检查直接失败
  （表现为菜单里的"将此站点作为应用安装"永远灰着）。
  所以这里把所有资源 URL 都拼上 sharecode，完全不依赖 Cookie。

用法：
  python build.py --sharecode HJS3ZX5ZE6
  python build.py                 # 本地调试，不带 sharecode
"""
import argparse
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC_CANDIDATES = ['wechat-formatter.html', '公众号快速排版工具.html']
OUT_HTML = os.path.join(HERE, 'index.html')
OUT_MANIFEST = os.path.join(HERE, 'manifest.webmanifest')
OUT_SW = os.path.join(HERE, 'sw.js')


def find_src():
    """主程序文件名在本地项目与开源仓库里可能不同，按候选顺序查找。"""
    for name in SRC_CANDIDATES:
        p = os.path.join(HERE, '..', name)
        if os.path.exists(p):
            return p
    sys.exit('找不到主程序文件（尝试过：%s）' % '、'.join(SRC_CANDIDATES))

APP_NAME = '公众号快速排版工具'
SHORT_NAME = '公众号排版'
DESC = '把 HTML 或 Markdown 转成公众号可直接粘贴的富文本，保留原有排版。'
THEME = '#0b6e75'
BG = '#f4f5f7'


def q(sharecode):
    """给资源 URL 追加鉴权参数。"""
    return ('?sharecode=' + sharecode) if sharecode else ''


def build_manifest(sharecode):
    s = q(sharecode)
    data = {
        'name': APP_NAME,
        'short_name': SHORT_NAME,
        'description': DESC,
        'id': './',
        'start_url': './index.html' + s,
        'scope': './',
        'display': 'standalone',
        'display_override': ['standalone', 'browser'],
        'orientation': 'any',
        'background_color': BG,
        'theme_color': THEME,
        'lang': 'zh-CN',
        'dir': 'ltr',
        'categories': ['productivity', 'utilities'],
        'icons': [
            {'src': 'icon-192.png' + s, 'sizes': '192x192', 'type': 'image/png', 'purpose': 'any'},
            {'src': 'icon-512.png' + s, 'sizes': '512x512', 'type': 'image/png', 'purpose': 'any'},
            {'src': 'icon-maskable-512.png' + s, 'sizes': '512x512', 'type': 'image/png', 'purpose': 'maskable'},
        ],
        'shortcuts': [
            {'name': '打开排版工具', 'url': './index.html' + s},
        ],
    }
    return json.dumps(data, ensure_ascii=False, indent=2) + '\n'


def build_sw(sharecode):
    s = q(sharecode)
    return """/* 公众号快速排版工具 - Service Worker
   纯离线工具，自身只有这几个文件，全部预缓存。
   注意：资源 URL 带 sharecode（见 build.py 注释），缓存键因此也带 query，
   匹配时用 ignoreSearch 兼容。 */
const CACHE = 'wechat-formatter-v2';
const ASSETS = [
  './index.html%(s)s',
  './manifest.webmanifest%(s)s',
  './icon-192.png%(s)s',
  './icon-512.png%(s)s',
  './icon-maskable-512.png%(s)s',
  './apple-touch-icon.png%(s)s'
];

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE)
      // 单个资源失败不影响整站可用（线上缺一个图标也要能装）
      .then((c) => Promise.all(ASSETS.map((u) => c.add(u).catch(() => null))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;
  if (new URL(req.url).origin !== self.location.origin) return;

  e.respondWith(
    caches.match(req, { ignoreSearch: true }).then((hit) => {
      if (hit) {
        // 后台拉新版写回缓存，用户无感；下次打开即生效
        fetch(req).then((res) => {
          if (res && res.ok) caches.open(CACHE).then((c) => c.put(req, res.clone()));
        }).catch(() => {});
        return hit;
      }
      return fetch(req).then((res) => {
        if (res && res.ok) {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(req, copy));
        }
        return res;
      }).catch(() => caches.match('./index.html', { ignoreSearch: true }));
    })
  );
});
""" % {'s': s}


def build_html(sharecode):
    with io.open(find_src(), encoding='utf-8') as f:
        html = f.read()

    s = q(sharecode)

    # 幂等：剥掉上一次注入的内容
    html = re.sub(r'<link rel="manifest".*?<link rel="apple-touch-icon"[^>]*>\n?', '', html, flags=re.S)
    html = re.sub(r'\n<!-- PWA：安装入口.*?\n</script>\n', '\n', html, flags=re.S)

    if '<title>' not in html or '</body>' not in html:
        sys.exit('源文件结构异常，找不到 <title> 或 </body>')

    head = """<link rel="manifest" href="./manifest.webmanifest%(s)s">
<meta name="theme-color" content="%(theme)s">
<meta name="application-name" content="%(short)s">
<meta name="apple-mobile-web-app-title" content="%(short)s">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="mobile-web-app-capable" content="yes">
<link rel="icon" type="image/png" sizes="192x192" href="./icon-192.png%(s)s">
<link rel="apple-touch-icon" href="./apple-touch-icon.png%(s)s">""" % {
        's': s, 'theme': THEME, 'short': SHORT_NAME
    }

    tail = """
<!-- PWA：安装入口 + Service Worker 注册（仅部署版注入） -->
<div id="pwaInstall" style="display:none;position:fixed;right:18px;bottom:52px;z-index:99;">
  <button id="pwaInstallBtn" type="button" style="display:flex;align-items:center;gap:8px;border:0;
    border-radius:999px;padding:11px 18px;background:%(theme)s;color:#fff;font-size:13px;font-weight:600;
    font-family:inherit;cursor:pointer;box-shadow:0 6px 18px rgba(11,110,117,.28);">
    <span style="font-size:15px;line-height:1;">＋</span>安装到桌面
  </button>
</div>
<script>
(function () {
  if (window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true) return;

  var box = document.getElementById('pwaInstall');
  var btn = document.getElementById('pwaInstallBtn');
  var deferred = null;

  window.addEventListener('beforeinstallprompt', function (e) {
    e.preventDefault();          // 不自动弹，交给按钮
    deferred = e;
    box.style.display = 'block';
  });

  btn.addEventListener('click', function () {
    if (!deferred) return;
    deferred.prompt();
    deferred.userChoice.then(function () {
      deferred = null;
      box.style.display = 'none';
    });
  });

  window.addEventListener('appinstalled', function () {
    box.style.display = 'none';
  });

  if ('serviceWorker' in navigator) {
    window.addEventListener('load', function () {
      navigator.serviceWorker.register('./sw.js%(s)s', { scope: './' })
        .catch(function (err) { console.warn('[PWA] SW 注册失败：', err); });
    });
  }
})();
</script>
""" % {'theme': THEME, 's': s}

    html = html.replace('</title>', '</title>\n' + head, 1)
    idx = html.rfind('</body>')
    html = html[:idx] + tail + html[idx:]
    return html


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sharecode', default=os.environ.get('PWA_SHARECODE', ''),
                    help='部署分享码，用于给 manifest/图标/start_url 追加 ?sharecode=')
    args = ap.parse_args()
    sc = args.sharecode.strip()

    html = build_html(sc)
    with io.open(OUT_HTML, 'w', encoding='utf-8', newline='\n') as f:
        f.write(html)
    with io.open(OUT_MANIFEST, 'w', encoding='utf-8', newline='\n') as f:
        f.write(build_manifest(sc))
    with io.open(OUT_SW, 'w', encoding='utf-8', newline='\n') as f:
        f.write(build_sw(sc))

    print('sharecode:', sc or '(none)')
    for p in (OUT_HTML, OUT_MANIFEST, OUT_SW):
        print('  %-24s %6.1f KB' % (os.path.basename(p), os.path.getsize(p) / 1024))


if __name__ == '__main__':
    main()
