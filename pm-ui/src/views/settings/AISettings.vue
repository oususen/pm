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
        <label class="check-line"><input v-model="dataPolicy.allow_external_image_transfer" :disabled="!canEdit" type="checkbox" @change="saveDataPolicy" /> 添付画像・PDFをOpenRouterへ送信して内容を判定する</label>
        <label>外部送信する最大集計行数
          <input v-model.number="dataPolicy.max_external_result_rows" :disabled="!canEdit" type="number" min="1" max="100" @change="saveDataPolicy" />
        </label>
        <label>会話履歴の保存期間（日・0は無期限）
          <input v-model.number="dataPolicy.conversation_retention_days" :disabled="!canEdit" type="number" min="0" max="3650" @change="saveDataPolicy" />
        </label>
        <p>画像は利用者が添付した時だけ、OpenRouterの画像対応モデルへ縮小して送信します。PDFは先頭3ページを画像化して一時送信します。個人別集計は画面権限とこの設定の両方が有効な場合だけ利用できます。</p>
      </div>
    </section>

    <section class="setting-section">
      <h3>分析実行設定</h3>
      <p class="section-help">分析機能の実装後、次に開始する分析から適用します。取得行数の上限を超えた場合は、対象の期間・条件を絞って再実行します。</p>
      <form v-if="analysisExecutionPolicy" @submit.prevent="saveAnalysisExecutionPolicy">
        <div class="policy-grid execution-policy-grid">
          <label v-for="field in executionFields" :key="field.key" :for="`analysis-setting-${field.key}`">
            {{ field.label }}
            <input :id="`analysis-setting-${field.key}`" v-model.number="analysisExecutionPolicy[field.key]"
              :disabled="!canEdit || loading || savingExecutionPolicy" type="number" required
              :min="field.min" :max="field.max" :step="field.step"
              :aria-invalid="Boolean(executionErrors[field.key])" :aria-describedby="`analysis-help-${field.key}`" />
            <small :id="`analysis-help-${field.key}`">{{ field.help }}</small>
            <small v-if="executionErrors[field.key]" class="field-error" role="alert">{{ executionErrors[field.key].join(' ') }}</small>
          </label>
        </div>
        <p v-if="executionError" class="error" role="alert">{{ executionError }}</p>
        <p v-if="executionNotice" class="notice" role="status">{{ executionNotice }}</p>
        <button v-if="canEdit" class="reload-button execution-save" type="submit" :disabled="loading || savingExecutionPolicy">
          {{ savingExecutionPolicy ? '保存中…' : '分析実行設定を保存' }}
        </button>
        <p v-else class="section-help">閲覧のみの権限です。</p>
      </form>
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
      <h3>横断参照の定義</h3>
      <p class="section-help">ここで定義した画面の組合せだけ、利用者が質問ごとに「今回だけ許可」できます。AIが任意のテーブル名や列を指定して参照することはできず、各画面のAI用DB辞書にある読み取り専用の列だけが対象です。</p>
      <div v-if="canEdit" class="cross-screen-form">
        <select v-model="newCrossScreen.source_screen_id"><option v-for="screen in screens" :key="screen.id" :value="screen.id">起点: {{ screen.label }}</option></select>
        <select v-model="newCrossScreen.target_screen_id"><option v-for="screen in targetScreenOptions" :key="screen.id" :value="screen.id">追加: {{ screen.label }}</option></select>
        <input v-model.trim="newCrossScreen.purpose" placeholder="利用目的（例: 日別の生産数と残業申請時間を比較）" />
        <label><input v-model="newCrossScreen.allow_external_transfer" type="checkbox" /> 外部AIへ集計結果を送信</label>
        <button class="reload-button" :disabled="!newCrossScreen.purpose || newCrossScreen.source_screen_id === newCrossScreen.target_screen_id" @click="addCrossScreen">組合せを追加</button>
      </div>
      <div class="knowledge-list">
        <label v-for="item in crossScreenAccess" :key="item.id" class="knowledge-row" :class="{ disabled: !item.is_enabled }">
          <span><strong>{{ item.source_screen_label }} × {{ item.target_screen_label }}</strong><small>{{ item.purpose }}</small></span>
          <span class="knowledge-actions"><label><input v-model="item.is_enabled" :disabled="!canEdit" type="checkbox" @change="saveCrossScreen(item)" /> 有効</label><label><input v-model="item.allow_external_transfer" :disabled="!canEdit || !item.is_enabled" type="checkbox" @change="saveCrossScreen(item)" /> 外部送信</label><button v-if="canEdit" class="delete-button" @click.prevent="removeCrossScreen(item)">削除</button></span>
        </label>
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
      <div v-if="canEdit" class="knowledge-upload">
        <select v-model="knowledgeUpload.category">
          <option value="manual">マニュアル</option>
          <option value="procedure">手順書</option>
          <option value="pm_structure">PMアプリ構造</option>
          <option value="security">安全・運用規約</option>
        </select>
        <input v-model.trim="knowledgeUpload.name" placeholder="資料名" />
        <input ref="knowledgeFileInput" type="file" accept=".pdf,.xlsx,.xls,.csv,.tsv,.png,.jpg,.jpeg,.webp,.bmp" @change="selectKnowledgeFile" />
        <button class="reload-button" :disabled="!knowledgeUpload.file || !knowledgeUpload.name" @click="uploadKnowledge">資料を追加</button>
      </div>
      <p class="section-help">PDF、Excel（.xlsx / .xls）、CSV、TSV、画像（PNG / JPG / WEBP / BMP）を15MBまで登録できます。画像はローカルOCRで文字を抽出します。チャットに画像・PDFを添付した時だけ、OpenRouterでは画像そのもの、またはPDF先頭3ページの見た目も内容判定に使えます。</p>
      <div v-if="knowledgeDocuments.length" class="knowledge-list">
        <label v-for="document in knowledgeDocuments" :key="document.id" class="knowledge-row" :class="{ disabled: !document.is_enabled }">
          <span><strong>{{ document.name }}</strong><small>{{ document.file }}<template v-if="document.description"> · {{ document.description }}</template></small></span>
          <span class="knowledge-actions"><label><input v-model="document.is_enabled" :disabled="!canEdit" type="checkbox" @change="saveKnowledgeDocument(document)" /> 有効</label><button v-if="canEdit" class="delete-button" @click.prevent="removeKnowledgeDocument(document)">削除</button></span>
        </label>
      </div>
    </section>

    <section class="setting-section">
      <h3>画像文字認識（OCR）</h3>
      <p class="section-help">AIアプリが画像資料を検索するための文字認識です。Tesseractのコンソール操作は不要です。テスト画像は保存せず、認識結果だけを表示します。</p>
      <div class="ocr-status" :class="{ unavailable: ocrStatus && !ocrStatus.available }">
        <strong>{{ ocrStatus?.available ? '利用可能' : '確認中・利用不可' }}</strong>
        <span>{{ ocrStatus?.message || 'OCRの状態を確認しています。' }}</span>
        <small v-if="ocrStatus?.languages?.length">言語データ: {{ ocrStatus.languages.join(', ') }}</small>
      </div>
      <div v-if="canEdit" class="knowledge-upload">
        <input ref="ocrFileInput" type="file" accept=".png,.jpg,.jpeg,.webp,.bmp" @change="selectOcrFile" />
        <button class="reload-button" :disabled="!ocrTestFile || ocrTesting" @click="runOcrTest">{{ ocrTesting ? '文字認識中…' : 'OCRテスト' }}</button>
      </div>
      <p v-if="ocrTestResult" class="ocr-result"><strong>{{ ocrTestResult.file_name }}（{{ ocrTestResult.character_count }}文字）</strong><br />{{ ocrTestResult.text || '文字を認識できませんでした。画像を大きく・鮮明にしてお試しください。' }}</p>
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
const analysisExecutionPolicy = ref(null)
const savingExecutionPolicy = ref(false)
const executionErrors = ref({})
const executionError = ref('')
const executionNotice = ref('')
const executionFields = [
  { key: 'plan_cache_ttl_minutes', label: '分析案キャッシュ有効期限（分）', min: 5, max: 480, step: 1, help: '5〜480分・1分単位' },
  { key: 'max_execution_seconds', label: 'Python最大実行時間（秒）', min: 30, max: 600, step: 1, help: '30〜600秒・1秒単位' },
  { key: 'max_memory_mb', label: 'Python最大メモリ（MB）', min: 512, max: 4096, step: 128, help: '512〜4096MB・128MB単位' },
  { key: 'max_cpu_cores', label: 'Python CPU上限（コア数）', min: 0.5, max: 2, step: 0.5, help: '0.5〜2コア・0.5コア単位' },
  { key: 'max_fetch_rows', label: '取得行数の上限（行）', min: 1000, max: 100000, step: 1000, help: '1,000〜100,000行・1,000行単位' },
]
const knowledgeSources = ref([])
const knowledgeDocuments = ref([])
const knowledgeFileInput = ref(null)
const knowledgeUpload = ref({ category: 'manual', name: '', file: null })
const ocrStatus = ref(null)
const ocrFileInput = ref(null)
const ocrTestFile = ref(null)
const ocrTestResult = ref(null)
const ocrTesting = ref(false)
const sqlDictionary = ref([])
const crossScreenAccess = ref([])
const screens = [
  { id: 'orders', label: '受注' }, { id: 'production', label: '生産' }, { id: 'quality', label: '品質' },
  { id: 'overtime', label: '勤務' }, { id: 'purchase', label: '仕入' }, { id: 'shipping', label: '出荷' },
  { id: 'inventory', label: '在庫' }, { id: 'masters', label: 'マスタ' },
]
const newCrossScreen = ref({ source_screen_id: 'production', target_screen_id: 'quality', purpose: '', allow_external_transfer: true })
const loading = ref(false)
const error = ref('')
const notice = ref('')
const canEdit = computed(() => hasPermission(authState.user, 'settings.ai', 'edit'))

