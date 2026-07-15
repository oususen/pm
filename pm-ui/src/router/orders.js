const orders = [
  {
    path: "/orders/menu",
    name: "OrderMenu",
    component: () => import("@/views/orders/OrderMenu.vue"),
    meta: { pageTitle: "受注管理メニュー", manualPath: "README.md", resource: "orders", allowChildResources: true },
  },
  {
    path: "/orders/kubota-naiji-analysis",
    name: "KubotaNaijiAnalysis",
    component: () => import("@/views/orders/KubotaNaijiAnalysis.vue"),
    meta: { pageTitle: "クボタ内示変化推移分析", manualPath: "受注/クボタ内示変化推移分析.md", resource: "orders.kubota_analysis" },
  },
  {
    path: "/orders/naiji-analysis",
    name: "NaijiAnalysis",
    component: () => import("@/views/orders/NaijiAnalysis.vue"),
    meta: { pageTitle: "内示分析", resource: "orders.naiji_analysis" },
  },
  {
    path: "/orders/missing-routing-items",
    name: "MissingRoutingOrderItems",
    component: () => import("@/views/orders/MissingRoutingOrderItems.vue"),
    meta: { pageTitle: "ルーティング未設定の注文品", manualPath: "受注/受注一覧.md", resource: "orders.list" },
  },
  {
    path: "/orders/first-article-setting",
    name: "OrderFirstArticleSetting",
    component: () => import("@/views/orders/OrderFirstArticleSetting.vue"),
    meta: { pageTitle: "受注お久しぶり製品通知設定", resource: "orders", permission: "edit" },
  },
  {
    path: "/orders",
    name: "OrderList",
    component: () => import("@/views/orders/OrderList.vue"),
    meta: { pageTitle: "受注一覧", manualPath: "受注/受注一覧.md", resource: "orders.list" },
  },
  {
    path: "/csv-upload",
    name: "CSVUpload",
    component: () => import("@/views/orders/CSVUpload.vue"),
    meta: { pageTitle: "CSV Upload", manualPath: "受注/受注取込.md", resource: "orders.csv_import", permission: "edit" },
  },
];

export default orders;
