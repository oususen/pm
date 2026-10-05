// 実コンポーネントのsetupとテンプレートを評価。API・DB・実ブラウザには接続しない。
import assert from 'node:assert/strict'
import test from 'node:test'
import { readFileSync } from 'node:fs'
import * as Vue from 'vue'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'

const filename = new URL('../src/components/AIFloatingButton.vue', import.meta.url)
const { descriptor, errors } = parse(readFileSync(filename, 'utf8'), { filename: filename.pathname })
assert.deepEqual(errors, [])
const script = compileScript(descriptor, { id: 'qa-test' })
const template = compileTemplate({ source: descriptor.template.content, filename: filename.pathname,
  id: 'qa-test', compilerOptions: { bindingMetadata: script.bindings } })
assert.deepEqual(template.errors, [])
const render = new Function('Vue', template.code
  .replace(/import \{([^}]+)\} from "vue"/, (_, imports) => `const {${imports.replace(/ as /g, ':')}} = Vue`)
  .replace('export function render', 'function render') + '\nreturn render')(Vue)
const names = ['computed', 'nextTick', 'onBeforeUnmount', 'onMounted', 'ref', 'watch', 'useRoute', 'authState', 'hasPermission',
  'aiDrawerOpen', 'openAIDrawer', 'requestDialogOpen', 'openRequestDialog', 'requestHistoryOpen', 'openRequestHistory', 'window', 'document', 'localStorage', 'console']
const setup = new Function(...names, descriptor.scriptSetup.content.replace(/^import .*\r?\n/gm, '') +
  '\nreturn {root,menu,menuOpen,collapsed,position,viewport,menuStyle,visible,canUseAI,size,height,floatingStyle,startDrag,moveDrag,endDrag,toggleMenu,collapse,restore,resize,placeMenu,chooseAI,chooseRequest,chooseHistory}')
const key = 'pm.qa-floating.preferences.v1'
const surface = () => {
  const listeners = new Map()
  return { listeners, addEventListener: (name, fn) => listeners.set(name, fn), removeEventListener: (name, fn) => {
    if (listeners.get(name) === fn) listeners.delete(name)
  } }
}
function fixture({ width = 1024, height = 768, storage = new Map(), permission = true, denied = false } = {}) {
  const scope = Vue.effectScope(), window = { ...surface(), innerWidth: width, innerHeight: height }, document = surface()
  const dialogs = [Vue.ref(false), Vue.ref(false), Vue.ref(false)], calls = [], warnings = []
  let mounted, unmount
  const localStorage = {
    getItem: name => { if (denied) throw Error(); return storage.get(name) ?? null },
    setItem: (name, value) => { if (denied) throw Error(); storage.set(name, value) },
  }
  const state = scope.run(() => setup(Vue.computed, Vue.nextTick, fn => { unmount = fn }, fn => { mounted = fn }, Vue.ref, Vue.watch,
    () => ({ fullPath: '/quality/test?date=2026-10-05' }), { user: {} }, (_user, resource, action) => {
      assert.equal(resource, 'ai.chat'); assert.equal(action, 'view'); return permission
    }, dialogs[0], path => calls.push(['ai', path]), dialogs[1], () => calls.push(['request']), dialogs[2], () => calls.push(['history']),
    window, document, localStorage, { warn: message => warnings.push(message) }))
  mounted()
  state.root.value = { contains: target => target === 'inside', getBoundingClientRect: () => {
    const { x, y } = state.position.value, length = state.size.value
    return { left: x, top: y, right: x + length, bottom: y + state.height.value }
  } }
  state.menu.value = { offsetWidth: 184, offsetHeight: permission ? 108 : 72 }
  const captures = new Set()
  const target = { setPointerCapture: id => captures.add(id), hasPointerCapture: id => captures.has(id), releasePointerCapture: id => captures.delete(id) }
  const event = (type = 'pointerdown', overrides = {}) => ({ type, pointerId: 1, isPrimary: true, button: 0, clientX: 900, clientY: 650,
    currentTarget: target, preventDefault() {}, ...overrides })
  const buttons = () => {
    const found = []
    const visit = node => { if (!node || typeof node !== 'object') return; if (node.type === 'button') found.push(node); if (Array.isArray(node.children)) node.children.forEach(visit) }
    visit(render({}, [], {}, Vue.proxyRefs(state))); return found
  }
  return { state, window, document, storage, dialogs, calls, warnings, captures, event, buttons,
    flush: async () => { await Vue.nextTick(); await Vue.nextTick() },
    dispose: () => { unmount(); scope.stop() } }
}

