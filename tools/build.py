"""
診断サイトのビルドスクリプト。

  python3 tools/build.py

data/works.json と tools/config.json から、次のファイルを生成する。
  index.html          … 診断ページ（OGP: og/default.png）
  result/<番号>.html  … 診断結果ページ（OGP: og/result-<番号>.png）
  og/result-<番号>.png … 結果ページのサムネイル（「書き出し」を描画）
  og/default.png      … 診断ページのサムネイル（仮画像。ファイルが無いときだけ作る）

必要なもの: Python 3.9+ / Pillow（pip install pillow）
"""
import hashlib
import html
import json
import os
import pathlib
import re
import urllib.parse

from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
CONFIG = json.loads((TOOLS / "config.json").read_text(encoding="utf-8"))
WORKS = json.loads((ROOT / "data" / "works.json").read_text(encoding="utf-8"))

# GitHub Actions では環境変数 SITE_URL（Pagesの公開URL）が優先される
SITE_URL = (os.environ.get("SITE_URL") or CONFIG["site_url"]).rstrip("/")
SITE_TITLE = CONFIG["site_title"]

# ---------------------------------------------------------------- ルビ

KANJI = r"\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF々〆〇ヵヶ"
RUBY_RE = re.compile(rf"｜([^｜《》\n]+)《([^《》\n]+)》|([{KANJI}]+)《([^《》\n]+)》")


def tokenize(text):
    """文字列を [(親文字, ルビ or None), ...] に分ける。
    「漢字《かんじ》」と、青空文庫式の「｜親文字《るび》」に対応。
    漢字が直前にない《》は、ルビではない括弧としてそのまま残す。"""
    out, pos = [], 0
    for m in RUBY_RE.finditer(text):
        if m.start() > pos:
            out.append((text[pos:m.start()], None))
        base, ruby = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
        out.append((base, ruby))
        pos = m.end()
    if pos < len(text):
        out.append((text[pos:], None))
    return out


def ruby_html(text):
    return "".join(
        f"<ruby>{html.escape(b)}<rp>（</rp><rt>{html.escape(r)}</rt><rp>）</rp></ruby>" if r else html.escape(b)
        for b, r in tokenize(text)
    )


def plain(text):
    """ルビを外した文字列（meta description 用）"""
    return "".join(b for b, _ in tokenize(text))


# ---------------------------------------------------------------- 作品データ

def opening_of(w):
    """「書き出し」。空の作品（漫画など）は「概要」で代用する"""
    return (w.get("書き出し") or "").strip("\n") or w.get("概要", "")


def links_html(w):
    items = []
    for key, url in (w.get("リンク先") or {}).items():
        if not key or not url or not re.match(r"https?://", url):
            continue
        label, sep, shown = key.partition(": ")
        a = f'<a href="{html.escape(url)}" target="_blank" rel="noopener">{html.escape(shown if sep else key)}</a>'
        items.append(f"<li>{html.escape(label + sep) if sep else ''}{a}</li>")
    return f'<ul class="links">{"".join(items)}</ul>' if items else ""


def category_html(w):
    cat = (w.get("カテゴリ") or "").strip()
    return f'<p class="category">カテゴリ：{html.escape(cat)}</p>' if cat else ""


def catalog_html():
    url = (CONFIG.get("catalog_url") or "").strip()
    if not url:
        return ""
    return f'<a class="secondary catalog" href="{html.escape(url)}" target="_blank" rel="noopener">四点灯台ブースのWebカタログへ</a>'


def file_version(path):
    return hashlib.sha1(path.read_bytes()).hexdigest()[:8]


# ---------------------------------------------------------------- HTML

def head(title, description, url, image, base):
    e = html.escape
    return f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(description)}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{e(SITE_TITLE)}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(description)}">
<meta property="og:url" content="{e(url)}">
<meta property="og:image" content="{e(image)}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Zen+Kaku+Gothic+New:wght@500;700&family=Zen+Old+Mincho:wght@400;700&display=swap">
<link rel="stylesheet" href="{base}assets/style.css">
</head>"""


def sign(base, linked):
    title = html.escape(SITE_TITLE)
    inner = f'<a href="{base}">{title}</a>' if linked else title
    return f"""<header class="sign">
  <svg class="sign-arrow" viewBox="0 0 24 24" aria-hidden="true"><path d="M3 12h15M12 5l7 7-7 7" fill="none" stroke="currentColor" stroke-width="2.6"/></svg>
  <span class="sign-title">{inner}</span>
</header>"""


def build_index():
    img = ROOT / "og" / "default.png"
    image = f"{SITE_URL}/og/default.png?v={file_version(img)}"
    page = f"""{head(SITE_TITLE, CONFIG["description"], SITE_URL + "/", image, "")}
