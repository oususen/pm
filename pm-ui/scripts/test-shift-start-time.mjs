import { readFileSync } from 'node:fs'
import assert from 'node:assert/strict'
import test from 'node:test'

const source = readFileSync(new URL('../src/views/shifts/ShiftManagement.vue', import.meta.url), 'utf8')

// 実画面の関数を抽出し、保存APIと画面更新のみ差し替える。
function extract(name) {
  const match = source.match(new RegExp(`(?:async )?function ${name}\\([^]*?\\n\\}`))
  assert.ok(match, `${name}が見つかること`)
  return match[0]
}

function setup(raw, editing = false) {
  const calls = []
  const alerts = []
  const state = {
    entryWorkerId: { value: 1 }, entryLineProcessId: { value: 2 }, entryWorkHours: { value: 2 },
    entryStart: { value: raw }, entryUnits: { value: 3 }, entryComment: { value: ' コメント ' },
    editingId: { value: editing ? 42 : null }, lineProcessMap: { value: { 2: { process: 7 } } },
    currentLineId: { value: 9 }, selectedDate: { value: '2026-10-12' },
    api: { shifts: {
      createAssignment: async payload => calls.push({ method: 'create', payload }),
      updateAssignment: async (id, payload) => calls.push({ method: 'update', id, payload }),
    } },
    alert: message => alerts.push(message), cancelEdit: () => {},
    loadAssignments: async () => {}, syncStartFromChart: () => {},
  }
  const run = new Function(...Object.keys(state), `${extract('parseTimeInput')}\n${extract('submitAssignment')}\nreturn submitAssignment`)
  return { save: run(...Object.values(state)), calls, alerts }
}

const validCases = [
  ['24:20', '00:20'], ['26:00', '02:00'], ['26:20', '02:20'],
  ['08:00', '08:00'], ['23:59', '23:59'], ['8', '08:00'], ['800', '08:00'],
  ['26', '02:00'], ['2620', '02:20'], ['08:00:30', '08:00:30'],
  ['24:20:30', '00:20:30'], ['48:00', '00:00'],
]

for (const editing of [false, true]) {
  for (const [raw, expected] of validCases) {
    test(`${editing ? '更新' : '新規'}: ${raw}を${expected}で保存しシフト日付を維持する`, async () => {
      const context = setup(raw, editing)
      await context.save()
      assert.deepEqual(context.alerts, [])
      assert.deepEqual(context.calls, [{
        method: editing ? 'update' : 'create', ...(editing ? { id: 42 } : {}),
        payload: {
          shift_line: 9, date: '2026-10-12', worker: 1, process: 7, line_process: 2,
          start_time: expected, work_hours: 2, units: 3, comment: 'コメント',
        },
      }])
    })
  }
  for (const raw of ['', '24:60', '26:99', '08:00:60', '-8', '8abc', '26:20x', '8:0', '100:00', '8.5', '2460', '08:00:', '99999999999999999999']) {
    test(`${editing ? '更新' : '新規'}: 不正入力${JSON.stringify(raw)}はAPIへ送信しない`, async () => {
      const context = setup(raw, editing)
      await context.save()
      assert.equal(context.calls.length, 0)
      assert.equal(context.alerts.length, 1)
      assert.match(context.alerts[0], /開始時刻/)
    })
  }
}

test('8時開始チャートでは翌日開始時刻の変換前後で位置が一致する', () => {
  const absMinute = new Function(`${extract('tm')}\n${extract('absMinute')}\nreturn absMinute`)()
  for (const [raw, saved] of [['24:20', '00:20'], ['26:00', '02:00'], ['26:20', '02:20']]) {
    assert.equal(absMinute(raw, 480), absMinute(saved, 480))
  }
})
