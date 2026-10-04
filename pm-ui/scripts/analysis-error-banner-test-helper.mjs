import { readFileSync } from 'node:fs'
import * as Vue from 'vue'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'

const filename = new URL('../src/components/AnalysisErrorBanner.vue', import.meta.url)
export const bannerSource = readFileSync(filename, 'utf8')
const { descriptor, errors } = parse(bannerSource, { filename: filename.pathname })
if (errors.length) throw errors[0]
const script = compileScript(descriptor, { id: 'error-banner-test' })
const template = compileTemplate({ source: descriptor.template.content, filename: filename.pathname,
  id: 'error-banner-test', compilerOptions: { bindingMetadata: script.bindings } })
if (template.errors.length) throw template.errors[0]
export const createBanner = new Function('ref', 'watch', 'nextTick', 'onBeforeUnmount', 'defineProps', 'window',
  descriptor.scriptSetup.content.replace(/^import .*\r?\n/gm, '') + '\nreturn {banner}')
const render = new Function('Vue', template.code
  .replace(/import \{([^}]+)\} from "vue"/, (_, imports) => `const {${imports.replace(/ as /g, ':')}} = Vue`)
  .replace('export function render', 'function render') + '\nreturn render')(Vue)
export const AnalysisErrorBanner = {
  props: ['notices'],
  setup: props => createBanner(Vue.ref, Vue.watch, Vue.nextTick, Vue.onBeforeUnmount, () => props, {}),
  render,
}
