<template>
  <div class="master-menu">
    <div class="page-header">
      <h2 class="page-title">負荷計算</h2>
      <DataSourceDialog title="負荷計算" :sources="dsSources" />
    </div>
    <div class="master-grid">
      <RouterLink
        v-for="tile in tiles"
        :key="tile.to"
        :to="tile.to"
        class="master-tile"
      >
        <div class="icon-box">{{ tile.icon }}</div>
        <div class="label">{{ tile.label }}</div>
        <div class="desc">{{ tile.desc }}</div>
      </RouterLink>
    </div>
  </div>
</template>

<script setup>
import { RouterLink } from 'vue-router'
import DataSourceDialog from '@/components/DataSourceDialog.vue'

const tiles = [
  {
    to: '/production/actual-cycle-time',
    icon: '⏱',
    label: '出来高集計',
    desc: '実績からサイクル時間を計算・BOM展開で完成品CTを算出',
  },
  {
    to: '/production/line-cycle-time',
    icon: '⏱',
    label: 'ラインサイクルタイム',
    desc: '長期負荷計算用のサイクルタイム(秒/個)を登録',
  },
  {
    to: '/production/line-load-chart',
    icon: '📉',
    label: '長期負荷チャート',
    desc: 'ライン別の負荷率を日・週・月単位で表示',
  },
]

const dsSources = [
  { section: '出来高集計' },
  { op: '実績読み取り', table: 't_process_work_session', desc: '工程作業セッション（タンク・組立等）' },
  { op: '実績読み取り', table: 'brake_line_record', desc: 'ブレーキ・スポット作業記録' },
  { op: '計算結果 保存', table: 't_actual_cycle_time', desc: '子部品の実績サイクル時間' },
  { op: '計算結果 保存', table: 't_finished_product_cycle_time', desc: '完成品サイクル時間（BOM展開後）' },
  { op: 'BOM展開', table: 'm_bom / m_bom_item', desc: '部品構成（逆展開で完成品を特定）' },
  { section: 'ラインサイクルタイム' },
  { op: '読み書き', table: 'm_line_cycle_time', desc: '長期負荷計算用CT（秒/個）' },
  { op: '参照', table: 'm_routing_step', desc: 'ルーティングから完成品×工程を抽出' },
  { section: '長期負荷チャート' },
  { op: '負荷計算', table: 'm_line_cycle_time × t_line_demand', desc: 'CT × 需要数量 = 負荷時間' },
]
</script>

<style scoped>
.master-menu { padding: 16px; }
.page-header { display: flex; align-items: center; gap: 8px; margin-bottom: 16px; }
.page-title { font-size: 18px; font-weight: 700; margin: 0; }
.master-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}
.master-tile {
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 16px;
  text-decoration: none;
  color: inherit;
  background: #fff;
  display: grid;
  gap: 6px;
  align-content: start;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04);
  transition: box-shadow 0.15s;
}
.master-tile:hover { box-shadow: 0 6px 16px rgba(0, 0, 0, 0.1); }
.master-tile .icon-box { font-size: 24px; }
.master-tile .label { font-weight: 700; font-size: 14px; }
.master-tile .desc { font-size: 12px; color: #64748b; }

@media (max-width: 800px) {
  .master-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 520px) {
  .master-grid { grid-template-columns: 1fr; }
}
</style>
