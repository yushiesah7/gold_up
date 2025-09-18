# golden-dragon-generator

このリポジトリは DDD + Hexagonal（Ports & Adapters）で構成された、研究（バックテスト/最適化）→ デプロイ設定生成までを自動化するプロジェクトです。

以下に「前提」「データ作成」「研究（オートチューニング）」「デプロイ設定生成」「TIPS」をまとめます。

## 前提（セットアップ）

- Python 実行はすべて `uv run` 経由
- Parquet ルート（未設定なら `./data/parquet` を既定使用）
- vbt PRO / MetaTrader5 / pyarrow などは `pyproject.toml` に準拠

## 1) MT5 → Parquet エクスポート（1 回だけ）

PowerShell 例：

```powershell
# 任意（既定の ./data/parquet を使うなら不要）
$env:VBT_PARQUET_ROOT = (Resolve-Path .\data\parquet).Path

# 7通貨 × m15,h1 を一括エクスポート（UTC）
uv run python tools/mt5_to_parquet_once.py `
  --symbols EURUSD,USDJPY,GBPUSD,AUDUSD,USDCHF,EURJPY,GBPJPY `
  --timeframes m15,h1 `
  --start 2023-01-01 --end 2025-09-01
```

実行ログに `[OK] Wrote ... rows=...` が並べば成功です。

## 2) 読み取りスモーク（任意）

```powershell
$code = @'
from datetime import datetime, timedelta, timezone
from trade_app.adapters.vbtpro.data_feed_adapter import VbtProDataFeedAdapter

symbols = ["EURUSD","USDJPY","GBPUSD","AUDUSD","USDCHF","EURJPY","GBPJPY"]
start = (datetime.now(timezone.utc) - timedelta(days=365)).strftime("%Y-%m-%d")
end = datetime.now(timezone.utc).strftime("%Y-%m-%d")

feed = VbtProDataFeedAdapter()
for sym in symbols:
    dto = feed.load([sym], start=start, end=end, timeframe="h1", tz="UTC")
    print(f"OK {sym:7s} h1 rows={len(dto.frame)}")
'@
$tmp = Join-Path $env:TEMP "gdx_read_test.py"; Set-Content -Path $tmp -Value $code -Encoding UTF8
uv run python $tmp; Remove-Item $tmp -Force
```

## 3) 研究（オートチューニング）

- 設定ファイル `spec.yaml` に `universe`（symbols/timeframes）と `sessions` を記載済み。
- Intraday 用の WFA 分割は `batch_runner.py` 側で時間足別に自動調整済み（h1/m15/h4）。

通常実行（既に検証済みの安定設定）

```powershell
uv run python -m trade_app.apps.research.explorer.cli_autotune spec.yaml `
  --start 2023-01-01 --end 2025-09-01 --tz UTC `
  --n-init 16 --n-trials 128 `
  --max-workers 8
```

高負荷版（マシンに余力がある場合はこちらを推奨）

```powershell
# CPU/メモリ状況を見て並列度を上げる（例: 12）
uv run python -m trade_app.apps.research.explorer.cli_autotune spec.yaml `
  --start 2023-01-01 --end 2025-09-01 --tz UTC `
  --n-init 16 --n-trials 256 `
  --max-workers 12
```

便利オプション（特別Option）

- `--session-only NY,LONDON` … セッション限定で探索（spec.yaml を書き換えずに切替）
- `--pruner [sha|median]` … 悪い試行の早期打ち切り（既定: sha=SuccessiveHalving）
- `--scorer [default|robust]` … 実利寄りのロバストスコアラー（MDD/件数/安定性で減点）
- `--auto-range` … ATR分布と fees+slippage から不足キーの探索レンジを自動補完（`sl_atr_mult/tp_atr_mult/rr`）
- 出口系: `--max-bars-hold`（最大保有バー数で強制Exit）、`--sl-trail/--no-sl-trail`（トレーリング、対応実装のみ透過）

出力：

- サマリ表: `runs/summary.csv`
- ベスト設定（ロック）: `runs/spec.lock.json`

## 4) Top-K バンドルの生成（デプロイ前の採用絞り込み）

探索後に複数の `summary.csv` を集約し、`best_score` 上位K件のロックファイルを 1 か所へコピーします。

```powershell
uv run python -m trade_app.apps.research.deploy.cli_export bundle `
  --runs-glob ".\runs\**\summary.csv" `
  --topk 20 `
  --out-dir .\deploy\bundle
```

生成物：

- `deploy/bundle/topk.csv` … 採用リスト（rank/score/元summary/lockのコピー先）
- `deploy/bundle/NN_SYMBOL_TF_SESSION_lock.json` … 各ロック（`spec.lock.json` のコピー）

備考：

- 本CLIは「採用候補の束ね」に特化（YAML生成は別アプリで行う想定）。
- PowerShell ではグロブが展開されることがあるため、そのまま渡して問題ありません。

## 5) TIPS（所要時間短縮・品質向上）

