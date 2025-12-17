<template>
  <div class="app-root" :class="{ 'sidebar-open': sidebarOpen }">
    <header class="app-header">
      <div class="app-header-left">
        <button
          v-if="isMobile"
          type="button"
          class="menu-toggle"
          aria-label="メニューを開閉"
          @click="sidebarOpen = !sidebarOpen"
        >
          ☰
        </button>
        <span class="app-title">ダイウン工業 [マスタメンテ]</span>
      </div>
      <div class="app-header-right">
        <span>{{ todayText }}</span>
      </div>
    </header>

    <div class="app-body">
      <div
        v-if="isMobile && sidebarOpen"
        class="sidebar-overlay"
        @click="sidebarOpen = false"
      ></div>
      <aside class="app-sidebar">
        <SideMenu />
      </aside>

      <main class="app-main">
        <RouterView />
      </main>
    </div>

    <footer class="app-footer">
      <span>ダイウン工業株式会社 / 王 素柱</span>
      <span>データベース: DMSP</span>
      <button class="logout-btn">F12: ログアウト</button>
    </footer>
  </div>
</template>

<script setup>
import { computed, onMounted, onBeforeUnmount, ref, watch } from "vue";
import { RouterView, useRoute } from "vue-router";
import SideMenu from "./components/SideMenu.vue";

const todayText = computed(() => {
  const d = new Date();
  const youbi = ["日", "月", "火", "水", "木", "金", "土"][d.getDay()];
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日（${youbi}曜日）`;
});

const route = useRoute();
const isMobile = ref(false);
const sidebarOpen = ref(true);
let mediaQuery = null;

const syncMobileState = () => {
  if (!mediaQuery) return;
  isMobile.value = mediaQuery.matches;
  sidebarOpen.value = !isMobile.value;
};

onMounted(() => {
  mediaQuery = window.matchMedia("(max-width: 768px)");
  syncMobileState();
  mediaQuery.addEventListener("change", syncMobileState);
});

onBeforeUnmount(() => {
  if (mediaQuery) {
    mediaQuery.removeEventListener("change", syncMobileState);
  }
});

watch(
  () => route.fullPath,
  () => {
    if (isMobile.value) sidebarOpen.value = false;
  }
);
</script>
