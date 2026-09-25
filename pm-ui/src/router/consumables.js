export default [
  {
    path: "/consumables",
    name: "ConsumableMenu",
    component: () => import("@/views/consumables/ConsumableMenu.vue"),
    meta: { pageTitle: "消耗品メニュー", resource: "consumables", allowChildResources: true },
  },
  {
    path: "/consumables/masters",
    name: "ConsumableMasters",
    component: () => import("@/views/consumables/ConsumableMasters.vue"),
    meta: { pageTitle: "消耗品マスタ", resource: "consumables.masters" },
  },
];