- 並列度: `--max-workers 8→12` と段階的に上げる（スループット向上）。
- 試行数: まず `--n-trials 128`、有望なら `--n-trials 256` 以上へ。
- セッション選定: まず `ALLDAY/LONDON/NY` に絞り、良い組が見えたら `TOKYO` も追加。
- 将来のアンサンブル: 現在のエクスポータは `ensemble=best` 固定。`topk_mean`/`vote` は Port の引数に互換で拡張予定（必要なら対応します）。

## クイックスタート要約（最短の手順）
- MT5→Parquet（初回のみ）
  - `uv run python tools/mt5_to_parquet_once.py --symbols EURUSD,USDJPY,GBPUSD,AUDUSD,USDCHF,EURJPY,GBPJPY --timeframes m15,h1 --start 2023-01-01 --end 2025-09-01`
- 探索（高負荷）
  - `uv run python -m trade_app.apps.research.explorer.cli_autotune spec.yaml --start 2023-01-01 --end 2025-09-01 --tz UTC --n-init 16 --n-trials 256 --max-workers 12`
- Top-K バンドル（採用候補の束ね）
  - `uv run python -m trade_app.apps.research.deploy.cli_export bundle --runs-glob ".\runs\**\summary.csv" --topk 20 --out-dir .\deploy\bundle`

## 安全運用まとめ（重要なポイントだけ）
- 生成時は必ず `--spec spec.yaml` を付ける（lock 内の古い/壊れたテンプレは無視し、`best_params` だけを使う）
- 最初は `ALLDAY/LONDON/NY` に絞る → 当たりが見えたら `TOKYO` も追加
- 並列数は 8→12→14 の順で段階調整（PCの余力を見ながら）
- 結果の見方: `runs/summary.csv` の `best_score` が 0 より大きい組を優先的に採用
- 出力YAML（`deploy/...yaml`）は別アプリで読み込んで使う“最終設定”

### 安全上の注意（ライブ発注はしません）
- 本リポのコマンドは「バックテスト（過去データでの仮想売買）」と「設定ファイルの生成」のみを行います。
- MT5/証券会社への“発注”は一切行いません（データ取得のみ）。
- 生成された `deploy.yaml` を“実運用アプリ”が読み込んだ時に初めて発注の可能性が生じます。本リポではそこまで行いません。

## spec.yaml テンプレ（抜粋例）
```yaml
features:
  rsi_{{rsi.length}}:
    kind: rsi
    on: "close"
    params: { length: "{{rsi.length}}" }
  sma_{{sma.len}}:
    kind: sma
    on: "close"
    params: { length: "{{sma.len}}" }
  bb_{{bb.window}}_{{bb.mult}}:
    kind: bb
    on: "close"
    params: { window: "{{bb.window}}", mult: "{{bb.mult}}" }

plan:
  preconditions:
    - { op: eq, left: "session_active", right: true }
  entries:
    - { op: gt, left: "rsi_{{rsi.length}}", right: "{{entry.rsi_gt}}", pre_shift: 1 }
    - { op: cross_over, left: "sma_{{sma.len}}", right: "bb_{{bb.window}}_{{bb.mult}}_middle", pre_shift: 1 }
  exits:
    - { op: lt, left: "rsi_{{rsi.length}}", right: "{{exit.rsi_lt}}", pre_shift: 1 }

space:
  rsi.length:   { type: int,   low: 5,  high: 40, step: 1 }
  sma.len:      { type: int,   low: 5,  high: 60, step: 5 }
  bb.mult:      { type: float, low: 1.0, high: 3.0, step: 0.25 }
  bb.window:    { type: int,   low: 10, high: 40, step: 2 }
  entry.rsi_gt: { type: int,   low: 45, high: 65, step: 1 }
  exit.rsi_lt:  { type: int,   low: 35, high: 55, step: 1 }

universe:
  symbols: [EURUSD, USDJPY, GBPUSD, AUDUSD, USDCHF, EURJPY, GBPJPY]
  timeframes: [m15, h1]

sessions:
  - { name: ALLDAY, type: all, tz: UTC }
  - { name: LONDON, type: window, start: "08:00", end: "17:00", tz: Europe/London }
  - { name: NY,     type: window, start: "09:30", end: "16:00", tz: America/New_York }
  - { name: TOKYO,  type: window, start: "09:00", end: "15:00", tz: Asia/Tokyo }
```

## 参考: 主なエントリポイント

- 研究（探索）CLI: `trade_app/apps/research/explorer/cli_autotune.py`
- Top-K バンドルCLI: `trade_app/apps/research/deploy/cli_export.py`
- データ取り込み（Parquet）: `tools/mt5_to_parquet_once.py`

---

質問や追加の要望（アンサンブル実装、ライブ配線など）があれば Issue へどうぞ.

## 集約出力（Top-K のみ手早く束ねたい場合）
複数の通貨・時間足・セッションの `summary.csv` 群をまとめ、Top-K のロックだけを収集します。

