const notifications = [
  {
    path: "/notifications/sources",
    name: "NotificationSourceInput",
    component: () => import("@/views/notifications/NotificationSourceInput.vue"),
    meta: { pageTitle: "通知: 知らせ源入力", resource: "notifications" },
  },
];

export default notifications;
