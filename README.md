# 論文コレクション デモ

論文の全文XML（JATS形式）を構造化データとして使うと何ができるかを示す、ブラウザで動くデモです。Europe PMC で公開されている CC BY の論文 74 本で、2つのコレクションを作っています。

- 抗体製剤の凝集・安定性（36本）
- PLAの結晶化・耐熱性（38本）

## 使い方

`index.html` をブラウザで開くだけで動きます。データはページに埋め込まれていて、サーバーは不要です。

```bash
git clone git@github.com:sssshun664/xml-data-analysis.git
cd xml-data-analysis
open index.html
```

ローカルのサーバーで開く場合：

```bash
python3 -m http.server 8765
```

ブラウザで http://localhost:8765/ を開きます。

## できること

| タブ | 内容 |
|---|---|
| コレクション | 本数、段落の内訳、表・図・参考文献の数、ライセンス、収録条件 |
| 全文検索 | 段落が属するセクション（序論・方法・結果・考察・結論）と表を区別して検索。「セクション別の見え方」で、同じ語の書かれ方の違いを比べられる |
| 表から値を集める | 全論文の表から指定した列（Tm、結晶化度、HDT など）の値を集める。論文ごとの分布図に、自社の値を重ねて位置を確かめられる。TSV で書き出し可 |
| ナレッジグラフ | 添加剤・条件・特性・手法などの要素と、同じ文で述べられている要素どうしのつながり。組み合わせの一覧（行列）、要素を中心にした図、間接的なつながり。すべてのつながりに根拠の文が付く |
| 根拠つき回答 | 段落と表だけを根拠にした回答の例（事前に作成したもの。ライブのAIではない） |
| 論文 | 目次・セクション・表・図の説明文に分かれた論文の表示。表ごとに元のXMLも表示できる |

ヘッダーの「営業向け解説」で、各モードの説明（何ができるか、研究開発での使い方、XMLだからできること、デモの手順、注意点）を表示します。「ダーク表示／ライト表示」で表示テーマを切り替えられます。

## ファイル構成

```
index.html                     デモ本体（ビルド済み、データ埋め込み）
build/
  template.html                ページの雛形（UIはここを編集）
  data/collections.json        解析済みの論文データ・回答例・コレクションの説明
  data/kg.json                 ナレッジグラフ（kg.py の出力）
  scripts/fetch_europepmc.py   Europe PMC の検索と全文XMLの取得
  scripts/parse_jats.py        JATS XML を論文データ（JSON）に変換
  scripts/kg.py                要素の辞書と、文単位のつながりの抽出
  scripts/build.py             データ・グラフ・解説を雛形に埋め込んで index.html を作る
  scripts/extract.py           ビルド済みのHTMLから collections.json を取り出す
```

## 作り直す

UIや解説を変えたときは、`build.py` だけを実行します。

```bash
python3 -I build/scripts/build.py .
```

要素の辞書（`kg.py` の `ENT`）を変えたときは、グラフを作り直してからビルドします。

```bash
python3 -I build/scripts/kg.py build/data/collections.json build/data/kg.json
```

```bash
python3 -I build/scripts/build.py .
```

## コレクションを追加する

1. 論文を探す：`python3 -I build/scripts/fetch_europepmc.py search '(TITLE:...) AND OPEN_ACCESS:y AND LICENSE:"cc by"' 80`
2. 全文XMLを取得する：`python3 -I build/scripts/fetch_europepmc.py fetch xml_new PMC... PMC...`
3. JSONに変換する：`python3 -I build/scripts/parse_jats.py xml_new new.json`
4. `build/data/collections.json` に新しいキーを追加する（`name`、`desc`、`query`、`fetched`、`source`、`searchDefault`、`papers`、`qa`）。`qa` の根拠は `PMC番号:s{セクション}p{段落}` または `PMC番号:t{表の番号}` の形式です。
5. `kg.py` の `ENT` に要素の辞書を、`build.py` に項目のプリセット（`presets`）と、グラフの中心にする要素（`kgCenter`）を追加する。
6. `kg.py`、`build.py` の順に実行する。

取得したXMLは外部から受け取ったデータです。スクリプトとは別のフォルダに置き、Python は `-I` を付けて実行してください。

## 制約

- 検索は英語のキーワードの一致です。
- 値の抽出は列名の一致による機械的な処理です。測定条件の違いまでは揃えていません。
- ナレッジグラフは、辞書と「同じ文に出てくるか」で作った簡易版です。因果関係は示しません。「増加・抑制」の表示は文中の語による推定です。

## データとライセンス

論文データは Europe PMC から取得した CC BY 4.0 の論文です（取得日 2026-11-03）。著作権は各論文の著者に帰属します。各論文の DOI とライセンスは、デモの論文表示と `collections.json` に含まれています。
