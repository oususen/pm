import { createRouter, createWebHistory } from "vue-router";
import masters from "./masters";
import orders from "./orders";
import production from "./production";
import purchase from "./purchase";
import shipping from "./shipping";

const root = [{ path: "/", redirect: "/masters" }];

const router = createRouter({
  history: createWebHistory(),
  routes: [...root, ...masters, ...orders, ...production, ...purchase, ...shipping],
});

export default router;
