const notifications = [
  {
    path: "/notifications",
    name: "NotificationList",
    component: () => import("@/views/notifications/NotificationList.vue"),
    meta: { pageTitle: "通知一覧" },
  },
  {
    path: "/notifications/sources",
    name: "NotificationSourceInput",
    component: () => import("@/views/notifications/NotificationSourceInput.vue"),
    meta: { pageTitle: "通知編集", resource: "notifications.create" },
  },
];

export default notifications;
