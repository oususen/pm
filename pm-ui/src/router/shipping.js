const shipping = [
  {
    path: "/shipping/menu",
    name: "ShippingMenu",
    component: () => import("@/views/shipping/ShippingMenu.vue"),
    meta: { pageTitle: "出荷管理メニュー", manualPath: "README.md", resource: "shipping" },
  },
  {
    path: "/shipping/instruction",
    name: "ShippingInstruction",
    component: () => import("@/views/shipping/ShippingInstruction.vue"),
    meta: { pageTitle: "出荷指示", manualPath: "出荷/出荷指示.md", resource: "shipping.instruction" },
  },
  {
    path: "/shipping/actual",
    name: "ShippingActual",
    component: () => import("@/views/shipping/ShippingActual.vue"),
    meta: { pageTitle: "出荷実績", manualPath: "出荷/出荷実績.md", resource: "shipping.actual" },
  },
  {
    path: "/shipping/progress",
    name: "ShippingProgress",
    component: () => import("@/views/shipping/ShippingProgress.vue"),
    meta: { pageTitle: "出荷進度照会", manualPath: "出荷/出荷進度照会.md", resource: "shipping.progress" },
  },
  {
    path: "/shipping/order-expansion",
    name: "ShippingOrderExpansion",
    component: () => import("@/views/shipping/ShippingOrderExpansion.vue"),
    meta: { pageTitle: "受注展開", resource: "shipping.progress" },
  },
  {
    path: "/shipping/order-document",
    name: "ShippingOrderDocument",
    component: () => import("@/views/shipping/ShippingOrderDocument.vue"),
    meta: { pageTitle: "出荷指示書", manualPath: "出荷/出荷指示書.md", resource: "shipping.order_document" },
  },
  {
    path: "/shipping/fujishoji-document",
    name: "FujishojiShippingDocument",
    component: () => import("@/views/shipping/FujishojiShippingDocument.vue"),
    meta: { pageTitle: "富士商事出荷指示書", resource: "shipping.fujishoji_document" },
  },
  {
    path: "/shipping/hirakata-pickup",
    name: "HirakataPickup",
    component: () => import("@/views/shipping/HirakataPickup.vue"),
    meta: { pageTitle: "枚方集荷依頼書", manualPath: "出荷/枚方集荷依頼書.md", resource: "shipping.hirakata_pickup" },
  },
  {
    path: "/shipping/kubota-sakai-due-adjustment",
    alias: ["/shipping/kubota-sakai-due-adjustment-2"],
    name: "KubotaSakaiDueAdjustment",
    component: () => import("@/views/shipping/KubotaSakaiDueAdjustment.vue"),
    meta: { pageTitle: "クボタ堺納期調整", resource: "shipping.kubota_sakai_due_adjustment" },
  },
  {
    path: "/shipping/kubota-sakai-trip-planning",
    alias: ["/shipping/kubota-sakai-trip-planning-2"],
    name: "KubotaSakaiTripPlanning",
    component: () => import("@/views/shipping/KubotaSakaiTripPlanning.vue"),
    meta: { pageTitle: "クボタ堺便計画", resource: "shipping.kubota_sakai_trip_planning" },
  },
  {
    path: "/shipping/trip-execution",
    name: "ShippingTripExecution",
    component: () => import("@/views/shipping/ShippingTripExecution.vue"),
    meta: { pageTitle: "便確認（出荷担当）", resource: "shipping.trip_execution", actualInputEnabled: false },
  },
  {
    path: "/shipping/trip-progress",
    name: "ShippingTripProgress",
    component: () => import("@/views/shipping/ShippingTripExecution.vue"),
    meta: { pageTitle: "便確認（業務員）", resource: "shipping.trip_progress", actualInputEnabled: true },
  },
  {
    path: "/shipping/trip-progress-summary",
    name: "ShippingTripProgressSummary",
    component: () => import("@/views/shipping/ShippingTripProgress.vue"),
    meta: { pageTitle: "便進捗サマリー", resource: "shipping.trip_progress_summary" },
  },
  {
    path: "/shipping/ship-to-lead-time",
    name: "ShipToLeadTimeSetting",
    component: () => import("@/views/shipping/ShipToLeadTimeSetting.vue"),
    meta: { pageTitle: "納入地別出荷加算日数", resource: "shipping.ship_to_lead_time" },
  },
];

export default shipping;
