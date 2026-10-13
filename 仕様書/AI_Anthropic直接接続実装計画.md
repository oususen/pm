# AI Anthropic Claude 直接接続 実装計画

作成日: 2026-10-13 / 状態: **単位1 実装済み(実機未確認・Evaluator検証待ち)**。単位2〜4は未着手。

## 1. 目的と方針(BOSS承認済み)

- Anthropicへ**直接**つなぐ(OpenRouter経由ではない)。最初のモデルは1つだけ: `claude-haiku-5-5`(表示名「Claude Haiku 5.5（Anthropic・有料/要クレジット）」)。プロバイダ名`anthropic`、ラベル「Anthropic Claude」。
- 使えるのは`ai.analysis`の**edit**水準を持つ利用者。権限リソース・テンプレート・権限のマイグレーションは新設しない(案a)。
- 公式docsで確認済みの制約: temperature/top_p/top_kを送らない / プレフィル(末尾assistant)を使わない / `thinking: {"type": "disabled"}` / JSONは構造化出力`output_config.format`(json_schema) / ヘッダは`x-api-key`と`anthropic-version: 2023-06-01` / systemはトップレベル、`max_tokens`必須(`AGENT_MAX_TOKENS`=4096を流用) / 応答は`content[]`の`type == 'text'`を連結 / `stop_reason`が`max_tokens`・`refusal`・`model_context_window_exceeded`は成功にしない。
- 上限値の新設なし(4096トークン・90秒は既存を流用)。**フォールバックなし**(再送しない・別プロバイダ/モデルへ切り替えない・構造化出力が通らなければプロンプトのみに落とさず停止)。
- `AIProviderConfig`の行はデータマイグレーションで**無効**・`display_order=4`・`default_model='claude-haiku-5-5'`。BOSSがキーを設定し、動作確認してから有効にする。

## 2. 単位の分割

| 単位 | 範囲 | 状態 |
|---|---|---|
| 1 | 基盤(クライアント・プロバイダ登録・設定・マイグレーション)と分析案の作成。チャット/相談/コード生成の暫定ガード。フロント最小限 | **実装済み(2026-10-13)。実機未確認、Evaluator検証待ち** |
| 2 | 相談・コード生成のスキーマ(構造化出力)と、単位1の暫定ガード(相談・コード生成の400)の解除 | 未着手 |
| 3 | チャットのツール呼び出しのアダプタ。チャットの403・GET一覧の権限別表示の本実装(単位1は暫定ガード) | 未着手 |
| 4 | (未定。実機確認の結果と運用で決める) | 未着手 |

## 3. 確認事項の承認結果

確認事項1〜9は、すべて推奨のとおりBOSS承認済み(2026-10-13)。

## 4. 単位1 実装内容

### バックエンド(`pm_backend/apps/ai/`)

| ファイル | 内容 |
|---|---|
| `services/anthropic_client.py`(新規) | Messages APIの送受信`request_json`。OpenAI形messagesからの変換(system分離・末尾assistant/system以外のroleは送らず停止)。構造化出力、エラー分類(キー未設定・401/403=`ai_auth`、TimeoutError・URLError(TimeoutError)=`ai_timeout`、接続失敗=`ai_connect`、402/429/400/5xx/529=`ai_http`で文面だけ状況別、空text=`ai_empty`)。`except HTTPError`を`URLError`より前に置く。HTTP本文・キー・リクエスト全文は出さない(`from None`)。`json_schema`が無ければHTTPリクエストなしで停止 |
| `services/analysis_llm.py` | `request_external_json`に`json_schema=None`を追加し、先頭で`anthropic`のとき`anthropic_client.request_json`へ渡す。deepseek/openrouterの経路は変更なし |
| `services/analysis_planning_service.py` | `PLANNING_PROVIDERS`に`anthropic`。`ANTHROPIC_PLAN_SCHEMA`(分析案か`{unsupported}`の`anyOf`)。`create_plan`がanthropicのとき`json_schema`を渡す(温度はbodyに入れない)。`ANTHROPIC_CONSULT_CODEGEN_BLOCKED`(暫定ガードの固定文) |
| `services/chat_service.py` | `ANTHROPIC_API_KEY`/`MODEL`/`BASE_URL`/`MODELS`、`EXTERNAL_AGENT_PROVIDERS['anthropic']`、`PROVIDER_REQUIRED_PERMISSION = {'anthropic': 'ai.analysis'}`。チャットGETの`providers`から常に除外。POSTは`ai.analysis`のedit水準が無い(判定失敗も)と403、あっても400の固定文 |
| `services/analysis_consult_service.py` / `analysis_codegen_service.py` | `anthropic`を400の固定文で拒否(コード生成は`_provider_for`。Claudeで作った分析案も対象)。外部AIは呼ばない |
| `config/catalog.py` / `config/serializers.py` | カタログに`anthropic`。`analysis_temperature`の変更を`anthropic`で拒否 |
| `migrations/0052_alter_aiproviderconfig_provider_anthropic.py` | `provider`のchoices AlterField(`makemigrations`が生成) |
| `migrations/0053_add_anthropic_provider.py` | データマイグレーション(`is_enabled=False`、`display_order=4`、`default_model='claude-haiku-5-5'`)。逆方向は行の削除 |
| `test_anthropic_direct.py`(新規) | 下記の検証 |

