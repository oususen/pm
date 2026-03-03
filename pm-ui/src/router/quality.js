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
];

export default quality;
