$ErrorActionPreference = 'Stop'

$baseUrl = 'https://10.0.1.232:8501'
$src = Join-Path $PSScriptRoot '..\デジタル化課題整理_報告書.md'
$dst = Join-Path $PSScriptRoot '..\デジタル化課題整理_報告書.html'

$markdown = Get-Content -Raw -LiteralPath $src
$htmlBody = (ConvertFrom-Markdown -InputObject $markdown).Html

$links = [ordered]@{
  '受注一覧' = '/orders'
  'CSV取込' = '/csv-upload'
  'クボタ内示変化推移分析' = '/orders/kubota-naiji-analysis'
  '内示分析' = '/orders/naiji-analysis'
  'ルーティング未設定注文品' = '/orders/missing-routing-items'
  '受注お久しぶり製品通知設定' = '/orders/first-article-setting'
  '旧OPEN受注洗い出し' = '/orders/open-order-audit'
  '生産計画入力' = '/production/plan-input'
  '単独計画' = '/production/single-process-plan'
  '工程ガント' = '/production/process-gantt'
  '出来高集計' = '/production/actual-cycle-time'
  'ラインサイクルタイム' = '/production/line-cycle-time'
  '長期負荷チャート' = '/production/line-load-chart'
  '負荷計算メニュー' = '/production/load-calc-menu'
  'ライン勤務カレンダ' = '/production/line-calendars'
  '生産計画変更履歴' = '/production/plan-change-history'
  'ガントチャート設定' = '/production/gantt-display-product-map'
  '在庫管理' = '/inventory'
  '棚卸現物入力' = '/inventory/stocktake-input'
  '棚卸レイアウト編集' = '/inventory/stocktake-layout'
  '在庫調整メニュー' = '/inventory/adjustments'
  '進度調整' = '/inventory/adjustments/progress'
  '在庫調整' = '/inventory/adjustments/stock'
  '計画在庫調整' = '/inventory/adjustments/planned-stock'
  '調整履歴' = '/inventory/adjustments/history'
  '実進度求め' = '/inventory/actual-progress'
  '棚卸初期化' = '/settings/stocktake-init'
  '仕入れ計画' = '/purchase/plan-input'
  '仕入れ在庫/残量' = '/purchase/inventory'
  '仕入れ進度のみ' = '/purchase/progress-only'
  '仕入れ先カレンダ' = '/purchase/supplier-calendar'
  '仕入れ検収' = '/purchase/receiving'
  '納入予定' = '/purchase/delivery-schedule'
  '仕入れ実績入力' = '/purchase/actual-input'
  '発注提案書一覧' = '/purchase/order-proposals'
  '発注タスク一覧' = '/purchase/order-tasks'
  '自動納入リスト送信' = '/purchase/auto-delivery-list'
  '注文書自動送信' = '/purchase/auto-order-send'
  '出荷指示' = '/shipping/instruction'
  '出荷実績照会' = '/shipping/actual'
  '出荷実績登録' = '/shipping/actual-register'
  '出荷情報追跡' = '/shipping/actual-trace'
  '出荷進度照会' = '/shipping/progress'
  '実績変更・進度調整' = '/shipping/progress-edit'
  'クボタ堺納期調整' = '/shipping/kubota-sakai-due-adjustment'
  'クボタ堺便計画' = '/shipping/kubota-sakai-trip-planning'
  '便確認（出荷担当）' = '/shipping/trip-execution'
  '便確認（業務員）' = '/shipping/trip-progress'
  '便進捗サマリー' = '/shipping/trip-progress-summary'
  '枚方集荷依頼書' = '/shipping/hirakata-pickup'
}

foreach ($name in $links.Keys) {
  $url = "$baseUrl$($links[$name])"
  $anchor = "<a href=""$url"" target=""_blank"" rel=""noopener noreferrer"">$name</a>"
  $pattern = ">\s*$([regex]::Escape($name))\s*<"
  $htmlBody = [regex]::Replace($htmlBody, $pattern, ">$anchor<")
}

