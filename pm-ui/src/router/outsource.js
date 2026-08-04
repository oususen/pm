const outsource = [
  {
    path: "/outsource/menu",
    name: "OutsourceMenu",
    component: () => import("@/views/outsource/OutsourceMenu.vue"),
    meta: { pageTitle: "FB外作管理", manualPath: "FB/FB外作管理.md", resource: "outsource" },
  },
  {
    path: "/outsource/orders",
    name: "OutsourceOrderList",
    component: () => import("@/views/outsource/OutsourceOrderList.vue"),
    meta: { pageTitle: "FB受注一覧", manualPath: "FB/外作_受注取込と受注一覧.md", resource: "outsource" },
  },
  {
    path: "/outsource/orders/import",
    name: "OutsourceOrderImport",
    component: () => import("@/views/outsource/OutsourceOrderImport.vue"),
    meta: { pageTitle: "FB受注取込", manualPath: "FB/外作_受注取込と受注一覧.md", resource: "outsource", permission: "edit" },
  },
  {
    path: "/outsource/orders/:id",
    name: "OutsourceOrderDetail",
    component: () => import("@/views/outsource/OutsourceOrderDetail.vue"),
    meta: { pageTitle: "案件詳細", manualPath: "FB/外作_案件詳細.md", resource: "outsource" },
  },
  {
    path: "/outsource/excel-export",
    name: "OutsourceExcelExport",
    component: () => import("@/views/outsource/OutsourceExcelExport.vue"),
    meta: { pageTitle: "外作先展開Excel出力", manualPath: "FB/外作_外作先展開Excel出力.md", resource: "outsource", permission: "edit" },
  },
  {
    path: "/outsource/splits/import",
    name: "OutsourceSplitImport",
    component: () => import("@/views/outsource/OutsourceSplitImport.vue"),
    meta: { pageTitle: "分割計画取込", manualPath: "FB/外作_分割計画取込.md", resource: "outsource", permission: "edit" },
  },
  {
    path: "/outsource/materials",
    name: "OutsourceMaterialList",
    component: () => import("@/views/outsource/OutsourceMaterialList.vue"),
    meta: { pageTitle: "材料支給", manualPath: "FB/外作_材料手配と材料検収.md", resource: "outsource" },
  },
  {
    path: "/outsource/material-receiving",
    name: "OutsourceMaterialReceiving",
    component: () => import("@/views/outsource/OutsourceMaterialReceiving.vue"),
    meta: { pageTitle: "材料検収", manualPath: "FB/外作_材料手配と材料検収.md", resource: "outsource" },
  },
  {
    path: "/outsource/material-stock",
    name: "OutsourceMaterialStock",
    component: () => import("@/views/outsource/OutsourceMaterialStock.vue"),
    meta: { pageTitle: "材料在庫", manualPath: "FB/外作_在庫管理.md", resource: "outsource" },
  },
  {
    path: "/outsource/product-stock",
    name: "OutsourceProductStock",
    component: () => import("@/views/outsource/OutsourceProductStock.vue"),
    meta: { pageTitle: "完成品在庫", manualPath: "FB/外作_在庫管理.md", resource: "outsource" },
  },
  {
    path: "/outsource/procurement",
    name: "OutsourceProcurement",
    component: () => import("@/views/outsource/OutsourceProcurement.vue"),
    meta: { pageTitle: "材料手配", manualPath: "FB/外作_材料手配と材料検収.md", resource: "outsource" },
  },
  {
    path: "/outsource/delivery",
    name: "OutsourceDelivery",
    component: () => import("@/views/outsource/OutsourceDelivery.vue"),
    meta: { pageTitle: "納入・出荷管理", manualPath: "FB/外作_納入出荷管理.md", resource: "outsource" },
  },
  {
    path: "/outsource/progress",
    name: "OutsourceProgress",
    component: () => import("@/views/outsource/OutsourceProgress.vue"),
    meta: { pageTitle: "FB外作進捗管理", manualPath: "FB/外作_進捗管理.md", resource: "outsource" },
  },
  {
    path: "/outsource/masters",
    name: "OutsourceMasters",
    component: () => import("@/views/outsource/masters/OutsourceMasters.vue"),
    meta: { pageTitle: "FB外作マスタ", manualPath: "FB/外作_マスタ管理.md", resource: "outsource", permission: "edit" },
  },
  {
    path: "/outsource/first-article-setting",
    name: "OutsourceFirstArticleSetting",
    component: () => import("@/views/outsource/OutsourceFirstArticleSetting.vue"),
    meta: { pageTitle: "FB外作お久しぶり製品通知設定", resource: "outsource.first_article", permission: "edit" },
  },
];

export default outsource;
