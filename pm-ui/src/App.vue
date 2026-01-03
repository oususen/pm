<template>
  <div class="app-root">
    <!-- グローバルナビゲーション -->
    <GlobalNavigation :is-mobile="isMobile" :today-text="todayText" />

    <div class="app-body">
      <main class="app-main">
        <RouterView />
      </main>
    </div>

    <footer class="app-footer">
      <span>ダイウン工業株式会社 / 王 崇栓</span>
      <span>データベース: DMSP</span>
      <button class="logout-btn">F12: ログアウト</button>
    </footer>
  </div>
</template>

<script setup>
import { computed, onMounted, onBeforeUnmount, ref } from "vue";
import { RouterView } from "vue-router";
import GlobalNavigation from "./components/GlobalNavigation.vue";

const todayText = computed(() => {
  const d = new Date();
  const youbi = ["日", "月", "火", "水", "木", "金", "土"][d.getDay()];
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日（${youbi}曜日）`;
});

const isMobile = ref(false);
let mediaQuery = null;

const syncMobileState = () => {
  if (!mediaQuery) return;
  isMobile.value = mediaQuery.matches;
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
</script>
