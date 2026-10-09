import type { Register } from 'claude-code'

// task-observer's deliverable flush fires on a handover, and a chat-only
// session with no todos never looks like one. This guard hangs the flush on
// an event the harness sees — the end of a turn — instead of a judgement.
//
// A "log write" is any main-loop tool call whose arguments touch the log the
// way a write does: the id helper, the per-skill lookup or session-start scan
// (both append to checkpoints.log), an append to checkpoints.log, or a
// Write/Edit whose path is in observation-log/. Reads that only grep the log
// do not count — a false "nothing logged" note costs one line, a false
// "logged" would silence the guard.
const WRITE_SIGNS = [
  /new-observation\.sh/,
  /skill-load\.sh/,
  /session-start-scan\.sh/,
  />>[^\n|;&]*checkpoints\.log/,
]
const LOG_PATH = /observation-log\/[^"'\s]*\.md|checkpoints\.log/

export function isLogWrite(tool: string, args: Record<string, unknown>): boolean {
  const path = typeof args.file_path === 'string' ? args.file_path : ''
  if ((tool === 'Write' || tool === 'Edit') && LOG_PATH.test(path)) return true
  const text = Object.values(args).filter(v => typeof v === 'string').join('\n')
  return WRITE_SIGNS.some(re => re.test(text))
}

const NOTE =
  'task-observer: this turn used tools and wrote nothing to the observation log or checkpoints.log.'
const REMINDER =
  'task-observer flush guard: the previous turn used tools and wrote nothing to ' +
  'skill-observations/observation-log/ or checkpoints.log. Before this turn ends, ' +
  'write any pending observation, or append a one-line `no observations` entry to ' +
  'skill-observations/checkpoints.log.'

export const register: Register = on => {
  let toolCalls = 0
  let logged = false
  let remind = false

  on('turn.start', ($, e, next) => {
    toolCalls = 0
    logged = false
    return next(e)
  })

  on('tool.call', async ($, e, next) => {
    const ran = await next(e)
    if (e.agentId === undefined && ran.deny === undefined) {
      toolCalls += 1
      const { tool, tool_use_id, agentId, requestMeta, ...args } = e as typeof e & {
        requestMeta?: unknown
      }
      if (isLogWrite(tool, args as Record<string, unknown>)) logged = true
    }
    return ran
  }).catch(($, e, next) => next.called ? next(e) : next(e))

  on('turn.complete', async ($, e, next) => {
    const done = await next(e)
    if (e.agentId !== undefined || e.reason !== 'answer') return done
    if (toolCalls > 0 && !logged) {
      remind = true
      return { ...done, text: `${done.text}\n\n_${NOTE}_` }
    }
    remind = false
    return done
  })

  on('prompt.compose', async ($, e, next) => {
    const composed = await next(e)
    if (!remind) return composed
    return {
      ...composed,
      sections: [
        ...composed.sections,
        { id: 'task-observer-flush:reminder', text: REMINDER, scope: 'session' as const },
      ],
    }
  })
}
