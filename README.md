# 18人の空港　おすすめ診断

## 公開まで（GitHub Actions）
1. フォルダ一式をリポジトリの main ブランチに push する
2. リポジトリの Settings → Pages → Build and deployment の Source を「GitHub Actions」にする
3. Actions タブで「Build and deploy」が緑になれば公開完了

以後は main に push するたびに、ビルド（結果ページとサムネイルの生成）と公開が自動で行われる。
Actions タブの「Run workflow」から手動で実行することもできる。

公開URLは Pages の設定から自動で取得するので、`tools/config.json` の `site_url` はローカルでビルドするときだけ使う。
生成物（index.html、result/、og/result-*.png）は .gitignore で除外しているので、リポジトリには入れない。

## ローカルで確認したいとき
`pip install pillow` → `python3 tools/build.py` → `python3 -m http.server` で http://localhost:8000 を開く。

## ファイルの役割
| ファイル | 内容 | 手で編集？ |
|---|---|---|
| data/works.json | 作品データ | ○ |
| data/questions.json | 質問・選択肢・配点（`"作品番号": 点数`） | ○ |
| tools/config.json | 公開URL、サイト名、共有文、ハッシュタグ | ○ |
| og/default.png | 診断ページ（トップ）のサムネイル。仮画像 | 差し替える |
| index.html / result/*.html / og/result-*.png | ビルドで生成 | ×（上書きされる） |

## トップのサムネイルを差し替える
`og/default.png` を 1200×630px の画像で上書きして push する。
ビルドは default.png が既にあれば作り直さない。URL末尾の `?v=` が画像の中身から自動で変わるので、X のキャッシュも更新されやすい。

## 配点を調整したら
`python3 tools/check_distribution.py` で全3125通りの回答に対する各作品の出現率を確認できる。

## ルビ
- `漢字《かんじ》` → 直前の漢字の連なりにルビ
- `｜親文字《るび》` → かなや英字などにもルビを振りたいとき
- 直前が漢字でない《》はルビにせず、そのまま表示する

## フォント
tools/fonts/ のフォント（Zen Old Mincho / Zen Kaku Gothic New、SIL Open Font License）はサムネイル生成用。
