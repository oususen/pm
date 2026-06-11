<template>
  <div class="manual-page">
    <aside class="manual-nav">
      <div class="manual-nav-header">マニュアル</div>
      <div class="manual-nav-body">
        <div v-for="section in manualSections" :key="section.id" class="manual-section">
          <!-- トップセクションは常に表示 -->
          <template v-if="section.id === 'top'">
            <ul class="section-list">
              <li v-for="item in section.items" :key="item.path">
                <RouterLink
                  class="section-link"
                  :class="{ active: item.path === currentPath }"
                  :to="{ path: '/manual', query: { path: item.path } }"
                >
                  {{ item.title }}
                </RouterLink>
              </li>
            </ul>
          </template>
          <!-- 他のセクションは折りたたみ可能 -->
          <template v-else>
            <div
              class="section-title"
              :class="{ expanded: expandedSections[section.id] }"
              @click="toggleSection(section.id)"
            >
              <span class="section-toggle">{{ expandedSections[section.id] ? '▼' : '▶' }}</span>
              {{ section.title }}
            </div>
            <ul v-show="expandedSections[section.id]" class="section-list">
              <li v-for="item in section.items" :key="item.path">
                <RouterLink
                  class="section-link"
                  :class="{ active: item.path === currentPath }"
                  :to="{ path: '/manual', query: { path: item.path } }"
                >
                  {{ item.title }}
                </RouterLink>
              </li>
            </ul>
          </template>
        </div>
      </div>
    </aside>

    <section class="manual-content">
      <div class="manual-header">
        <div>
          <h1 class="manual-title">{{ currentTitle }}</h1>
          <div class="manual-path">{{ currentPath }}</div>
        </div>
        <div class="manual-actions">
          <button class="btn-secondary" @click="openInNewTab">
            新しいタブで開く
          </button>
        </div>
      </div>

      <div v-if="loading" class="manual-state">読込中...</div>
      <div v-else-if="error" class="manual-state error">{{ error }}</div>
      <article
        v-else
        class="manual-body"
        v-html="renderedHtml"
        @click="onContentClick"
      ></article>
    </section>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { manualLookup, manualSections } from '@/manual/manualIndex'

const route = useRoute()
const router = useRouter()
const markdown = ref('')
const loading = ref(false)
const error = ref('')

// セクションの折りたたみ状態（デフォルトは全て閉じる）
const expandedSections = ref({})

const toggleSection = (sectionId) => {
  expandedSections.value[sectionId] = !expandedSections.value[sectionId]
}

// 現在のパスに応じてセクションを自動展開
const expandCurrentSection = () => {
  const lookup = manualLookup[currentPath.value]
  if (lookup?.sectionId) {
    expandedSections.value[lookup.sectionId] = true
  }
}

const normalizeQueryPath = (value) => {
  const raw = Array.isArray(value) ? value[0] : value
  if (!raw) return ''
  const trimmed = String(raw).trim()
  if (!trimmed) return ''
  if (!/%[0-9A-Fa-f]{2}/.test(trimmed)) return trimmed
  try {
    return decodeURIComponent(trimmed)
  } catch {
    return trimmed
  }
}

const normalizePath = (path) => {
  const parts = String(path || '').split('/')
  const stack = []
  parts.forEach((part) => {
    if (!part || part === '.') return
    if (part === '..') {
      stack.pop()
      return
    }
    stack.push(part)
  })
  return stack.join('/')
}

const currentPath = computed(() => {
  const raw = normalizeQueryPath(route.query.path)
  const normalized = normalizePath(raw)
  return normalized || 'README.md'
})

const currentTitle = computed(() => {
  return manualLookup[currentPath.value]?.title || 'マニュアル'
})

const currentDir = computed(() => {
  const parts = currentPath.value.split('/')
  parts.pop()
  return parts.join('/')
})

const buildFetchUrl = (path) => {
  const normalized = normalizePath(path)
  const segments = normalized.split('/').filter(Boolean).map(encodeURIComponent)
  return `/manual/${segments.join('/')}`
}

const resolveRelativePath = (href) => {
  if (!href) return ''
  if (href.startsWith('http://') || href.startsWith('https://')) return href
  if (href.startsWith('data:') || href.startsWith('#')) return href
  if (href.startsWith('/')) return href
  const merged = currentDir.value ? `${currentDir.value}/${href}` : href
  return normalizePath(merged)
}

const renderer = computed(() => {
  const custom = new marked.Renderer()
  custom.image = (href, title, text) => {
    const resolved = resolveRelativePath(href || '')
    const src = resolved ? buildFetchUrl(resolved) : ''
    const titleAttr = title ? ` title="${title}"` : ''
    const altAttr = text ? ` alt="${text}"` : ' alt=""'
    return `<img src="${src}"${altAttr}${titleAttr} />`
  }
  custom.link = (href, title, text) => {
    const resolved = resolveRelativePath(href || '')
    const isMarkdown = resolved && resolved.endsWith('.md')
    const target = isMarkdown ? `/manual?path=${encodeURIComponent(resolved)}` : resolved
    const titleAttr = title ? ` title="${title}"` : ''
    return `<a href="${target}"${titleAttr}>${text}</a>`
  }
  return custom
})