$head = @"
<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>デジタル化課題整理_報告書</title>
  <style>
    :root {
      --bg: #f4f6f8;
      --card: #ffffff;
      --text: #1f2937;
      --muted: #667085;
      --line: #d0d5dd;
      --accent: #0f766e;
      --accent-soft: #e6fffb;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Yu Gothic UI", "Meiryo", sans-serif;
      color: var(--text);
      background: linear-gradient(180deg, #eef4f6 0%, var(--bg) 100%);
      line-height: 1.7;
    }
    .wrap {
      width: min(1180px, calc(100vw - 32px));
      margin: 24px auto 56px;
    }
    .hero, .content {
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 16px;
      box-shadow: 0 10px 30px rgba(15, 23, 42, 0.06);
    }
    .hero {
      padding: 28px 32px;
      margin-bottom: 16px;
      background: linear-gradient(135deg, #f7fffd 0%, #ffffff 48%, #f6fbfb 100%);
    }
    .hero h1 {
      margin: 0 0 10px;
      font-size: 30px;
      line-height: 1.25;
    }
    .hero p {
      margin: 0;
      color: var(--muted);
      font-size: 14px;
    }
    .content {
      padding: 28px 32px 40px;
    }
    h1, h2, h3, h4 { color: #0f172a; line-height: 1.35; }
    h1 { font-size: 28px; margin-top: 0; }
    h2 {
      font-size: 24px;
      margin-top: 40px;
      padding-bottom: 6px;
      border-bottom: 2px solid #dfe7ea;
    }
    h3 {
      font-size: 20px;
      margin-top: 28px;
      padding-left: 10px;
      border-left: 5px solid var(--accent);
    }
    h4 { font-size: 17px; margin-top: 22px; }
    p, li { font-size: 14px; }
    ul, ol { padding-left: 22px; }
    blockquote {
      margin: 18px 0;
      padding: 12px 16px;
      background: #f8fafc;
      border-left: 4px solid #94a3b8;
      color: #334155;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      margin: 14px 0 20px;
      font-size: 13px;
    }
    th, td {
      border: 1px solid #dbe1e8;
      padding: 8px 10px;
      text-align: left;
      vertical-align: top;
    }
    th {
      background: #f1f5f9;
      font-weight: 700;
      white-space: nowrap;
    }
    tr:nth-child(even) td { background: #fcfdfd; }
    code {
      font-family: Consolas, Monaco, monospace;
      background: #f4f4f5;
      padding: 1px 5px;
      border-radius: 4px;
      font-size: 0.95em;
    }
    a {
      color: var(--accent);
      text-decoration: none;
      font-weight: 600;
    }
    a:hover { text-decoration: underline; }
    hr {
      border: 0;
      border-top: 1px solid #e5e7eb;
      margin: 28px 0;
    }
    .note {
      margin-top: 12px;
      padding: 10px 12px;
      background: var(--accent-soft);
      border: 1px solid #b8f0ea;
      border-radius: 10px;
      color: #115e59;
      font-size: 13px;
    }
    @media (max-width: 900px) {
      .wrap { width: min(100vw - 16px, 100%); margin: 12px auto 28px; }
      .hero, .content { padding: 18px 16px; border-radius: 12px; }
      .hero h1 { font-size: 24px; }
      h2 { font-size: 21px; }
      h3 { font-size: 18px; }
      table { display: block; overflow-x: auto; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <h1>業務管轄におけるデジタル化の課題整理と効果振り返り</h1>
      <p>正式報告書 / 本番PC向けリンク付きHTML</p>
      <div class="note">画面名リンクは本番環境 <strong>$baseUrl</strong> を開きます。社内ネットワーク接続が必要です。</div>
    </section>
    <main class="content">
"@

$tail = @"
    </main>
  </div>
</body>
</html>
"@

$html = $head + "`r`n" + $htmlBody + "`r`n" + $tail
Set-Content -LiteralPath $dst -Value $html -Encoding utf8
