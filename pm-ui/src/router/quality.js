const quality = [
  {
    path: "/quality",
    name: "QualityMenu",
    component: () => import("@/views/quality/QualityMenu.vue"),
    meta: { pageTitle: "品質管理メニュー" },
  },
  {
    path: "/quality/equipment-inspection",
    name: "EquipmentInspectionMenu",
    component: () => import("@/views/quality/EquipmentInspectionMenu.vue"),
    meta: { pageTitle: "設備点検表" },
  },
  {
    path: "/quality/equipment-inspection/master",
    name: "EquipmentInspectionMaster",
    component: () => import("@/views/quality/EquipmentInspectionMaster.vue"),
    meta: { pageTitle: "点検項目作成" },
  },
  {
    path: "/quality/equipment-inspection/operation",
    name: "EquipmentInspectionOperation",
    component: () => import("@/views/quality/EquipmentInspectionOperation.vue"),
    meta: { pageTitle: "点検実施" },
  },
  {
    path: "/quality/equipment-inspection/monthly-review",
    name: "EquipmentInspectionMonthlyReview",
    component: () => import("@/views/quality/EquipmentInspectionMonthlyReview.vue"),
    meta: { pageTitle: "月間確認" },
  },
  {
    path: "/quality/product-checksheet",
    name: "ProductChecksheetMenu",
    component: () => import("@/views/quality/ProductChecksheetMenu.vue"),
    meta: { pageTitle: "品質チェックシート" },
  },
  {
    path: "/quality/training-certification",
    name: "TrainingCertificationApp",
    component: () => import("@/views/quality/TrainingCertificationApp.vue"),
    meta: { pageTitle: "教育・テスト・認定" },
  },
  {
    path: "/quality/product-checksheet/templates",
    name: "ProductChecksheetTemplateList",
    component: () => import("@/views/quality/ProductChecksheetTemplateList.vue"),
    meta: { pageTitle: "品質チェックシート作成" },
  },
  {
    path: "/quality/product-checksheet/templates/:id/edit",
    name: "ProductChecksheetEditor",
    component: () => import("@/views/quality/ProductChecksheetEditor.vue"),
    meta: { pageTitle: "製品チェックシート配置編集" },
  },
  {
    path: "/quality/product-checksheet/operation",
    name: "ProductChecksheetOperation",
    component: () => import("@/views/quality/ProductChecksheetOperation.vue"),
    meta: { pageTitle: "チェック実施" },
  },
  {
    path: "/quality/product-checksheet/input/:batchId",
    name: "ProductChecksheetInput",
    component: () => import("@/views/quality/ProductChecksheetInput.vue"),
    meta: { pageTitle: "製品チェックシート入力" },
  },
  {
    path: "/quality/product-checksheet/quality",
    name: "ProductChecksheetQualityList",
    component: () => import("@/views/quality/ProductChecksheetQualityList.vue"),
    meta: { pageTitle: "製品チェックシート品質確認一覧" },
  },
  {
    path: "/quality/product-checksheet/integrated/templates",
    name: "IntegratedChecksheetTemplateManager",
    component: () => import("@/views/quality/IntegratedChecksheetTemplateManager.vue"),
    meta: { pageTitle: "工程一体チェックシート テンプレート管理", manualPath: "品質/工程一体チェックシート.md" },
  },
  {
    path: "/quality/product-checksheet/integrated/operation",
    name: "IntegratedChecksheetOperation",
    component: () => import("@/views/quality/IntegratedChecksheetOperation.vue"),
    meta: { pageTitle: "工程一体チェックシート チェック実施", manualPath: "品質/工程一体チェックシート.md" },
  },
  {
    path: "/quality/product-checksheet/integrated/review",
    name: "IntegratedChecksheetReview",
    component: () => import("@/views/quality/IntegratedChecksheetOperation.vue"),
    meta: { pageTitle: "工程一体チェックシート リーダー・班長確認", manualPath: "品質/工程一体チェックシート.md" },
  },
  {
    path: "/quality/product-checksheet/integrated/weekly-monthly",
    name: "IntegratedChecksheetWeeklyMonthly",
    component: () => import("@/views/quality/IntegratedChecksheetWeeklyMonthly.vue"),
    meta: { pageTitle: "工程一体チェックシート 週・月確認", manualPath: "品質/工程一体チェックシート.md" },
  },
  {
    path: "/quality/product-checksheet/integrated/trend-analysis",
    name: "IntegratedChecksheetTrendAnalysis",
    component: () => import("@/views/quality/IntegratedChecksheetTrendAnalysis.vue"),
    meta: { pageTitle: "工程一体チェックシート 傾向確認・分析", manualPath: "品質/工程一体チェックシート.md" },
  },
  {
    path: "/quality/product-checksheet/integrated/problem-tools",
    name: "IntegratedChecksheetProblemTools",
    component: () => import("@/views/quality/IntegratedChecksheetProblemTools.vue"),
    meta: { pageTitle: "工程一体チェックシート 品質問題時ツール", manualPath: "品質/工程一体チェックシート.md" },
  },
];

export default quality;
