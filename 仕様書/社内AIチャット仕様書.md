# 社内AIチャット仕様書

## 目的

社内利用者が、ローカルQwenまたはDeepSeek APIを選択して質問し、社内データに基づく回答やチャート・報告書を取得する。

社内AIの業務目的、DBアクセス範囲、外部API送信、禁止操作は、[社内AI運用規約・AI用DB辞書](社内AI運用規約・AI用DB辞書.md) に従う。
画面ごとの業務構造、正規データソース、集計規則は、[PMアプリ構造辞書](PMアプリ構造辞書.md) に従う。

## 実行方式

- 画面上で「DeepSeek API」と「ローカルQwen」を切り替えられる。DeepSeek API選択時は「DeepSeek V4 Pro（高精度）」と「DeepSeek Flash（高速）」を切り替えられる。初期選択は幹部会での実演を想定して DeepSeek V4 Pro とする。
- DeepSeek API選択時は、質問・会話履歴・回答に必要なDB集計結果をDeepSeekへ送信する。APIキーはバックエンドの `DEEPSEEK_API_KEY` 環境変数だけで管理し、画面・ソースコード・Gitには含めない。
- DeepSeek API選択時は、DeepSeekが非思考モードの関数呼び出しで読み取り専用ツールを選ぶ。生産数を照会する場合は、品番マスタ検索を行ってから集計ツールを呼ぶ。PM側がツール実行とデータ範囲の検証を担当し、DeepSeekは任意SQLやDB更新を実行できない。
- ローカルQwen選択時は、PC内で動作する Ollama の `qwen3:4b-instruct`（Qwen3-4B-Instruct-2507）を使用し、外部AIサービスへ質問・データを送信しない。
- 導入済みの `qwen3:4b` は実体がThinking-2507で、Ollamaの `thinking.values` が `[true]` の思考専用モデルだった。`think:false` の指定だけでは通常回答モードに変更できないため、このチャットではInstruct版を明示して使用する。
- Instruct版の生成設定は `think:false`、`temperature:0.7`、`top_p:0.8`、`top_k:20`、`min_p:0`、`num_ctx:4096`。モデルの保持時間は10分とする。

## 処理フロー

質問を受け取った際、以下の優先順で処理を振り分ける。

1. **パターンマッチ即回答**: 「北村さんの8月の残業」のように氏名・月が明示された残業照会は、Qwen呼び出しなしでDBから直接集計して回答する。
2. **DeepSeekによるツール調査／Qwenの固定集計**: DeepSeekでは、生産数・仕損・中断・残業などDB根拠を要する質問に対し、モデル自身が品番マスタ検索・許可済み集計ツールを必要な順番で呼び、集計結果を基に自然文で回答する。ローカルQwenでは既存の固定集計を使う。いずれもチャートや報告書の生成に対応する。
   - このチャットは本社の生産管理を基本対象とする。
   - 品番を会話内で明示した場合は、続く生産数質問でもその品番を引き継ぐ。品番マスタに存在しない場合は全品番集計を行わず、未登録であることを回答する。
   - 品番に空白・ハイフン・英字大小の表記ゆれがある場合は正規化して照合する。完全一致しない場合は近い候補を最大3件提示し、AIが候補を勝手に選んで集計しない。
   - AIが示した「1. 生産数」「2. 仕損」「3. 残業」の選択肢に番号だけで返答した場合は、直前の選択肢を業務質問として復元し、直近15件の会話から正式品番と直近の対象期間を引き継いで集計する。
   - 個人別残業は `overtime.personal_summary` の閲覧権限を持つ画面だけで利用できる。DeepSeekには一時ID・期間・合計時間・しきい値超過者だけを渡し、申請明細・理由・連絡先は渡さない。
3. **一般会話**: 上記に該当しない質問は、選択中のモデルへ会話をそのまま渡して回答する。

## DB集計対象（読み取り専用）

| intent | データソース | 集計内容 |
|---|---|---|
| production | ProcessRealtimeRecord、LaserActualDetail、BrakeLineRecord | 日別生産数・工程別生産数。品番指定時は画面別の正規実績を二重計上せずに使用する |
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

実装は、生産管理アプリから独立した `ai` アプリで管理する。`ai/views.py` はHTTP入口、`ai/services/chat_service.py` は業務ロジックを担当する。旧 `production/views_ai_demo.py` と `/api/production-ai-demo/` は互換入口として残す。

- `GET /api/production-ai-demo/`: QwenとDeepSeek APIの準備状態を返す。
- `POST /api/production-ai-demo/`: `message`、直近会話、`provider`（`deepseek` または `qwen`）、DeepSeek利用時の`model`（`deepseek-v4-pro` または `deepseek-flash`）を受け取り、以下のいずれかで回答する。
  - パターンマッチ即回答（残業個人照会）
  - DB集計結果＋選択モデルの自然文回答（チャート・報告書含む）
  - 選択モデルの一般会話
- `GET /api/ai/chat/` と `POST /api/ai/chat/`: 社内AIの正式API。リクエスト・レスポンスは旧APIと同じ。

## AIアプリの権限

- AI画面は `ai.chat` の閲覧権限で表示する。`ai.chat` は `ai` 親権限へフォールバックしない。
- 個人別残業集計は、AI画面の利用可否とは別に `overtime.personal_summary` の閲覧権限を必要とする。
