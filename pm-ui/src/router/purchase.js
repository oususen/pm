const purchase = [
  {
    path: "/purchase/menu",
    name: "PurchaseMenu",
    component: () => import("@/views/purchase/PurchaseMenu.vue"),
    meta: { pageTitle: "仕入れ管理メニュー", resource: "purchase" },
  },
  {
    path: "/purchase/plan-input",
    name: "PurchasePlanInput",
    component: () => import("@/views/purchase/PurchasePlanInput.vue"),
    meta: { pageTitle: "仕入れ計画", manualPath: "仕入れ/仕入計画入力.md", resource: "purchase" },
  },
  {
    path: "/purchase/inventory",
    name: "PurchaseInventory",
    component: () => import("@/views/inventory/PurchaseInventory.vue"),
    meta: { pageTitle: "仕入れ在庫/残量", manualPath: "生産/仕入れ在庫残量一覧.md", resource: "purchase" },
  },
  {
    path: "/purchase/progress-only",
    name: "PurchaseProgressOnly",
    component: () => import("@/views/purchase/PurchaseProgressOnly.vue"),
    meta: { pageTitle: "仕入れ進度のみ", resource: "purchase" },
  },
  {
    path: "/purchase/supplier-calendar",
    name: "PurchaseSupplierCalendar",
    component: () => import("@/views/purchase/PurchaseSupplierCalendar.vue"),
    meta: { pageTitle: "仕入れ先カレンダ", resource: "purchase" },
  },
  {
    path: "/purchase/actual-input",
    name: "PurchaseActualInput",
    component: () => import("@/views/purchase/PurchaseActualInput.vue"),
    meta: { pageTitle: "仕入れ実績入力", resource: "purchase" },
  },
  {
    path: "/purchase/actual-inquiry",
    name: "PurchaseActualInquiry",
    component: () => import("@/views/purchase/PurchaseActualInquiry.vue"),
    meta: { pageTitle: "納入実績照会", resource: "purchase" },
  },
  {
    path: "/purchase/actual-edit",
    name: "PurchaseActualEdit",
    component: () => import("@/views/purchase/PurchaseActualEdit.vue"),
    meta: { pageTitle: "納入実績編集", resource: "purchase.actual_input" },
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
];

export default purchase;
