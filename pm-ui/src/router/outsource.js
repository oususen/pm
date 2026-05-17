const outsource = [
  {
    path: "/outsource/menu",
    name: "OutsourceMenu",
    component: () => import("@/views/outsource/OutsourceMenu.vue"),
    meta: { pageTitle: "FB外作管理", resource: "outsource" },
  },
  {
    path: "/outsource/orders",
    name: "OutsourceOrderList",
    component: () => import("@/views/outsource/OutsourceOrderList.vue"),
    meta: { pageTitle: "FB受注一覧", resource: "outsource" },
  },
  {
    path: "/outsource/orders/import",
    name: "OutsourceOrderImport",
    component: () => import("@/views/outsource/OutsourceOrderImport.vue"),
    meta: { pageTitle: "FB受注取込", resource: "outsource", permission: "edit" },
  },
  {
    path: "/outsource/orders/:id",
    name: "OutsourceOrderDetail",
    component: () => import("@/views/outsource/OutsourceOrderDetail.vue"),
    meta: { pageTitle: "案件詳細", resource: "outsource" },
  },
  {
    path: "/outsource/excel-export",
    name: "OutsourceExcelExport",
    component: () => import("@/views/outsource/OutsourceExcelExport.vue"),
    meta: { pageTitle: "外作先展開Excel出力", resource: "outsource", permission: "edit" },
  },
  {
    path: "/outsource/splits/import",
    name: "OutsourceSplitImport",
    component: () => import("@/views/outsource/OutsourceSplitImport.vue"),
    meta: { pageTitle: "分割計画取込", resource: "outsource", permission: "edit" },
  },
  {
    path: "/outsource/materials",
    name: "OutsourceMaterialList",
    component: () => import("@/views/outsource/OutsourceMaterialList.vue"),
    meta: { pageTitle: "材料所要量一覧", resource: "outsource" },
  },
  {
    path: "/outsource/procurement",
    name: "OutsourceProcurement",
    component: () => import("@/views/outsource/OutsourceProcurement.vue"),
    meta: { pageTitle: "材料手配", resource: "outsource" },
  },
  {
    path: "/outsource/delivery",
    name: "OutsourceDelivery",
    component: () => import("@/views/outsource/OutsourceDelivery.vue"),
    meta: { pageTitle: "納入・出荷管理", resource: "outsource" },
  },
  {
    path: "/outsource/progress",
    name: "OutsourceProgress",
    component: () => import("@/views/outsource/OutsourceProgress.vue"),
    meta: { pageTitle: "FB外作進捗管理", resource: "outsource" },
  },
  {
    path: "/outsource/masters",
    name: "OutsourceMasters",
    component: () => import("@/views/outsource/masters/OutsourceMasters.vue"),
    meta: { pageTitle: "FB外作マスタ", resource: "outsource", permission: "edit" },
  },
];

export default outsource;