test('マウス/タッチで移動し、ドラッグ後のclickはメニューを開かない。通常/キーボードclickは開く', () => {
  for (const pointerType of ['mouse', 'touch']) {
    const f = fixture()
    try {
      const origin = { ...f.state.position.value }
      f.state.startDrag(f.event('pointerdown', { pointerType }))
      f.state.moveDrag(f.event('pointermove', { pointerType, clientX: 800, clientY: 550 }))
      f.state.endDrag(f.event('pointerup', { pointerType }))
      assert.deepEqual(f.state.position.value, { x: origin.x - 100, y: origin.y - 100 })
      assert.equal(f.captures.size, 0); assert.equal(f.window.listeners.has('pointermove'), false)
      f.state.toggleMenu({ detail: 1 }); assert.equal(f.state.menuOpen.value, false)
      f.state.startDrag(f.event()); f.state.moveDrag(f.event('pointermove', { clientX: 901 })); f.state.endDrag(f.event('pointerup'))
      f.state.toggleMenu({ detail: 1 }); assert.equal(f.state.menuOpen.value, true)
      f.state.toggleMenu({ detail: 0 }); assert.equal(f.state.menuOpen.value, false)
    } finally { f.dispose() }
  }
})
test('別pointer/右クリックを無視し、cancel/unmountで捕捉と全listenerを解除', () => {
  const f = fixture()
  f.state.startDrag(f.event('pointerdown', { button: 2 })); assert.equal(f.captures.size, 0)
  f.state.startDrag(f.event()); f.state.endDrag(f.event('pointerup', { pointerId: 2 })); assert.equal(f.captures.size, 1)
  f.state.endDrag(f.event('pointercancel')); assert.equal(f.captures.size, 0)
  f.state.toggleMenu({ detail: 1 }); assert.equal(f.state.menuOpen.value, false)
  f.state.startDrag(f.event()); f.dispose()
  assert.equal(f.captures.size, 0); assert.equal(f.window.listeners.size, 0); assert.equal(f.document.listeners.size, 0)
})
test('×と復元の実テンプレートイベントで切替、専用キー保存、新setupで位置/折りたたみを復元', () => {
  const f = fixture(), storage = f.storage
  try {
    f.state.position.value = { x: 220, y: 330 }
    f.buttons().find(b => b.props.class === 'qa-collapse').props.onClick()
    assert.equal(f.state.collapsed.value, true); assert.equal(f.state.menuOpen.value, false)
    assert.equal(f.buttons().length, 1); assert.equal(f.state.floatingStyle.value.left, '976px')
    assert.deepEqual([...storage.keys()], [key])
    const restored = fixture({ storage })
    try {
      assert.deepEqual(restored.state.position.value, { x: 220, y: 330 }); assert.equal(restored.state.collapsed.value, true)
      restored.buttons()[0].props.onClick(); assert.equal(restored.state.collapsed.value, false)
      assert.equal(restored.state.floatingStyle.value.left, '220px')
      assert.equal(JSON.parse(storage.get(key)).collapsed, false)
    } finally { restored.dispose() }
  } finally { f.dispose() }
})
test('画面外drag・縮小/回転・保存値復元でボタン全体が画面内。折りたたみは右端', () => {
  const f = fixture()
  try {
    f.state.startDrag(f.event()); f.state.moveDrag(f.event('pointermove', { clientX: 9999, clientY: -9999 })); f.state.endDrag(f.event('pointerup'))
    assert.deepEqual(f.state.position.value, { x: 952, y: 0 })
    f.window.innerWidth = 360; f.window.innerHeight = 640; f.state.resize()
    assert.equal(f.state.position.value.x, 292); assert.equal(f.state.size.value, 68)
    f.state.collapse(); assert.equal(f.state.floatingStyle.value.left, '312px')
    f.window.innerWidth = 640; f.window.innerHeight = 360; f.state.position.value.y = 999; f.state.resize()
    assert.equal(f.state.position.value.y, 284); assert.equal(f.state.floatingStyle.value.left, '592px')
    f.state.restore(); assert.equal(f.state.floatingStyle.value.top, '284px')
    const next = fixture({ width: 320, height: 240, storage: f.storage })
    try { assert.deepEqual(next.state.position.value, { x: 252, y: 164 }) } finally { next.dispose() }
  } finally { f.dispose() }
})
test('四隅でメニュー全体を画面内に配置し、開閉で位置が変わらない', async () => {
  const f = fixture({ width: 360, height: 640 })
  try {
    for (const x of [0, 292]) for (const y of [0, 564]) {
      f.state.position.value = { x, y }; f.state.menuOpen.value = true
      await f.state.placeMenu()
      const mx = x + parseFloat(f.state.menuStyle.value.left), my = y + parseFloat(f.state.menuStyle.value.top)
      assert.ok(mx >= 0 && mx + 184 <= 360); assert.ok(my >= 0 && my + 108 <= 640)
      f.state.menuOpen.value = false; assert.deepEqual(f.state.position.value, { x, y })
    }
  } finally { f.dispose() }
})
test('AI権限と既存3入口を維持、各dialog表示中は通常/折りたたみ両方非表示', async () => {
  for (const permission of [true, false]) {
    const f = fixture({ permission })
    try {
      f.state.menuOpen.value = true
      const entries = f.buttons().filter(b => b.props.role === 'menuitem')
      assert.equal(entries.length, permission ? 3 : 2)
      entries.forEach(b => b.props.onClick())
      assert.deepEqual(f.calls, permission ? [['ai', '/quality/test?date=2026-10-05'], ['request'], ['history']] : [['request'], ['history']])
      for (const collapsed of [false, true]) for (const dialog of f.dialogs) {
        f.state.collapsed.value = collapsed; dialog.value = true; await f.flush()
        assert.equal(f.state.visible.value, false); assert.equal(f.buttons().length, 0)
        dialog.value = false; await f.flush(); assert.equal(f.state.visible.value, true)
      }
    } finally { f.dispose() }
  }
})
test('外側clickはメニューを閉じる。dialog表示中のdragも清掃', async () => {
  const f = fixture()
  try {
    f.state.menuOpen.value = true; f.document.listeners.get('click')({ target: 'inside' }); assert.equal(f.state.menuOpen.value, true)
    f.document.listeners.get('click')({ target: 'outside' }); assert.equal(f.state.menuOpen.value, false)
    f.state.startDrag(f.event()); f.dialogs[0].value = true; await f.flush()
    assert.equal(f.captures.size, 0); assert.equal(f.window.listeners.has('pointermove'), false)
  } finally { f.dispose() }
})
test('破損/無効な保存値を適用しない。保存拒否は例外伝播せず警告し、代替保存しない', () => {
  for (const saved of ['{', '{"position":{"x":"22","y":3},"collapsed":true}']) {
    const f = fixture({ storage: new Map([[key, saved]]) })
    try { assert.deepEqual(f.state.position.value, { x: 934, y: 670 }); assert.equal(f.state.collapsed.value, false) } finally { f.dispose() }
  }
  const f = fixture({ denied: true })
  try { f.state.collapse(); assert.equal(f.state.collapsed.value, true); assert.equal(f.storage.size, 0); assert.equal(f.warnings.length, 2) } finally { f.dispose() }
})
