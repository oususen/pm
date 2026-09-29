<template>
  <div class="ai-settings">
    <header class="page-header">
      <div>
        <h2>AI設定</h2>
        <p>社内AIで利用するプロバイダ、画面別ツール、外部送信範囲、ナレッジを管理します。</p>
      </div>
      <button class="reload-button" :disabled="loading" @click="load">更新</button>
    </header>

    <p v-if="error" class="error">{{ error }}</p>
    <p v-if="notice" class="notice">{{ notice }}</p>

    <section class="setting-section">
      <h3>AIプロバイダ・モデル</h3>
      <div class="provider-grid">
        <article v-for="item in providers" :key="item.id" class="setting-card" :class="{ disabled: !item.is_enabled }">
          <div class="card-title"><strong>{{ item.label }}</strong><label><input v-model="item.is_enabled" :disabled="!canEdit" type="checkbox" @change="saveProvider(item)" /> 有効</label></div>
          <label>既定モデル
            <select v-model="item.default_model" :disabled="!canEdit" @change="saveProvider(item)">
              <option v-for="model in item.models" :key="model.id" :value="model.id">{{ model.label }}</option>
            </select>
          </label>
          <small>認証情報はここには保存せず、サーバーの環境変数で管理します。</small>
        </article>
      </div>
    </section>

    <section class="setting-section">
      <h3>外部送信・個人情報</h3>
      <div v-if="dataPolicy" class="policy-grid">
        <label class="check-line"><input v-model="dataPolicy.allow_aggregated_external_transfer" :disabled="!canEdit" type="checkbox" @change="saveDataPolicy" /> DeepSeekへ集計結果を送信する</label>
        <label class="check-line"><input v-model="dataPolicy.allow_authorized_personal_data" :disabled="!canEdit" type="checkbox" @change="saveDataPolicy" /> 権限を持つ利用者の個人別集計を許可する</label>
        <label>外部送信する最大集計行数
          <input v-model.number="dataPolicy.max_external_result_rows" :disabled="!canEdit" type="number" min="1" max="100" @change="saveDataPolicy" />
        </label>
        <p>氏名・ログインID・連絡先・未集計明細は外部送信しません。個人別集計は画面権限とこの設定の両方が有効な場合だけ利用できます。</p>
      </div>
    </section>

    <section class="setting-section">
      <h3>画面別に利用できるAIツール</h3>
      <p class="section-help">この一覧の有効なツールだけをAIへ提示します。任意SQLや任意テーブル検索を追加する設定ではありません。</p>
      <div v-for="group in toolGroups" :key="group.screenId" class="tool-group">
        <h4>{{ group.label }}</h4>
        <div class="tool-list">
          <label v-for="tool in group.items" :key="tool.id" class="tool-row" :class="{ disabled: !tool.is_enabled }">
            <span><strong>{{ tool.tool_label }}</strong><small>{{ kindLabel(tool.tool_kind) }}</small></span>
            <span class="tool-actions">
              <label><input v-model="tool.is_enabled" :disabled="!canEdit" type="checkbox" @change="saveTool(tool)" /> 利用</label>
              <label><input v-model="tool.allow_external_transfer" type="checkbox" :disabled="!tool.is_enabled || !canEdit" @change="saveTool(tool)" /> DeepSeekへ送信</label>
            </span>
          </label>
        </div>
      </div>
    </section>

    <section class="setting-section">
      <h3>AIナレッジ</h3>
      <p class="section-help">有効な区分だけを、質問と起点画面に応じてRAG検索します。正式原本は仕様書とマニュアルで管理し、回答には参照したファイルを根拠として表示します。</p>
      <div class="knowledge-list">
        <label v-for="source in knowledgeSources" :key="source.id" class="knowledge-row" :class="{ disabled: !source.is_enabled }">
          <span><strong>{{ source.name }}</strong><small>{{ source.relative_path }}<template v-if="source.description"> · {{ source.description }}</template></small></span>
          <span><input v-model="source.is_enabled" :disabled="!canEdit" type="checkbox" @change="saveKnowledge(source)" /> 有効</span>
        </label>
      </div>
    </section>

    <section class="setting-section">
      <h3>AI用DB辞書（読み取りSQL）</h3>
      <p class="section-help">ここに表示されたテーブル・列だけをLLMがSELECTで参照できます。「個人情報列」は権限を持つ利用者だけに公開され、DeepSeekへは一時IDに置き換えて送信します。</p>
      <details v-for="screen in sqlDictionary" :key="screen.screen_id" class="dictionary-screen">
        <summary>{{ screen.screen_label }}（{{ screen.tables.length }}テーブル）</summary>
        <div v-for="table in screen.tables" :key="table.table" class="dictionary-table">
          <strong>{{ table.table }}</strong>
          <small>通常列: {{ table.columns.join(', ') || 'なし' }}</small>
          <small v-if="table.personal_columns.length">個人情報列（権限者）: {{ table.personal_columns.join(', ') }}</small>
        </div>
      </details>
    </section>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import api from '@/api/client'
import { authState } from '@/auth'
import { hasPermission } from '@/router'

const providers = ref([])
const tools = ref([])
const dataPolicy = ref(null)
const knowledgeSources = ref([])
const sqlDictionary = ref([])
const loading = ref(false)
const error = ref('')
const notice = ref('')
const canEdit = computed(() => hasPermission(authState.user, 'settings.ai', 'edit'))

