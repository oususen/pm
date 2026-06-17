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
    meta: { pageTitle: "通知編集", resource: "notifications" },
  },
  {
    path: "/notifications/calls",
    name: "NotificationCallCenter",
    component: () => import("@/views/notifications/NotificationCallCenter.vue"),
    meta: { pageTitle: "社内通話", resource: "notifications" },
  },
];

export default notifications;
