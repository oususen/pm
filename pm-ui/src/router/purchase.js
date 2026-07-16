const purchase = [
  {
    path: "/purchase/menu",
    name: "PurchaseMenu",
    component: () => import("@/views/purchase/PurchaseMenu.vue"),
    meta: { pageTitle: "仕入れ管理メニュー", resource: "purchase", allowChildResources: true },
  },
  {
    path: "/purchase/plan-input",
    name: "PurchasePlanInput",
    component: () => import("@/views/purchase/PurchasePlanInput.vue"),
    meta: { pageTitle: "仕入れ計画", manualPath: "仕入れ/仕入計画入力.md", resource: "purchase.plan_input" },
  },
  {
    path: "/purchase/inventory",
    name: "PurchaseInventory",
    component: () => import("@/views/inventory/PurchaseInventory.vue"),
    meta: { pageTitle: "仕入れ在庫/残量", manualPath: "生産/仕入れ在庫残量一覧.md", resource: "purchase.inventory" },
  },
  {
    path: "/purchase/progress-only",
    name: "PurchaseProgressOnly",
    component: () => import("@/views/purchase/PurchaseProgressOnly.vue"),
    meta: { pageTitle: "仕入れ進度のみ", resource: "purchase.progress" },
  },
  {
    path: "/purchase/supplier-calendar",
    name: "PurchaseSupplierCalendar",
    component: () => import("@/views/purchase/PurchaseSupplierCalendar.vue"),
    meta: { pageTitle: "仕入れ先カレンダ", manualPath: "仕入れ/仕入れ先カレンダ.md", resource: "purchase.supplier_calendar" },
  },
  {
    path: "/purchase/receiving",
    name: "PurchaseReceiving",
    component: () => import("@/views/purchase/PurchaseReceiving.vue"),
    meta: { pageTitle: "仕入れ検収", manualPath: "仕入れ/仕入れ検収.md", resource: "purchase.receiving" },
  },
  {
    path: "/purchase/delivery-schedule",
    name: "PurchaseDeliverySchedule",
    component: () => import("@/views/purchase/PurchaseDeliverySchedule.vue"),
    meta: {
      pageTitle: "納入予定",
      manualPath: "仕入れ/納入予定.md",
      resource: "purchase.delivery_schedule",
    },
  },
  {
    path: "/purchase/supplier-order-pattern",
    name: "PurchaseSupplierOrderPatternSettings",
    component: () => import("@/views/settings/SupplierOrderPatternSettings.vue"),
    meta: {
      pageTitle: "納入パターン設定",
      manualPath: "設定/納入パターン設定.md",
      resource: "purchase.supplier_order_pattern",
      fallbackToParent: false,
    },
  },
  {
    path: "/purchase/outsource-progress-compare",
    name: "OutsourceProgressCompare",
    component: () => import("@/views/purchase/OutsourceProgressCompare.vue"),
    meta: { pageTitle: "外作注文書・進度表比較", resource: "purchase.progress" },
  },
  {
    path: "/purchase/actual-input",
    name: "PurchaseActualInput",
    component: () => import("@/views/purchase/PurchaseActualInput.vue"),
    meta: { pageTitle: "仕入れ実績入力", manualPath: "仕入れ/仕入れ実績入力.md", resource: "purchase.actual_input" },
  },
  {
    path: "/purchase/actual-inquiry",
    name: "PurchaseActualInquiry",
    component: () => import("@/views/purchase/PurchaseActualInquiry.vue"),
    meta: { pageTitle: "納入実績照会", resource: "purchase.actual_inquiry" },
  },
  {
    path: "/purchase/actual-edit",
    name: "PurchaseActualEdit",
    component: () => import("@/views/purchase/PurchaseActualEdit.vue"),
    meta: {
      pageTitle: "納入実績編集",
      resource: "purchase.actual_edit",
    },
  },
  {
    path: "/purchase/order-proposals",
    name: "PurchaseOrderProposalList",
    component: () => import("@/views/purchase/PurchaseOrderProposalList.vue"),
    meta: { pageTitle: "発注提案書一覧", resource: "purchase.order_proposals" },
  },
  {
    path: "/purchase/order-tasks",
    name: "PurchaseOrderTaskList",
    component: () => import("@/views/purchase/PurchaseOrderTaskList.vue"),
    meta: { pageTitle: "発注タスク一覧", resource: "purchase.order_proposals" },
  },
  {
    path: "/purchase/order-proposals/:id",
    name: "PurchaseOrderProposalDetail",
    component: () => import("@/views/purchase/PurchaseOrderProposalDetail.vue"),
    meta: { pageTitle: "発注提案書詳細", resource: "purchase.order_proposals" },
  },
  {
    path: "/purchase/auto-delivery-list",
    name: "PurchaseAutoDeliveryList",
    component: () => import("@/views/purchase/PurchaseAutoDeliveryListSettings.vue"),
    meta: { pageTitle: "自動納入リスト送信", manualPath: "仕入れ/自動納入リスト送信.md", resource: "purchase.auto_delivery_list" },
  },
];

export default purchase;