<body>
{sign("", False)}
<main class="wrap" id="app">
  <section class="intro" id="intro">
    <p class="lead">{html.escape(CONFIG["lead"])}</p>
    <button type="button" class="primary" id="start">診断をはじめる</button>
  </section>
  <section class="quiz" id="quiz" hidden>
    <div class="progress" aria-live="polite"><span id="count"></span><ol class="ticks" id="ticks"></ol></div>
    <h1 class="question" id="question" tabindex="-1"></h1>
    <ul class="options" id="options"></ul>
    <button type="button" class="back" id="back">ひとつ前の質問に戻る</button>
  </section>
  <noscript><p class="lead">この診断を使うには JavaScript を有効にしてください。</p></noscript>
</main>
<script src="assets/quiz.js"></script>
</body>
</html>
"""
    (ROOT / "index.html").write_text(page, encoding="utf-8")


def build_result(key, w):
    num = key.replace("作品", "")
    title, author = w["タイトル"], w["作者"]
    opening = opening_of(w)
    is_summary = not (w.get("書き出し") or "").strip()
    url = f"{SITE_URL}/result/{num}.html"
    img = ROOT / "og" / f"result-{num}.png"
    image = f"{SITE_URL}/og/result-{num}.png?v={file_version(img)}"
    desc = plain(opening).replace("\n", "").replace("　", "")[:110]

    share_text = CONFIG["share_text"].format(title=title, author=author)
    share = "https://x.com/intent/post?" + urllib.parse.urlencode(
        {"text": share_text, "url": url, "hashtags": ",".join(CONFIG.get("hashtags", []))},
        quote_via=urllib.parse.quote,
    )
    paras = "".join(f"<p>{ruby_html(p)}</p>" for p in opening.split("\n"))
    figure = ""
    img_path = CONFIG.get("author_images", {}).get(author)
    if img_path:
        with Image.open(ROOT / img_path) as im:
            iw, ih = im.size
        alt = f"{author}『{title}』より"
        figure = (f'<figure class="work-image"><img src="../{html.escape(img_path)}" '
                  f'width="{iw}" height="{ih}" alt="{html.escape(alt)}" loading="lazy"></figure>')
    page_title = f"『{title}』{author}｜{SITE_TITLE}"

    page = f"""{head(page_title, desc, url, image, "../")}
<body>
{sign("../", True)}
<main class="wrap">
  <p class="result-lead">あなたにおすすめの一篇は</p>
  <article class="pass">
    <div class="pass-head">
      <h1 class="work-title">{html.escape(title)}</h1>
      <p class="work-author">{html.escape(author)}</p>
    </div>
    <div class="pass-tear" aria-hidden="true"></div>
    <div class="pass-body{' is-summary' if is_summary else ''}">
      <h2 class="opening-label">{"作品紹介" if is_summary else "書き出し"}</h2>
      {figure}
      <div class="opening">{paras}</div>
      {category_html(w)}
      {links_html(w)}
    </div>
  </article>
  <div class="actions">
    <a class="primary" href="{html.escape(share)}" target="_blank" rel="noopener">Xで結果を共有する</a>
    <a class="secondary" href="../">もう一度診断する</a>
    {catalog_html()}
  </div>
