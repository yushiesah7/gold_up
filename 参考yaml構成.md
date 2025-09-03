yaml例
```yaml
market:
  symbol: EURUSD
  timeframe: M15
ensemble:
  columns:
  - thr=|rsi=14|bb=(30, 1.75)
  - thr=|rsi=14|bb=(30, 2.0)
  weights:
    thr=|rsi=14|bb=(30, 1.75): 0.5
    thr=|rsi=14|bb=(30, 2.0): 0.5
  meta:
    weight_method: equal
    count: 2
    source: runs\summary\selected_ids_eurusd_m15.yaml
execution:
  order_type: market
  price: nextopen
  slippage_rate: 0.0001
  fees_rate: 2.0e-05
  size: 1.0
  leverage: 20.0
  init_cash: 100000.0
stops:
  mode: atr_rr
  atr_rr:
    atr_window:
    - 10
    - 14
    - 20
    k_for_sl:
    - 0.7
    - 0.85
    - 1.0
    - 1.25
    rr:
    - 1.2
    - 1.5
    - 1.8
    - 2.2
risk:
  per_trade_risk_pct: 0.02
constraints:
  session:
    timezone: Europe/London
    start: 07:15
    end: '11:00'
broker_specs:
  digits: 5
  point: 1.0e-05
  trade_contract_size: 100000.0
  trade_tick_value: 148.89400000000003
  trade_tick_size: 1.0e-05
  volume_min: 0.01
  volume_step: 0.01
  trade_stops_level: 0
  trade_freeze_level: 0
  filling_mode: 2
  spread: 22
news_filter: null
trade_identification: null

```


# 作成された最終成果物の説明