const renderedHtml = computed(() => {
  if (!markdown.value) return ''
  const rawHtml = marked.parse(markdown.value, {
    renderer: renderer.value,
    breaks: true,
  })
  return DOMPurify.sanitize(rawHtml)
})

const loadMarkdown = async () => {
  loading.value = true
  error.value = ''
  try {
    const res = await fetch(buildFetchUrl(currentPath.value))
    if (!res.ok) {
      throw new Error(`読み込みに失敗しました: ${res.status}`)
    }
    markdown.value = await res.text()
  } catch (err) {
    markdown.value = ''
    error.value = err?.message || '読み込みに失敗しました'
  } finally {
    loading.value = false
  }
}

const onContentClick = (event) => {
  const anchor = event.target?.closest?.('a')
  if (!anchor) return
  const href = anchor.getAttribute('href') || ''
  if (!href || href.startsWith('http')) return
  if (href.startsWith('/manual?path=')) {
    event.preventDefault()
    const nextPath = href.replace('/manual?path=', '')
    router.push({ path: '/manual', query: { path: decodeURIComponent(nextPath) } })
  }
}

const openInNewTab = () => {
  const encoded = currentPath.value
    .split('/')
    .filter(Boolean)
    .map(encodeURIComponent)
    .join('/')
  window.open(`/manual?path=${encoded}`, '_blank', 'noopener')
}

watch(currentPath, () => {
  loadMarkdown()
  expandCurrentSection()
}, { immediate: true })
</script>

<style scoped>
.manual-page {
  display: grid;
  grid-template-columns: 260px 1fr;
  gap: 16px;
  padding: 16px;
  min-height: calc(100vh - 120px);
  background: #f8fafc;
}

.manual-nav {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 12px;
  height: fit-content;
  position: sticky;
  top: 70px;
}

.manual-nav-header {
  font-weight: 700;
  font-size: 16px;
  margin-bottom: 10px;
}

.manual-nav-body {
  max-height: calc(100vh - 170px);
  overflow-y: auto;
  padding-right: 4px;
}

.manual-section + .manual-section {
  margin-top: 12px;
}

.section-title {
  font-size: 13px;
  font-weight: 700;
  color: #475569;
  margin-bottom: 6px;
  cursor: pointer;
  padding: 6px 8px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  gap: 6px;
  user-select: none;
}

.section-title:hover {
  background: #f1f5f9;
}

.section-toggle {
  font-size: 10px;
  color: #94a3b8;
}

.section-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: 4px;
}

.section-link {
  display: block;
  padding: 6px 8px;
  border-radius: 6px;
  color: #1f2937;
  text-decoration: none;
  font-size: 13px;
}

.section-link:hover {
  background: #eef2ff;
}

.section-link.active {
  background: #2563eb;
  color: #fff;
}

.manual-content {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 16px;
  min-width: 0;
}

.manual-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  border-bottom: 1px solid #e5e7eb;
  padding-bottom: 12px;
  margin-bottom: 16px;
}

.manual-title {
  margin: 0 0 4px 0;
  font-size: 20px;
}

.manual-path {
  font-size: 12px;
  color: #64748b;
}

.manual-actions {
  display: flex;
  gap: 8px;
}

.btn-secondary {
  padding: 6px 10px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  background: #f8fafc;
  cursor: pointer;
  font-size: 12px;
}

.manual-state {
  color: #64748b;
  font-size: 14px;
}

.manual-state.error {
  color: #dc2626;
}

.manual-body {
  color: #111827;
  line-height: 1.7;
  font-size: 14px;
}

.manual-body :deep(h1),
.manual-body :deep(h2),
.manual-body :deep(h3) {
  margin-top: 24px;
  margin-bottom: 10px;
}

.manual-body :deep(p) {
  margin: 10px 0;
}

.manual-body :deep(ul),
.manual-body :deep(ol) {
  padding-left: 20px;
}

.manual-body :deep(code) {
  background: #f1f5f9;
  padding: 2px 4px;
  border-radius: 4px;
  font-size: 13px;
}

.manual-body :deep(pre) {
  background: #f1f5f9;
  color: #1e293b;
  padding: 12px;
  border-radius: 8px;
  overflow: auto;
}

.manual-body :deep(pre code) {
  background: transparent;
  padding: 0;
  color: inherit;
}

.manual-body :deep(a) {
  color: #2563eb;
  text-decoration: underline;
}

.manual-body :deep(img) {
  max-width: 100%;
  display: block;
  margin: 12px 0;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

@media (max-width: 960px) {
  .manual-page {
    grid-template-columns: 1fr;
  }

  .manual-nav {
    position: static;
  }
}
</style>