設定: `pm_backend/.env.example`・ルート`.env.example`に`ANTHROPIC_API_KEY=`(空)・`ANTHROPIC_MODEL`・`ANTHROPIC_BASE_URL`、`docker-compose.yml`に環境変数の中継を追加。`.env`本体は触っていない。

### フロント(`pm-ui/`)

- `src/views/ai/AIAnalysis.vue`: 有料確認にプロバイダ単位で`anthropic`を追加。
- `src/views/settings/AISettings.vue`: `anthropic`のカードで温度フォームを非表示。
- `src/components/AIChatDrawer.vue`: `providerLabels`にラベルだけ追加(GETに出ないため表示はされない)。
- `scripts/test-analysis-codegen-ui.mjs`・`test-analysis-external-confirmation.mjs`・`test-qwen-analysis-timeout.mjs`を更新。

## 5. 検証結果(generatorの実行結果。完了の判定はEvaluator)

- `ai.test_anthropic_direct`: 37件OK(外部は呼ばない。urlopen模擬、ダミーキー)。
- ai全体・フロント・ビルド・マイグレーション確認の結果は、完了報告に記載。
- 実機(実際のAnthropic API)での確認は**未実施**。

## 6. 未確認・未完了事項

- **実機未確認**: 実際のAnthropic APIへの送信は一度も行っていない。
- **ルートの`anyOf`**: 構造化出力でルートに`anyOf`を置けるかは公式docsで未確認。400で通らない場合は、プロンプトのみに落とさず**停止してBOSSへ報告**する(スキーマの形の再検討はBOSS判断)。
- **プリペイド残高0のときのHTTPステータス**: 未確認(402か400かなど)。現状は402=請求エラー、400=一般文、429=レート制限または月間上限の文面。
- **BOSSの組織でのモデル利用可否**: 未確認(`claude-haiku-5-5`がAPIキーの組織で使えるか)。
- **データ取扱い**: Anthropic側のData retention設定、商用規約でのAPI入力の学習利用、データの所在地は、BOSS確認待ち(`AI運用規約・AI用DB辞書.md`に記載)。
- **入力トークン数**: 分析案の作成の入力(system=公開ビュー一覧を含む)が実際に何トークンか未確認(コスト・`model_context_window_exceeded`の見込み)。
- 相談・コード生成は暫定ガードで拒否(単位2)。チャットは暫定ガード(単位3)。`planning_options`は相談・コード生成用の別一覧を持たないため、画面の選択肢にClaudeが出る(相談・コード生成で選ぶと400の固定文)。
- `ProductionAIDataAnalysis.vue`は範囲外のため触っていない。

## 7. 開発/本番の反映状況

| 項目 | 開発 | 本番 |
|---|---|---|
| コード | 作業ツリーに変更あり(未コミット) | 未反映 |
| マイグレーション0052・0053 | 未適用(`migrate`はBOSS実行) | 未適用 |
| `ANTHROPIC_API_KEY` | 未設定 | 未設定(`docker-compose.yml`の中継は追加済み) |
| AI設定の有効化 | 無効のまま | 無効のまま |
