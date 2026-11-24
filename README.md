# 公众号快速排版工具

> 把 Markdown 或 HTML 一键转成公众号编辑器可直接粘贴的富文本，尽量 1:1 还原你原本的排版。
>
> A single-file, offline-capable formatter that converts Markdown/HTML into rich text you can paste straight into the WeChat Official Account editor.

纯前端、零依赖、零后端、不联网上传任何内容。复制粘贴之间完成排版。

---

## 为什么做这个

公众号编辑器不是通用富文本编辑器，它有自己的脾气：它不认 `<style>` 标签和 class，会重写 `figure`、圆角、`object-fit`，会吃掉 `<ol>` 的自动编号，还会让百分比宽度的图片塌缩。

这个工具把这些"坑"提前处理掉，输出的 HTML 是**按公众号编辑器的行为反向适配**过的：

| 公众号的坑 | 这里的处理 |
|---|---|
| 不认 `<style>` / class，只认内联样式 | 用 `DOMParser` 解析源文件，把 CSS 规则逐条匹配到元素上，写成内联 `style` |
| `body` 上的 `line-height` 等继承样式会丢 | 单独抽取 `body/html` 的字体、字号、行高、颜色，套到输出根节点上 |
| `<ol>` / `<ul>` 会被编辑器重新编号，序号变成「1. 1.」 | 连列表外壳一起拆掉，序号用文字写死成 `inline-block` 定宽块 + 悬挂缩进 |
| `<figure>` / `border-radius` / `object-fit` 被重写导致图片裁切 | 图片统一输出为 `section > p > img`，去掉圆角，只保留 1px 边框 |
| 图片百分比宽度被源容器宽度固化 | 复制走 677px 离屏容器，宽度用 `!important` 兜底 |
| 表格列宽平均分配，短标题后面一大片空白 | 按内容估算列宽，首列窄、说明列宽自适应 |
| 折叠列表、勾选框等 `::before` 内容无法内联 | 改用真实 DOM 元素绘制（空心方框用 `border` 画，不靠字符） |

## 快速开始

### 方式一：直接用（推荐，零配置）

下载 [`wechat-formatter.html`](wechat-formatter.html)，双击用浏览器打开即可。**不需要安装、不需要联网、数据不出本机。**

- 顶部下拉切换 `Markdown` / `HTML 原格式` 两种输入模式
- 直接把 `.md` 或 `.html` 文件拖进左侧输入框，自动识别格式
- 右侧实时预览，点「复制富文本」，再到公众号编辑器 `Ctrl+V`

### 方式二：装成桌面应用（PWA）

`pwa/` 目录是完整 PWA 版本，可安装成独立窗口的桌面应用，支持离线打开。

```bash
cd pwa
python make_icons.py                   # 生成图标（纯标准库，无需装 Pillow）
python build.py                        # 本地调试，不带鉴权参数
python build.py --sharecode XXXXXX     # 部署到需要 ?sharecode= 鉴权的平台
```

产物：

- `pwa/index.html` —— 带 manifest、图标、SW 注册的应用页
- `pwa/manifest.webmanifest` —— 应用清单
- `pwa/sw.js` —— Service Worker（cache-first + 后台更新）
- `pwa/icon-*.png` —— 应用图标，由 `make_icons.py` 生成（图标以 Base64 内嵌在脚本里，不需要联网或装任何依赖）

> **部署到带鉴权的平台时注意**：有些平台（如 `workbuddy.host`）靠 URL 查询参数 `?sharecode=` 鉴权，而浏览器获取 `<link rel="manifest">` 时按规范**不发送 Cookie**。所以 manifest、图标、`start_url`、Service Worker 的 URL 必须全部带上 `sharecode`，否则浏览器会拿到 403，安装入口会一直是灰的。`build.py` 已经处理好这一点。

## 公众号排版兼容性笔记

如果你在写自己的公众号排版工具，这几条是最费时间的：

1. **正文标准宽度约 677px**，手机预览约 420px（去掉内边距约 384px）。换行点会随容器宽度变化，无法完全锁定。
2. **`<style>` 和 class 全部无效**，只能内联。
3. **`<strong>` 建议显式写 `display:inline`**，否则可能被当成块级元素强制换行。
4. **序号不要用 `<ol>` 的自动编号**，用文字写死 + `padding-left` / 负 `text-indent` 做悬挂缩进，折行才能对齐到文字左缘。
5. **图片不要用 `object-fit` 和圆角**，公众号会重写这两个属性，结果是图被裁掉。
6. **表格需要 `table-layout:fixed` + 显式列宽**，否则两列会被平均分。

## 目录结构

```
wechat-article-formatter/
├── wechat-formatter.html      # 单文件版（主程序，零依赖）
├── pwa/
│   ├── build.py               # 构建脚本：生成 index.html / manifest / sw.js
│   ├── make_icons.py          # 图标生成脚本（Base64 内嵌，纯标准库）
│   ├── index.html             # 构建产物（由 build.py 生成）
│   ├── manifest.webmanifest   # 应用清单（由 build.py 生成）
│   └── sw.js                  # Service Worker（由 build.py 生成）
├── LICENSE
└── README.md
```

## 二次开发

主程序全部逻辑都在 `wechat-formatter.html` 一个文件里：

- `inlineCSS(src)` —— HTML 原格式模式的入口，负责 CSS 内联化与公众号适配
- `parse(md)` —— Markdown 模式的解析器
- `copyRich()` —— 从离屏容器复制富文本
- 列表 / 表格 / 图片的适配规则都集中在 `inlineCSS()` 里，改那里即可

## 免责声明

本项目与腾讯 / 微信官方无关，仅为个人排版效率工具。公众号编辑器的实际行为可能随版本调整，请以你看到的真实效果为准。

## License

MIT