以下は [runs/summary/live_spec_eurusd_m15.yaml](cci:7://file:///c:/Users/yushi/work/trade_app/runs/summary/live_spec_eurusd_m15.yaml:0:0-0:0) の各セクション・各値の「意味・vbtpro上の動作・実運用での解釈」です。

# ファイル全体の目的
- __[役割]__ 外部オートトレード用の統合仕様書。アンサンブル構成・執行条件・リスク・セッション・ストップ設定を一元化。
- __[由来]__  
  - `ensemble.columns/weights`: `runs/summary/live_registry_eurusd_m15.yaml` の採択列を等重みで採用  
  - `execution`: [configs/ensemble/eurusd_m15/vbt_params.yaml](cci:7://file:///c:/Users/yushi/work/trade_app/configs/ensemble/eurusd_m15/vbt_params.yaml:0:0-0:0) の値を反映  
  - `stops`: [configs/strategy/_london_open_rr.pro.fast.yaml](cci:7://file:///c:/Users/yushi/work/trade_app/configs/strategy/_london_open_rr.pro.fast.yaml:0:0-0:0) のベースを採用

# market
- __symbol: EURUSD__  
  - 対象シンボル。外部アプリ/データ取得・発注時の銘柄指定に使用。
- __timeframe: M15__  
  - 15分足前提。シグナル集計・ストップ更新・セッション境界もM15基準で動く。

# ensemble
- __columns: ['thr=|rsi=14|bb=(30, 1.75)', 'thr=|rsi=14|bb=(30, 2.0)']__  
  - アンサンブルに含める戦略列（=シグナル生成セット）。  
  - 例: `rsi=14`, `bb=(window=30, alpha=1.75/2.0)` の組み合わせ。`thr=|...|` はしきい値系の適用（詳細は元戦略YAMLに依存）。
- __weights: 0.5 / 0.5__  
  - 等重み合成。ポジションサイズ配分・PnL集計・投票一体化などで均等に扱う。  
  - 実運用では「同額配分」に近い解釈。重みを変えると期待収益/リスク寄与が変化。
- __meta__  
  - __weight_method: equal__ → 重みづけが等分であることの明示。  
  - __count: 2__ → 採用列数。  
  - __source: runs\summary\selected_ids_eurusd_m15.yaml__ → 採用根拠の出所。

# execution
- __order_type: market__  
  - 成行執行。スリッページ考慮が必要（以下の `slippage_rate` で反映）。
- __price: nextopen__  
  - シグナルバーの次足始値で約定を仮定。vbtproでは「シグナル確定後の次足で約定」の安全側シミュレーション。
- __slippage_rate: 0.0001__  
  - レートに対する相対スリッページ。EURUSDなら約1 pip相当（小数点以下桁と`digits`に依存）。実ブローカー状況に合わせて微調整可能。
- __fees_rate: 2.0e-05__  
  - 取引コスト（スプレッド/手数料相当）を相対で計上。コスト感度に直結。
- __size: 1.0__  
  - 1ユニットの建玉（バックテスト上の基本サイズ）。外部アプリ側でロット換算する場合あり。
- __leverage: 20.0__  
  - 想定レバレッジ（実運用の証拠金効率の想定値）。リスク管理/証拠金要件の参考。
- __init_cash: 100000.0__  
  - 初期証拠金（バックテスト/シミュレーションの参照値）。パフォーマンス指標のスケールに影響。

# stops
- __mode: atr_rr__  
  - ATRベースのRR指定ストップ。`SL = k_for_sl * ATR(atr_window)`, `TP = RR * SL` の関係で設置。
- __atr_rr.atr_window: [10, 14, 20]__  
  - ATR算出期間の候補。短期は敏感、長期は安定。外部アプリ側が固定/選択運用するかは設計次第（現状は候補提示）。
- __k_for_sl: [0.7, 0.85, 1.0, 1.25]__  
  - 損切りの基準倍率。小さくするほどタイト。大きいほどワイド。
- __rr: [1.2, 1.5, 1.8, 2.2]__  
  - RR比（TP=RR×SL）。大きいほど利食いは遠くなるが勝率は下がりやすい。  
  - vbtproではSL/TPストップ行列として適用可能。外部アプリ側では「固定組合せを選ぶ」か「回帰的に最適値を決める」運用方針が必要。

# risk
- __per_trade_risk_pct: 0.02__  
  - 1トレード当たり口座の2%を最大損失目安とするリスクポリシー。  
  - 実運用では「SL距離と許容損失からロット自動計算」の基礎。  
  - vbtproのサイズ決定と整合させる場合、SL距離に連動した動的`size`に拡張可能。

# constraints.session
- __timezone: Europe/London__  
  - セッション判定のタイムゾーン。ローカル時刻での実行時間とズレないように注意（ブローカー時刻との整合が重要）。
- __start: 07:15 / end: '11:00'__  
  - ロンドンオープン寄りの時間帯を取引対象に制限。  
  - vbtpro/外部アプリで「この時間帯のみエントリー/クローズを許可」等の実装ポリシーに反映。

# vbtproの観点（このYAMLで決まる挙動）
- __発注モデル__: `price: nextopen`, `order_type: market` → 次足始値成行、`slippage_rate`/`fees_rate`で実務的なコスト補正。  
- __ストップ管理__: `atr_rr` の組合せからSL/TPを自動計算。RR・ATRパラメタの選択方針は外部側に委譲（固定/動的最適化）。  
- __アンサンブル__: 列の合成比率（weights）でPnLやエクスポージャを分配。2列なら各50%。  
- __セッション制約__: 指定時間帯以外の新規は抑制。過剰取引を避け、ターゲットセッションに集中。

# 実運用での注意・微調整ポイント
- __コスト校正__: `slippage_rate`/`fees_rate` はブローカー実測値に近づけるほど再現性が上がる。  
- __ロット算出__: `per_trade_risk_pct` と `k_for_sl×ATR` に基づいてサイズ計算を行う実装が望ましい（現在は固定`size=1.0`）。  
- __候補集合の扱い__: `atr_window/k_for_sl/rr` は候補集合。運用時は固定値を選ぶ、またはヒストリカルで定期リバランス（WFA）する設計が必要。  
- __タイムゾーン整合__: ブローカー時刻・OS時刻・YAMLの`timezone`が一致しているかを事前検証。  
- __ブローカー仕様__（任意拡張）: `digits/point/volume_min/volume_step` を反映する `broker_specs` を追加すると、丸め誤差や発注拒否を減らせる。