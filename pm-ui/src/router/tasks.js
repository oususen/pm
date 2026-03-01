const tasks = [
  {
    path: "/tasks",
    name: "TaskInbox",
    component: () => import("@/views/tasks/TaskInbox.vue"),
    meta: { pageTitle: "タスク受信箱" },
  },
]

export default tasks
