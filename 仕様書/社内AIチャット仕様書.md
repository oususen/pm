# 社内AIチャット仕様書

## 目的

社内利用者が、PC内のQwenに質問し、社内データに基づく回答やチャート・報告書を取得する。

## 実行方式

- 回答モデルはPC内で動作する Ollama の `qwen3:4b-instruct`（Qwen3-4B-Instruct-2507）とする。外部AIサービスへ質問・データを送信しない。
- 導入済みの `qwen3:4b` は実体がThinking-2507で、Ollamaの `thinking.values` が `[true]` の思考専用モデルだった。`think:false` の指定だけでは通常回答モードに変更できないため、このチャットではInstruct版を明示して使用する。
- Instruct版の生成設定は `think:false`、`temperature:0.7`、`top_p:0.8`、`top_k:20`、`min_p:0`、`num_ctx:4096`。モデルの保持時間は10分とする。

## 処理フロー

質問を受け取った際、以下の優先順で処理を振り分ける。

1. **パターンマッチ即回答**: 「北村さんの8月の残業」のように氏名・月が明示された残業照会は、Qwen呼び出しなしでDBから直接集計して回答する。
2. **DB集計＋Qwen回答**: 生産数・仕損・中断・残業などDB根拠を要する質問は、まずQwenで意図分類（intent・日付範囲・対象者等）を行い、DBから集計した結果をQwenに渡して自然文で回答する。チャートや報告書の生成も対応する。
3. **一般会話**: 上記に該当しない質問は、Qwenへ会話をそのまま渡して回答する。

## DB集計対象（読み取り専用）

| intent | データソース | 集計内容 |
|---|---|---|
| production | ProcessRealtimeRecord | 日別生産数・工程別生産数 |
| operator | ProcessRealtimeRecord | 指定作業者の日別生産数 |
| scrap | ScrapRecord | 確定仕損の理由別数量 |
| interruption | BrakeLineRecord | 中断・強制終了の理由別件数 |
| overtime | OvertimeApplication | グループ別残業申請時間（承認段階別） |
| individual_overtime | OvertimeApplication | 個人の残業申請時間（承認段階別） |
| report | 上記複合 | 生産・仕損・中断の期間集計＋報告書生成 |

## 対象データと安全性

- DBは読み取り専用で集計する。書き込み・更新は行わない。
- 個人の評価・順位付けには使わない。
- 作成した文書は画面からダウンロードされ、サーバーには保存されない。

## API

- `GET /api/production-ai-demo/`: Ollama接続状態とモデル準備状態を返す。
- `POST /api/production-ai-demo/`: `message` と直近会話を受け取り、以下のいずれかで回答する。
  - パターンマッチ即回答（残業個人照会）
  - DB集計結果＋Qwen自然文回答（チャート・報告書含む）
  - Qwen一般会話