```powershell
uv run python -m trade_app.apps.research.deploy.cli_export bundle `
  --runs-glob ".\runs\**\summary.csv" `
  --topk 20 `
  --out-dir .\deploy\bundle
```

出力先:
- `deploy/bundle/topk.csv`
- `deploy/bundle/NN_SYMBOL_TF_SESSION_lock.json`

## 6) はじめての方向けマニュアル（専門用語ナシで）

このプロジェクトは「過去の価格データを使って、ルール（条件）を試し、良さそうな設定を探して、最後に“使うための設定ファイル”を作る」道具です。以下は設定ファイル `spec.yaml` とコマンドの意味を、できるだけやさしく説明したものです。

### spec.yaml の見かた（おおまかな地図）

- `universe`（対象）

  - `symbols`: 調べたい通貨のリスト（例: `EURUSD`, `USDJPY`）
  - `timeframes`: 価格をどんな粒度で見るか（例: `m15`=15 分ごと、`h1`=1 時間ごと）

- `sessions`（時間帯の枠）

  - 1 日の中で「どの時間帯に動くか」を指定します。
  - `ALLDAY` は一日中、`LONDON` や `NY` はだいたいの稼働時間帯を表します。
  - 難しく考えなくて OK。「この時間帯だけ使う」と覚えてください。

- `features`（材料）

  - 「価格から作る数式の部品」です。たとえば「平均」「勢い」など。
  - 例: `rsi_{{rsi.length}}` は「勢いの強さ」を示す部品で、`rsi.length` という数字（期間）を後で調整します。

- `plan`（判断ルール）

  - どんな時に「入る」か、どんな時に「やめる」かを、if 文のように書きます。
  - 例: `rsi_... が 50 より大きいとき入る` のような形です。
  - `preconditions` は「そもそもこの条件を満たしていなければ何もしない」という前提条件です。ここでは「指定した時間帯かどうか」を見ています。

- `space`（調整する幅）

  - `features` や `plan` の中で「数字をいくつにするか」を自動で探す範囲です。
  - 例: `rsi.length: 5〜30` のように幅を決めておき、たくさん試して良い数字を見つけます。

- `portfolio`（任意）
  - 実運用で使うときの手数料やサイズの設定です。なければ空でも OK です。

> まとめると: `features`（材料）を `plan`（判断ルール）で使い、`space`（調整幅）で数字を試す。`universe`（通貨や粒度）と `sessions`（時間帯）を変えながら、「どれが良いか」を探します。

### コマンドの引数（どれもカンタン）

- `--start` / `--end`
  - いつからいつまでの期間で試すか（例: `2023-01-01` から `2025-09-01`）。
- `--tz`
  - 時間の基準。`UTC` で OK（難しければ触らなくて大丈夫）。
- `--n-init`
  - 最初に広く試す回数。少ないとスピードは速いが見落としが増える、というイメージ。
- `--n-trials`
  - そのあと掘り下げて試す回数。大きいほど「より良い設定」を見つけやすいが時間がかかる。
- `--max-workers`
  - 同時に動かす数（並列数）。パソコンが強ければ大きくして OK。目安は `8〜12`。

### どの順番でやるの？（最短コース）

1. 一度だけ、過去データを保存します
   - 上の「1) MT5→Parquet エクスポート」を実行
2. 探します（オートチューニング）
   - 上の「3) 研究（オートチューニング）」のコマンドを実行
   - 余力があれば「高負荷版」で回すと、より良い結果になりやすい
3. 使える形にまとめます（デプロイ設定）
   - 上の「4) デプロイ用設定の自動生成」を実行
   - `deploy/通貨/粒度/時間帯.yaml` ができあがり

### 例: より強めに探す（パソコンに余裕がある場合）

```powershell
uv run python -m trade_app.apps.research.explorer.cli_autotune spec.yaml `
  --start 2023-01-01 --end 2025-09-01 --tz UTC `
  --n-init 16 --n-trials 384 `
  --max-workers 14
```

### 困ったときの Q&A

- Q: 何をしているのか、ざっくり一言で言うと？

  - A: 「過去の値動きを見て、条件の数字をいろいろ変え、良さそうな組合せを見つける作業」です。

- Q: `sessions` は難しそう…

  - A: 「どの時間帯だけ使うか」を選ぶだけです。最初は `ALLDAY` と `LONDON` / `NY` だけで十分です。

- Q: 数字（`--n-trials` 等）はどう決めれば？

  - A: まずは README の「通常実行」。余裕がありそうなら「高負荷版」へ。重いと感じたら `--max-workers` を少し下げてください。

- Q: できた YAML はどこで使う？
  - A: `deploy/...yaml` は「最終的に使うための設定ファイル」です。別の運用アプリがこの YAML を読み込んで動きます（このリポジトリでは“作るところ”まで）。

---

わからない点があれば、`spec.yaml` の該当箇所やエラーメッセージを添えて質問してください。できる限り“専門用語ナシ”でお答えします。
