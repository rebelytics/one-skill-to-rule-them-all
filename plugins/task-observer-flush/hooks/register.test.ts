import { test, expect } from 'claude-code/testing'
import { isLogWrite } from './register'

const ROOT = '/home/user/work space/skill-observations'

test('log writes are recognised from the real command shapes', () => {
  expect(isLogWrite('mcp__remote-devices__device_bash', {
    command: `bash "$HOME/tmp/to/new-observation.sh" some-slug "${ROOT}/.."`,
  })).toBe(true)
  expect(isLogWrite('mcp__remote-devices__device_bash', {
    command: `echo "2026-01-01 09:00 no observations" >> "${ROOT}/checkpoints.log"`,
  })).toBe(true)
  expect(isLogWrite('Write', { file_path: `${ROOT}/observation-log/1900-x.md`, content: 'x' })).toBe(true)
})

test('reads of the log do not count as writes', () => {
  expect(isLogWrite('mcp__remote-devices__device_bash', {
    command: `grep -l status "${ROOT}/observation-log/"*.md; tail -3 "${ROOT}/checkpoints.log"`,
  })).toBe(false)
  expect(isLogWrite('Bash', { command: 'ls -la' })).toBe(false)
})

test('a turn with tool calls and no log write gets the note; the next prompt carries the reminder', async ($, on) => {
  on('turn.start', ($, e) => ({ turnId: e.turnId }))
  on('tool.call', () => ({ result: { stdout: 'ok', stderr: '', interrupted: false } }) as never)
  on('turn.complete', ($, e) => ({ text: e.answer }))
  on('prompt.compose', () => ({ sections: [] }))
  await $.turn.start({ text: 'do it', turnId: 't1' })
  await $.tool.call({ tool: 'Bash', command: 'ls' } as never)
  const done = await $.turn.complete({ answer: 'Done.', durationMs: 1, isAborted: false, reason: 'answer', turnId: 't1' } as never)
  expect(done.text).toContain('wrote nothing to the observation log')
  const composed = await $.prompt.compose({ model: 'claude-fable-5-1', promptModel: 'claude-fable-5-1', surfaces: [], tools: [], outputStyle: null, traits: [] } as never)
  expect(composed.sections.some(s => s.id === 'task-observer-flush:reminder')).toBe(true)
})

test('a turn that logged gets no note and clears the reminder', async ($, on) => {
  on('turn.start', ($, e) => ({ turnId: e.turnId }))
  on('tool.call', () => ({ result: { stdout: 'ok', stderr: '', interrupted: false } }) as never)
  on('turn.complete', ($, e) => ({ text: e.answer }))
  on('prompt.compose', () => ({ sections: [] }))
  await $.turn.start({ text: 'do it', turnId: 't2' })
  await $.tool.call({ tool: 'Bash', command: `echo x >> "${ROOT}/checkpoints.log"` } as never)
  const done = await $.turn.complete({ answer: 'Done.', durationMs: 1, isAborted: false, reason: 'answer', turnId: 't2' } as never)
  expect(done.text).toBe('Done.')
  const composed = await $.prompt.compose({ model: 'claude-fable-5-1', promptModel: 'claude-fable-5-1', surfaces: [], tools: [], outputStyle: null, traits: [] } as never)
  expect(composed.sections.length).toBe(0)
})

test('a turn with no tool calls gets no note', async ($, on) => {
  on('turn.start', ($, e) => ({ turnId: e.turnId }))
  on('turn.complete', ($, e) => ({ text: e.answer }))
  await $.turn.start({ text: 'hi', turnId: 't3' })
  const done = await $.turn.complete({ answer: 'Hello.', durationMs: 1, isAborted: false, reason: 'answer', turnId: 't3' } as never)
  expect(done.text).toBe('Hello.')
})
