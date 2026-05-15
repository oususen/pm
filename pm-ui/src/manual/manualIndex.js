export const manualSections = [
  {
    id: "top",
    title: "マニュアル",
    items: [{ title: "マニュアルトップ", path: "README.md" }],
  },
  {
    id: "common",
    title: "共通",
    items: [
      { title: "基本操作", path: "共通/基本操作.md" },
      { title: "タスク受信箱", path: "共通/タスク受信箱.md" },
    ],
  },
  {
    id: "masters",
    title: "マスタ",
    items: [
      { title: "カレンダ一覧", path: "マスタ/カレンダ一覧.md" },
      { title: "BOM作成マニュアル", path: "マスタ/BOM作成マニュアル.md" },
    ],
  },
  {
    id: "orders",
    title: "受注管理",
    items: [
      { title: "受注取込", path: "受注/受注取込.md" },
      { title: "受注一覧", path: "受注/受注一覧.md" },
      { title: "クボタ内示変化推移分析", path: "受注/クボタ内示変化推移分析.md" },
    ],
  },
  {
    id: "shipping",
    title: "出荷管理",
    items: [
      { title: "出荷進度照会", path: "出荷/出荷進度照会.md" },
      { title: "出荷指示", path: "出荷/出荷指示.md" },
      { title: "出荷指示書", path: "出荷/出荷指示書.md" },
      { title: "枚方集荷依頼書", path: "出荷/枚方集荷依頼書.md" },
      { title: "出荷実績", path: "出荷/出荷実績.md" },
    ],
  },
  {
    id: "purchase",
    title: "仕入れ管理",
    items: [
      { title: "発注提案システム", path: "仕入れ/発注提案システム.md" },
      { title: "仕入れ検収", path: "仕入れ/仕入れ検収.md" },
      { title: "仕入れ在庫/残量一覧", path: "生産/仕入れ在庫残量一覧.md" },
    ],
  },
  {
    id: "inventory",
    title: "在庫管理",
    items: [
      { title: "在庫管理メニュー", path: "在庫/在庫管理メニュー.md" },
      { title: "在庫調整メニュー", path: "在庫/在庫調整メニュー.md" },
      { title: "在庫調整", path: "在庫/在庫調整.md" },
      { title: "進度調整", path: "在庫/進度調整.md" },
      { title: "調整履歴", path: "在庫/調整履歴.md" },
      { title: "実進度求め", path: "在庫/実進度求め.md" },
    ],
  },
  {
    id: "production",
    title: "生産管理",
    items: [
      { title: "生産計画員業務手順書", path: "生産計画員業務手順書.md" },
      { title: "生産調達向け説明資料", path: "生産調達向け説明資料.md" },
      { title: "工程作業入力", path: "生産/工程作業入力.md" },
      { title: "レーザー実績入力", path: "生産/レーザー実績入力.md" },
      { title: "仕損品記録", path: "生産/仕損品記録.md" },
      { title: "仕損履歴", path: "生産/仕損履歴.md" },
      { title: "進捗管理", path: "生産/進捗管理.md" },
      { title: "実進度求め", path: "在庫/実進度求め.md" },
      { title: "在庫/残量一覧", path: "生産/在庫残量一覧.md" },
      { title: "構成部品在庫一覧", path: "生産/構成部品在庫一覧.md" },
      { title: "ライン需要一覧", path: "生産/ライン需要一覧.md" },
      { title: "生産計画入力", path: "生産/生産計画入力.md" },
      { title: "配送計画（フロア出荷）", path: "生産/配送計画.md" },
      { title: "デフォルト開始時刻設定", path: "生産/デフォルト開始時刻設定.md" },
      { title: "ライン勤務カレンダ", path: "生産/ライン勤務カレンダ.md" },
      { title: "在庫引当一覧", path: "生産/在庫引当一覧.md" },
      { title: "製造指示一覧", path: "生産/製造指示一覧.md" },
      { title: "製造指示登録・編集", path: "生産/製造指示登録編集.md" },
      { title: "工程実績入力", path: "生産/工程実績入力.md" },
      { title: "ミックス順序ボード", path: "生産/ミックス順序ボード.md" },
      { title: "ライン稼働監視", path: "生産/ライン稼働監視.md" },
      { title: "ライン作業記録", path: "生産/ライン作業記録.md" },
      { title: "実績変更", path: "生産/実績変更.md" },
    ],
  },
  {
    id: "quality",
    title: "品質管理",
    items: [
      { title: "工程一体チェックシート", path: "品質/工程一体チェックシート.md" },
    ],
  },
  {
    id: "engineeringChange",
    title: "設変管理",
    items: [{ title: "設変管理", path: "設変/設変管理.md" }],
  },
  {
    id: "settings",
    title: "設定",
    items: [
      { title: "ユーザー管理", path: "設定/ユーザー管理.md" },
      { title: "権限設定", path: "設定/権限設定.md" },
      { title: "定時タスク設定", path: "設定/定時タスク設定.md" },
      { title: "自動計画生成タスク", path: "設定/自動計画生成タスク.md" },
      { title: "納入パターン設定", path: "設定/納入パターン設定.md" },
    ],
  },
];

export const manualLookup = manualSections.reduce((acc, section) => {
  section.items.forEach((item) => {
    acc[item.path] = { ...item, sectionId: section.id, sectionTitle: section.title };
  });
  return acc;
}, {});