</main>
</body>
</html>
"""
    (ROOT / "result" / f"{num}.html").write_text(page, encoding="utf-8")


# ---------------------------------------------------------------- OGP画像

W, H = 1200, 630
PAPER, INK, SUB, SIGN, LINE = "#ECEFF1", "#1E2A44", "#5B6676", "#F3C316", "#C4CBD3"
F_MINCHO = str(TOOLS / "fonts" / "ZenOldMincho-Regular.ttf")
F_MINCHO_B = str(TOOLS / "fonts" / "ZenOldMincho-Bold.ttf")
F_GOTHIC = str(TOOLS / "fonts" / "ZenKakuGothicNew-Medium.ttf")

NO_LINE_START = set("、。，．・：；？！ー）」』】〉》〕］｝’”ぁぃぅぇぉっゃゅょゎァィゥェォッャュョヮヵヶ…‥")


def layout(tokens, font, rfont, max_w):
    """ルビ付きテキストを行に分ける。各行は [(x, base, ruby, w)]。
    ルビ付きの語は途中で折り返さない。行頭禁則文字はぶら下げる。"""
    units = []
    for base, ruby in tokens:
        if ruby:
            w = max(font.getlength(base), rfont.getlength(ruby))
            units.append((base, ruby, w))
        else:
            units += [(c, None, font.getlength(c)) for c in base]
    lines, cur, x = [], [], 0.0
    for base, ruby, w in units:
        if cur and x + w > max_w and not (ruby is None and base in NO_LINE_START):
            lines.append(cur)
            cur, x = [], 0.0
        cur.append((x, base, ruby, w))
        x += w
    if cur:
        lines.append(cur)
    return lines


def draw_opening(d, text, box, size, max_lines):
    x0, y0, max_w = box
    font = ImageFont.truetype(F_MINCHO, size)
    rfont = ImageFont.truetype(F_MINCHO, size // 2)
    lh = int(size * 1.95)
    lines = []
    for para in text.split("\n"):
        lines += layout(tokenize(para), font, rfont, max_w)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        last = lines[-1]
        ell = font.getlength("…")
        while last and last[-1][0] + last[-1][3] + ell > max_w:
            last.pop()
        x = last[-1][0] + last[-1][3] if last else 0
        last.append((x, "…", None, ell))
    for i, line in enumerate(lines):
        y = y0 + i * lh
        for x, base, ruby, w in line:
            bw = font.getlength(base)
            d.text((x0 + x + (w - bw) / 2, y), base, font=font, fill=INK)
            if ruby:
                rw = rfont.getlength(ruby)
                d.text((x0 + x + (w - rw) / 2, y - size * 0.62), ruby, font=rfont, fill=SUB)
    return len(lines)


def base_canvas():
    im = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 22, H], fill=SIGN)
    return im, d


def build_result_image(key, w):
    num = key.replace("作品", "")
    im, d = base_canvas()
    pad = 96
    og_img = CONFIG.get("author_og_images", {}).get(w["作者"])
    if og_img:
        # 指定画像を上部の枠（1008×430）に収まるよう縮小・拡大して中央に置く
        src = Image.open(ROOT / og_img).convert("RGBA")
        flat = Image.new("RGB", src.size, "#FFFFFF")
        flat.paste(src, mask=src.split()[3])
        box_w, box_h, top = W - pad * 2, 430, 40
        scale = min(box_w / flat.width, box_h / flat.height)
        size = (round(flat.width * scale), round(flat.height * scale))
        flat = flat.resize(size, Image.LANCZOS)
        x, y = (W - size[0]) // 2, top + (box_h - size[1]) // 2
        im.paste(flat, (x, y))
        d.rectangle([x - 1, y - 1, x + size[0], y + size[1]], outline=LINE, width=1)
    else:
        draw_opening(d, opening_of(w), (pad, 92, W - pad * 2), 38, 5)
    # 下部：作品名と作者、サイト名
    d.line([pad, 500, W - pad, 500], fill=LINE, width=2)
    af = ImageFont.truetype(F_GOTHIC, 22)
    # タイトルは区切り線と同じ幅に収める。収まらなければ文字を小さくし（30→22px）、
    # それでも収まらないときだけ末尾を「…」で省略する
    title_x = pad - 14  # 『 の左の余白ぶん左に出して、本文と頭をそろえる
    max_w = W - pad - title_x
    title = f"『{w['タイトル']}』"
    for size in range(30, 21, -1):
        tf = ImageFont.truetype(F_MINCHO_B, size)
        if tf.getlength(title) <= max_w:
            break
    core = w["タイトル"]
    while tf.getlength(title) > max_w and len(core) > 1:
        core = core[:-1]
        title = f"『{core}…』"
    d.text((title_x, 528 + (30 - size) // 2), title, font=tf, fill=INK)
    d.text((pad, 576), w["作者"], font=af, fill=SUB)
    st = SITE_TITLE
    d.text((W - pad - af.getlength(st), 576), st, font=af, fill=SUB)
    im.save(ROOT / "og" / f"result-{num}.png", optimize=True)


def build_default_image():
    """診断ページ用の仮画像。og/default.png が既にあれば作らない（差し替え後に上書きしないため）"""
    path = ROOT / "og" / "default.png"
    if path.exists():
        return
    im, d = base_canvas()
    big = ImageFont.truetype(F_MINCHO_B, 64)
    small = ImageFont.truetype(F_GOTHIC, 28)
    d.text((96, 220), SITE_TITLE, font=big, fill=INK)
    im.save(path, optimize=True)


# ----------------------------------------------------------------

def main():
    (ROOT / "og").mkdir(exist_ok=True)
    (ROOT / "result").mkdir(exist_ok=True)
    build_default_image()
    for key, w in WORKS.items():
        build_result_image(key, w)
        build_result(key, w)
    build_index()
    print(f"built: index.html, {len(WORKS)} result pages / images")


if __name__ == "__main__":
    main()