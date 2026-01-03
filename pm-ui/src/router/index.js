import { createRouter, createWebHistory } from "vue-router";
import Dashboard from "../views/Dashboard.vue";
import masters from "./masters";
import orders from "./orders";
import production from "./production";
import purchase from "./purchase";
import shipping from "./shipping";

const root = [
  {
    path: "/",
    component: Dashboard,
    meta: { pageTitle: "ダッシュボード - DAISO管理システム" }
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes: [...root, ...masters, ...orders, ...production, ...purchase, ...shipping],
});

const DEFAULT_TITLE = "pm-ui";

router.afterEach((to) => {
  const pageTitle = to.meta?.pageTitle;
  document.title = pageTitle || DEFAULT_TITLE;
});

export default router;
