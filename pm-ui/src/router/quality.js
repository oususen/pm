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
];

export default quality;