const screenOrder = ['ai_home', 'orders', 'production', 'quality', 'overtime', 'purchase', 'shipping', 'inventory', 'masters']
const toolGroups = computed(() => screenOrder
  .map((screenId) => {
    const items = tools.value.filter((tool) => tool.screen_id === screenId)
    return { screenId, label: items[0]?.screen_label || '', items }
  })
  .filter((group) => group.items.length))
const targetScreenOptions = computed(() => screens.filter((screen) => screen.id !== newCrossScreen.value.source_screen_id))

const kindLabel = (kind) => ({ master: 'マスタ参照', aggregate: '集計', personal: '個人別集計', sql: '読み取りSQL' }[kind] || kind)
const saved = (message) => { notice.value = message; setTimeout(() => { notice.value = '' }, 2500) }
const failed = (requestError) => { error.value = requestError.response?.data?.detail || 'AI設定の保存に失敗しました。' }

const load = async () => {
  loading.value = true
  error.value = ''
  try {
    const [providerResponse, toolResponse, policyResponse, knowledgeResponse, documentResponse, dictionaryResponse, ocrResponse, crossScreenResponse, executionPolicyResponse] = await Promise.all([
      api.aiSettings.providers(), api.aiSettings.tools(), api.aiSettings.dataPolicy(), api.aiSettings.knowledgeSources(), api.aiSettings.knowledgeDocuments(), api.aiSettings.sqlDictionary(), api.ocr.status(), api.aiSettings.crossScreenAccess(),
      api.aiSettings.analysisExecutionPolicy(),
    ])
    providers.value = providerResponse.data
    tools.value = toolResponse.data
    dataPolicy.value = policyResponse.data
    analysisExecutionPolicy.value = executionPolicyResponse.data
    executionErrors.value = {}
    executionError.value = ''
    executionNotice.value = ''
    knowledgeSources.value = knowledgeResponse.data
    knowledgeDocuments.value = documentResponse.data
    sqlDictionary.value = dictionaryResponse.data
    ocrStatus.value = ocrResponse.data.tesseract
    crossScreenAccess.value = crossScreenResponse.data.results || crossScreenResponse.data
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
const saveAnalysisExecutionPolicy = async () => {
  if (!canEdit.value || loading.value || savingExecutionPolicy.value) return
  executionErrors.value = {}
  executionError.value = ''
  executionNotice.value = ''
  savingExecutionPolicy.value = true
  try {
    const payload = Object.fromEntries(executionFields.map(field => [field.key, analysisExecutionPolicy.value[field.key]]))
    const { data } = await api.aiSettings.updateAnalysisExecutionPolicy(payload)
    analysisExecutionPolicy.value = data
    executionNotice.value = '分析実行設定を保存しました。'
  } catch (requestError) {
    const response = requestError.response?.data
    executionErrors.value = Object.fromEntries(executionFields
      .filter(field => response?.[field.key])
      .map(field => [field.key, [response[field.key]].flat()]))
    executionError.value = response?.detail || '分析実行設定を保存できませんでした。入力値を確認してください。'
  } finally {
    savingExecutionPolicy.value = false
  }
}
const saveKnowledge = async (item) => {
  try { await api.aiSettings.updateKnowledgeSource(item.id, { is_enabled: item.is_enabled }); saved('ナレッジ設定を保存しました。') } catch (requestError) { failed(requestError); await load() }
}
const selectKnowledgeFile = (event) => { knowledgeUpload.value.file = event.target.files?.[0] || null }
const selectOcrFile = (event) => { ocrTestFile.value = event.target.files?.[0] || null; ocrTestResult.value = null }
const runOcrTest = async () => {
  const form = new FormData()
  form.append('image', ocrTestFile.value)
  ocrTesting.value = true
  try {
    const { data } = await api.ocr.recognize(form)
    ocrTestResult.value = data
    saved(data.message)
  } catch (requestError) { failed(requestError) } finally { ocrTesting.value = false }
}
const uploadKnowledge = async () => {
  const form = new FormData()
  form.append('category', knowledgeUpload.value.category)
  form.append('name', knowledgeUpload.value.name)
  form.append('file', knowledgeUpload.value.file)
  try {
    await api.aiSettings.createKnowledgeDocument(form)
    knowledgeUpload.value = { category: 'manual', name: '', file: null }
    if (knowledgeFileInput.value) knowledgeFileInput.value.value = ''
    saved('AIナレッジ資料を追加しました。')
    await load()
  } catch (requestError) { failed(requestError) }
}
const saveKnowledgeDocument = async (item) => {
  try { await api.aiSettings.updateKnowledgeDocument(item.id, { is_enabled: item.is_enabled }); saved('ナレッジ資料の設定を保存しました。') } catch (requestError) { failed(requestError); await load() }
}
const removeKnowledgeDocument = async (item) => {
  try { await api.aiSettings.deleteKnowledgeDocument(item.id); saved('AIナレッジ資料を削除しました。'); await load() } catch (requestError) { failed(requestError) }
}
const addCrossScreen = async () => {
  try {
    await api.aiSettings.createCrossScreenAccess(newCrossScreen.value)
    newCrossScreen.value = { source_screen_id: 'production', target_screen_id: 'quality', purpose: '', allow_external_transfer: true }
    saved('横断参照の組合せを追加しました。')
    await load()
  } catch (requestError) { failed(requestError) }
}
const saveCrossScreen = async (item) => {
  try {
    await api.aiSettings.updateCrossScreenAccess(item.id, { is_enabled: item.is_enabled, allow_external_transfer: item.allow_external_transfer })
    saved('横断参照の設定を保存しました。')
  } catch (requestError) { failed(requestError); await load() }
}
const removeCrossScreen = async (item) => {
  try { await api.aiSettings.deleteCrossScreenAccess(item.id); saved('横断参照の組合せを削除しました。'); await load() } catch (requestError) { failed(requestError) }
}

load()
</script>

<style scoped>
.ai-settings{max-width:1180px;padding:14px 16px;margin:0 auto;color:#334155}.page-header{display:flex;justify-content:space-between;align-items:start;gap:16px}.page-header h2{margin:0;font-size:19px}.page-header p,.section-help,.policy-grid p{margin:5px 0 0;font-size:12px;line-height:1.6;color:#64748b}.reload-button{border:1px solid #93bfb5;background:#fff;color:#147a6d;border-radius:6px;padding:5px 11px;cursor:pointer}.setting-section{margin-top:15px;padding:13px;border:1px solid #dce8e5;border-radius:10px;background:#fff}.setting-section h3{margin:0 0 9px;font-size:14px;color:#176b60}.provider-grid,.policy-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.setting-card,.policy-grid{padding:10px;border-radius:7px;background:#f7fbfa}.card-title,.tool-row,.knowledge-row{display:flex;align-items:center;justify-content:space-between;gap:10px}.setting-card label{display:grid;gap:4px;margin-top:7px;font-size:11px}.setting-card select,.policy-grid input[type=number]{border:1px solid #cdded9;border-radius:5px;padding:5px;background:white}.setting-card small,.tool-row small,.knowledge-row small{display:block;margin-top:3px;font-size:10px;color:#73878a}.check-line{font-size:12px}.tool-group{margin-top:10px}.tool-group h4{margin:0;padding:6px 8px;background:#eef7f5;font-size:12px}.tool-list,.knowledge-list{border:1px solid #e1ece9}.tool-row,.knowledge-row{padding:7px 9px;border-bottom:1px solid #e8efed;font-size:12px}.tool-row:last-child,.knowledge-row:last-child{border-bottom:0}.tool-actions{display:flex;gap:10px;font-size:11px;white-space:nowrap}.dictionary-screen{margin-top:6px;border:1px solid #e1ece9;border-radius:6px;padding:7px;font-size:12px}.dictionary-screen summary{cursor:pointer;font-weight:700;color:#356c66}.dictionary-table{display:grid;gap:2px;padding:7px 3px;border-top:1px solid #edf2f1}.dictionary-table:first-of-type{margin-top:7px}.dictionary-table small{font-family:Consolas,monospace;font-size:10px;color:#687d81;word-break:break-all}.disabled{opacity:.48}.notice,.error{margin:9px 0;padding:7px 10px;border-radius:6px;font-size:12px}.notice{background:#e9f8f1;color:#237765}.error{background:#fff1ee;color:#ae5146}@media(max-width:760px){.provider-grid,.policy-grid{grid-template-columns:1fr}.tool-row{align-items:start;flex-direction:column}.tool-actions{width:100%;justify-content:space-between}}
.knowledge-actions,.knowledge-upload{display:flex;gap:10px;font-size:11px;white-space:nowrap}.knowledge-upload{margin-top:10px;align-items:center;flex-wrap:wrap}.knowledge-upload select,.knowledge-upload input{border:1px solid #cdded9;border-radius:5px;padding:5px;background:#fff}.delete-button{border:1px solid #f0b7ae;background:#fff;color:#b04c40;border-radius:5px;padding:3px 7px;cursor:pointer}
.cross-screen-form{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:10px 0}.cross-screen-form select,.cross-screen-form input{border:1px solid #cdded9;border-radius:5px;padding:5px;background:#fff;font-size:11px}.cross-screen-form input[type=text]{min-width:280px}.cross-screen-form label{font-size:11px}
.ocr-status{display:grid;gap:3px;margin-top:9px;padding:8px 10px;border:1px solid #b8ded3;border-radius:7px;background:#eef9f5;font-size:12px;color:#176b60}.ocr-status small{color:#5c7772}.ocr-status.unavailable{border-color:#efc7bd;background:#fff4f1;color:#ad5548}.ocr-result{white-space:pre-wrap;max-height:260px;overflow:auto;margin:10px 0 0;padding:9px;border:1px solid #e1ece9;border-radius:7px;background:#f8fbfa;font-size:12px;line-height:1.6}
.execution-policy-grid label{display:grid;gap:4px;font-size:12px}.execution-policy-grid small{font-size:11px;color:#64748b}.execution-policy-grid .field-error{color:#ae5146}.execution-save{margin-top:10px}
</style>
