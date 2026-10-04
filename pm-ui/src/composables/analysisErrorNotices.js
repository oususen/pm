import { computed, hasInjectionContext, inject, onScopeDispose, provide, shallowRef } from 'vue'

const ERROR_HOST = Symbol('analysis-error-host')

// 分析・実行・履歴のエラーを同じ帯へ集める。元のrefとクリア時点は変えない。
export function useAnalysisErrorNotices(errors, createHost = false) {
  const inComponent = hasInjectionContext()
  const inherited = !createHost && inComponent ? inject(ERROR_HOST, null) : null
  const host = inherited || { sources: shallowRef([]) }
  if (createHost && inComponent) provide(ERROR_HOST, host)
  const sources = errors.map(([id, error]) => ({ id, error }))
  host.sources.value = [...host.sources.value, ...sources]
  onScopeDispose(() => { host.sources.value = host.sources.value.filter(source => !sources.includes(source)) })
  const notices = computed(() => host.sources.value.filter(source => source.error.value).map(source => ({
    id: source.id, message: source.error.value, dismiss: () => { source.error.value = '' },
  })))
  return { notices, renderBanner: !inherited }
}
