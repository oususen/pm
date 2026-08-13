const notifications = [
  {
    path: "/notifications",
    name: "NotificationList",
    component: () => import("@/views/notifications/NotificationList.vue"),
    meta: { pageTitle: "通知一覧", manualPath: "通知閲覧.md" },
  },
  {
    path: "/notifications/communication",
    name: "NotificationCommunication",
    component: () => import("@/views/notifications/NotificationCommunication.vue"),
    meta: { pageTitle: "通信", resource: "notifications" },
  },
  {
    path: "/notifications/sources",
    name: "NotificationSourceInput",
    component: () => import("@/views/notifications/NotificationSourceInput.vue"),
    meta: { pageTitle: "通知編集", manualPath: "通知作成.md", resource: "notifications" },
  },
  {
    path: "/notifications/calls",
    name: "NotificationCallCenter",
    component: () => import("@/views/notifications/NotificationCallCenter.vue"),
    meta: { pageTitle: "社内通話", resource: "notifications" },
  },
  {
    path: "/notifications/recordings",
    name: "NotificationRecordingList",
    component: () => import("@/views/notifications/NotificationRecordingList.vue"),
    meta: { pageTitle: "通話録音一覧", resource: "notifications" },
  },
];

export default notifications;
