# mjlog to MJAI 変換システム

## 概要
天鳳のmjlog形式（XML）ファイルをMJAI形式（JSON Lines）に変換するシステムです。
Ruby mjai gemを使用した安定した変換を実現しています。

## 必要な環境
- Python 3.11以上
- Ruby 3.4以上
- mjai gem (0.0.7)
- Mortal (オプション: 検証用)

## セットアップ

### 1. Ruby環境の準備
```bash
# Rubyのインストール確認
ruby --version
# => ruby 3.4.5 以上

# mjai gemのインストール
gem install mjai
```

### 2. mjai gemの互換性修正
Ruby 3.4では`URI.decode`が廃止されているため、以下の修正が必要です：

**ファイル**: `C:\Ruby34-x64\lib\ruby\gems\3.4.0\gems\mjai-0.0.7\lib\mjai\tenhou_archive.rb`
**行45**: 
```ruby
# 変更前
@names = escaped_names.map(){ |s| URI.decode(s) }

# 変更後
@names = escaped_names.map(){ |s| URI.decode_www_form_component(s) }
```

## ファイル構成

### メインスクリプト
- **batch_convert_mjlog.py**: バッチ変換用のメインスクリプト

## 使用方法

### 基本的な使用方法
```bash
# ディレクトリ内の全XMLファイルを変換
python batch_convert_mjlog.py "dataset/xml(mjlog)/2019" "dataset/mjai/2019"

# 検証付きで変換
python batch_convert_mjlog.py "dataset/xml(mjlog)/2019" "dataset/mjai/2019" -v

# 並列度を指定して変換（デフォルト: 4）
python batch_convert_mjlog.py "dataset/xml(mjlog)/2019" "dataset/mjai/2019" -w 8

# ファイル数を制限して変換
python batch_convert_mjlog.py "dataset/xml(mjlog)/2019" "dataset/mjai/2019" -l 100
```

### コマンドラインオプション
| オプション | 説明 | デフォルト |
|-----------|------|-----------|
| `-v, --validate` | Mortalで出力を検証 | 無効 |
| `-w, --workers` | 並列処理のワーカー数 | 4 |
| `-l, --limit` | 処理するファイル数の上限 | 制限なし |

## 処理の流れ

1. **XML読み込み**: 天鳳形式のXMLファイルを読み込み
2. **Gzip圧縮**: XMLファイルをgzipで圧縮し、.mjlog形式に変換
3. **MJAI変換**: Ruby mjai gemを使用してMJAI形式に変換
4. **検証**（オプション）: Mortalのvalidate_logsで形式を検証
5. **結果出力**: 
   - MJAI形式のJSONファイル（.mjson）
   - 変換結果レポート（conversion_results.json）

## 出力形式

### MJAI形式（JSON Lines）
各行が1つのゲームイベントを表すJSON形式：
```json
{"type":"start_game","uri":"http://tenhou.net/0/?log=...","names":["プレイヤー1","プレイヤー2","プレイヤー3","プレイヤー4"]}
{"type":"start_kyoku","bakaze":"E","kyoku":1,"honba":0,"oya":0,"dora_marker":"N","tehais":[[...],[...],[...],[...]]}
{"type":"tsumo","actor":0,"pai":"2s"}
{"type":"dahai","actor":0,"pai":"1m","tsumogiri":false}
```

### 変換結果レポート
`conversion_results.json`として保存される詳細レポート：
```json
[
  {
    "file": "2019010100gm-00a9-0000-009379d9.xml",
    "status": "converted",
    "error": null,
    "validation": "passed"
  },
  ...
]
```

## トラブルシューティング

### よくあるエラーと対処法

#### 1. "not in gzip format" エラー
**原因**: mjai gemはgzip圧縮されたファイルを期待
**対処**: スクリプトが自動的にgzip圧縮を行います

#### 2. URI.decode エラー
**原因**: Ruby 3.x での互換性問題
**対処**: 上記の「mjai gemの互換性修正」を参照

#### 3. 検証エラー
**原因**: MJAIデータの形式不正
**対処**: 
- can_riichi, can_kakan等のエラーは元データの問題の可能性
- Ruby mjai gemの公式実装を使用することで最小化

## 注意事項

1. **ファイル拡張子**: 入力XMLファイルは`.xml`拡張子である必要があります
2. **一時ファイル**: 処理中に一時的な.mjlogファイルが作成されますが、自動削除されます
3. **エラーハンドリング**: 変換失敗したファイルはスキップされ、レポートに記録されます

## ライセンス
このシステムはRuby mjai gemを使用しています。
mjai gem: https://github.com/gimite/mjai

## サポート
問題が発生した場合は、以下を確認してください：
1. Ruby/Pythonのバージョン
2. mjai gemが正しくインストールされているか
3. 入力XMLファイルの形式が正しいか
