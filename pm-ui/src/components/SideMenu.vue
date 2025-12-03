<template>
  <nav class="side-menu">
    <div class="side-section">
      <div class="side-section-title">受注管理</div>
      <ul>
        <li>受注入力</li>
        <li>受注一覧</li>
      </ul>
    </div>

    <div class="side-section">
      <div class="side-section-title">出荷管理</div>
      <ul>
        <li>出荷指示</li>
        <li>出荷実績</li>
      </ul>
    </div>

    <div class="side-section">
      <div class="side-section-title">生産管理</div>
      <ul>
        <li>生産計画</li>
        <li>進捗管理</li>
      </ul>
    </div>

    <div class="side-section">
      <div class="side-section-title">品質管理</div>
      <ul>
        <li>検査実績</li>
      </ul>
    </div>

    <div class="side-section">
      <div class="side-section-title">マスタメンテ</div>
      <ul>
        <li>
          <RouterLink to="/masters" class="link">マスタメニュー</RouterLink>
        </li>
      </ul>
    </div>
  </nav>
</template>

<script setup>
import { RouterLink } from "vue-router";
</script>