const screenOrder = ['ai_home', 'orders', 'production', 'quality', 'overtime', 'purchase', 'shipping', 'inventory']
const toolGroups = computed(() => screenOrder
  .map((screenId) => {
    const items = tools.value.filter((tool) => tool.screen_id === screenId)
    return { screenId, label: items[0]?.screen_label || '', items }
  })
  .filter((group) => group.items.length))

const kindLabel = (kind) => ({ master: 'マスタ参照', aggregate: '集計', personal: '個人別集計', sql: '読み取りSQL' }[kind] || kind)
const saved = (message) => { notice.value = message; setTimeout(() => { notice.value = '' }, 2500) }
const failed = (requestError) => { error.value = requestError.response?.data?.detail || 'AI設定の保存に失敗しました。' }

const load = async () => {
  loading.value = true
  error.value = ''
  try {
    const [providerResponse, toolResponse, policyResponse, knowledgeResponse, dictionaryResponse] = await Promise.all([
      api.aiSettings.providers(), api.aiSettings.tools(), api.aiSettings.dataPolicy(), api.aiSettings.knowledgeSources(), api.aiSettings.sqlDictionary(),
    ])
    providers.value = providerResponse.data
    tools.value = toolResponse.data
    dataPolicy.value = policyResponse.data
    knowledgeSources.value = knowledgeResponse.data
    sqlDictionary.value = dictionaryResponse.data
  } catch (requestError) {
    failed(requestError)
  } finally {
    loading.value = false
  }
}

const saveProvider = async (item) => {
  try { await api.aiSettings.updateProvider(item.id, { is_enabled: item.is_enabled, default_model: item.default_model }); saved('プロバイダ設定を保存しました。') } catch (requestError) { failed(requestError); await load() }
}
const saveTool = async (item) => {
  try { await api.aiSettings.updateTool(item.id, { is_enabled: item.is_enabled, allow_external_transfer: item.allow_external_transfer }); saved('ツール設定を保存しました。') } catch (requestError) { failed(requestError); await load() }
}
const saveDataPolicy = async () => {
  try { const { data } = await api.aiSettings.updateDataPolicy(dataPolicy.value); dataPolicy.value = data; saved('データ送信設定を保存しました。') } catch (requestError) { failed(requestError); await load() }
}
const saveKnowledge = async (item) => {
  try { await api.aiSettings.updateKnowledgeSource(item.id, { is_enabled: item.is_enabled }); saved('ナレッジ設定を保存しました。') } catch (requestError) { failed(requestError); await load() }
}

load()
</script>

<style scoped>
.ai-settings{max-width:1180px;padding:14px 16px;margin:0 auto;color:#334155}.page-header{display:flex;justify-content:space-between;align-items:start;gap:16px}.page-header h2{margin:0;font-size:19px}.page-header p,.section-help,.policy-grid p{margin:5px 0 0;font-size:12px;line-height:1.6;color:#64748b}.reload-button{border:1px solid #93bfb5;background:#fff;color:#147a6d;border-radius:6px;padding:5px 11px;cursor:pointer}.setting-section{margin-top:15px;padding:13px;border:1px solid #dce8e5;border-radius:10px;background:#fff}.setting-section h3{margin:0 0 9px;font-size:14px;color:#176b60}.provider-grid,.policy-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.setting-card,.policy-grid{padding:10px;border-radius:7px;background:#f7fbfa}.card-title,.tool-row,.knowledge-row{display:flex;align-items:center;justify-content:space-between;gap:10px}.setting-card label{display:grid;gap:4px;margin-top:7px;font-size:11px}.setting-card select,.policy-grid input[type=number]{border:1px solid #cdded9;border-radius:5px;padding:5px;background:white}.setting-card small,.tool-row small,.knowledge-row small{display:block;margin-top:3px;font-size:10px;color:#73878a}.check-line{font-size:12px}.tool-group{margin-top:10px}.tool-group h4{margin:0;padding:6px 8px;background:#eef7f5;font-size:12px}.tool-list,.knowledge-list{border:1px solid #e1ece9}.tool-row,.knowledge-row{padding:7px 9px;border-bottom:1px solid #e8efed;font-size:12px}.tool-row:last-child,.knowledge-row:last-child{border-bottom:0}.tool-actions{display:flex;gap:10px;font-size:11px;white-space:nowrap}.dictionary-screen{margin-top:6px;border:1px solid #e1ece9;border-radius:6px;padding:7px;font-size:12px}.dictionary-screen summary{cursor:pointer;font-weight:700;color:#356c66}.dictionary-table{display:grid;gap:2px;padding:7px 3px;border-top:1px solid #edf2f1}.dictionary-table:first-of-type{margin-top:7px}.dictionary-table small{font-family:Consolas,monospace;font-size:10px;color:#687d81;word-break:break-all}.disabled{opacity:.48}.notice,.error{margin:9px 0;padding:7px 10px;border-radius:6px;font-size:12px}.notice{background:#e9f8f1;color:#237765}.error{background:#fff1ee;color:#ae5146}@media(max-width:760px){.provider-grid,.policy-grid{grid-template-columns:1fr}.tool-row{align-items:start;flex-direction:column}.tool-actions{width:100%;justify-content:space-between}}
</style>
