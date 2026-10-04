// 表示・スクロールのみを検証。AI・API・DBには接続しない。
import assert from 'node:assert/strict'
import test from 'node:test'
import * as Vue from 'vue'
import { renderToString } from '@vue/server-renderer'
import { useAnalysisErrorNotices } from '../src/composables/analysisErrorNotices.js'
import { AnalysisErrorBanner, bannerSource, createBanner } from './analysis-error-banner-test-helper.mjs'

test('共通帯は空なら非表示、エラーの見出し・alert・閉じるボタン・エスケープをSSRで確認', async () => {
  const html = notices => renderToString(Vue.createSSRApp(AnalysisErrorBanner, { notices }))
  assert.equal((await html([])).includes('analysis-error-banner'), false)
  const text = await html([{ id: 'analysis', message: '<script>秘密</script>', dismiss: () => {} }])
  assert.ok(text.includes('analysis-error-banner')); assert.ok(text.includes('エラー</strong>'))
  assert.ok(text.includes('role="alert"')); assert.ok(text.includes('aria-label="エラーを閉じる"'))
  assert.ok(text.includes('&lt;script&gt;')); assert.equal(text.includes('<script>'), false)
})

test('実際にコンパイルした閉じるボタンのイベントが、該当するエラーだけを消す', () => {
  const scope = Vue.effectScope(), first = Vue.ref('分析エラー'), second = Vue.ref('履歴エラー')
  try {
    const host = scope.run(() => useAnalysisErrorNotices([['analysis', first], ['history', second]]))
    const vnode = AnalysisErrorBanner.render({}, [], { notices: host.notices.value }, { banner: null })
    const buttons = []
    const visit = node => {
      if (!node || typeof node !== 'object') return
      if (node.type === 'button') buttons.push(node)
      if (Array.isArray(node.children)) node.children.forEach(visit)
    }
    visit(vnode)
    assert.equal(buttons.length, 2)
    buttons[1].props.onClick({ type: 'click' })
    assert.equal(first.value, '分析エラー'); assert.equal(second.value, '')
    buttons[0].props.onClick({ type: 'click' }); assert.equal(host.notices.value.length, 0)
  } finally { scope.stop() }
})

function scrolling(reduced = false, deferTick = false) {
  const scope = Vue.effectScope(), props = Vue.reactive({ notices: [] }), calls = []
  let rect = { top: 40, bottom: 100, left: 0, right: 400 }, shown = true, unmount
  const pendingTicks = []
  const element = { getClientRects: () => shown ? [rect] : [], getBoundingClientRect: () => rect,
    scrollIntoView: options => calls.push(options), focus: () => assert.fail('フォーカスを移してはいけない') }
  const state = scope.run(() => createBanner(Vue.ref, Vue.watch, deferTick ? () => new Promise(resolve => pendingTicks.push(resolve)) : Vue.nextTick, callback => { unmount = callback }, () => props,
    { innerHeight: 800, innerWidth: 1000, matchMedia: query => { assert.equal(query, '(prefers-reduced-motion: reduce)'); return { matches: reduced } } }))
  state.banner.value = element
  const flush = async () => { await Vue.nextTick(); await Vue.nextTick() }
  return { props, calls, state, flush, unmount, releaseTicks: () => pendingTicks.splice(0).forEach(resolve => resolve()), rect: value => { rect = value }, hide: () => { shown = false }, stop: () => scope.stop() }
}

test('新しいエラーが視界外のときだけスクロール。視界内・閉じる・同じ内容では動かさない', async () => {
  const f = scrolling()
  try {
    f.props.notices = [{ id: 'a', message: '画面内', dismiss: () => {} }]; await f.flush()
    assert.equal(f.calls.length, 0)
    f.rect({ top: 1000, bottom: 1060, left: 0, right: 400 })
    f.props.notices = [{ id: 'a', message: '新しいエラー', dismiss: () => {} }]; await f.flush()
    assert.deepEqual(f.calls, [{ block: 'start', behavior: 'smooth' }])
    f.props.notices = [{ id: 'a', message: '新しいエラー', dismiss: () => {} }]; await f.flush()
    f.props.notices = []; await f.flush(); assert.equal(f.calls.length, 1)
  } finally { f.stop() }
})

test('reduced-motionではauto。非表示タブ・画面破棄後・古い待機処理はスクロールしない', async () => {
  for (const mode of ['reduced', 'hidden', 'disposed', 'stale']) {
    const f = scrolling(true, mode === 'stale')
    try {
      f.rect({ top: -100, bottom: -40, left: 0, right: 400 })
      if (mode === 'hidden') f.hide()
      f.props.notices = [{ id: 'a', message: 'エラー', dismiss: () => {} }]
      if (mode === 'disposed') f.unmount()
      if (mode === 'stale') { await Vue.nextTick(); f.props.notices = []; await Vue.nextTick(); f.releaseTicks() }
      await f.flush()
      assert.deepEqual(f.calls, mode === 'reduced' ? [{ block: 'start', behavior: 'auto' }] : [], mode)
    } finally { f.stop() }
  }
})

test('共有ホストは子の実行・履歴も集め、閉じる対象だけを消す。独立画面は自前の帯', async () => {
  const analysis = Vue.ref('分析'), execution = Vue.ref('実行'), history = Vue.ref('履歴')
  let host, child
  const Child = { setup() { child = useAnalysisErrorNotices([['execution', execution], ['history', history]]); return () => Vue.h('span') } }
  const Root = { setup() { host = useAnalysisErrorNotices([['analysis', analysis]], true); return () => Vue.h(Child) } }
  await renderToString(Vue.createSSRApp(Root))
  assert.equal(host.renderBanner, true); assert.equal(child.renderBanner, false)
  assert.deepEqual(host.notices.value.map(notice => notice.message), ['分析', '実行', '履歴'])
  host.notices.value.find(notice => notice.id === 'history').dismiss()
  assert.equal(history.value, ''); assert.equal(execution.value, '実行'); assert.equal(analysis.value, '分析')
  const scope = Vue.effectScope()
  const local = scope.run(() => useAnalysisErrorNotices([['execution', execution]]))
  assert.equal(local.renderBanner, true)
  scope.stop(); assert.equal(local.notices.value.length, 0)
})

test('赤と背景のコントラストは4.5以上。sticky前面表示で点滅やフォーカス移動なし', () => {
  const luminance = hex => {
    const rgb = hex.replace('#', '').match(/../g).map(value => parseInt(value, 16) / 255)
      .map(value => value <= .04045 ? value / 12.92 : ((value + .055) / 1.055) ** 2.4)
    return rgb[0] * .2126 + rgb[1] * .7152 + rgb[2] * .0722
  }
  const contrast = (luminance('#fff0ee') + .05) / (luminance('#aa2222') + .05)
  assert.ok(contrast >= 4.5, `contrast=${contrast}`)
  assert.ok(bannerSource.includes('position: sticky')); assert.ok(bannerSource.includes('z-index: 10000'))
  assert.ok(bannerSource.includes('color: #a22')); assert.equal(/animation:|\.focus\(/.test(bannerSource), false)
})
