import { expect, test } from '@playwright/test'
import type { Chat } from '../src/api/types'

for (const reducedMotion of ['no-preference', 'reduce'] as const) {
  test(`long task indicator rotates without blinking with ${reducedMotion} motion`, async ({ page }) => {
    await page.emulateMedia({ reducedMotion })
    const chat: Chat = {
      id: 'animation-chat', title: 'Long-running research', model_id: 'openai',
      attachments: [], artifacts: [],
      turns: [{
        id: 'animation-turn', state: 'running', mode: 'background', answer: '', error: null,
        request: {
          client_request_id: 'animation-request', message: 'Research this customer',
          model_id: 'openai', skill_id: null, attachment_ids: [], artifact_version_id: null,
        },
      }],
      tasks: [{
        id: 'animation-task', turn_id: 'animation-turn', state: 'running',
        stage: 'Researching customer', error: null,
      }],
    }
    await page.route(/\/api\/chats(?:\/|$)/, async route => {
      const pathname = new URL(route.request().url()).pathname
      if (pathname.endsWith('/events')) {
        await route.fulfill({ contentType: 'text/event-stream', body: '' })
      } else {
        await route.fulfill({ json: pathname === '/api/chats' ? [chat] : chat })
      }
    })
    await page.goto('/')
    await page.getByRole('button', { name: chat.title, exact: true }).click()
    const spinner = page.locator('.task-card .spin')
    await expect(spinner).toBeVisible()
    await expect.poll(() => spinner.evaluate(async element => {
      const before = getComputedStyle(element)
      const initialTransform = before.transform
      const initialOpacity = before.opacity
      await new Promise<void>(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve())))
      const after = getComputedStyle(element)
      return {
        rotating: initialTransform !== after.transform,
        pulsing: initialOpacity !== after.opacity,
      }
    })).toEqual({ rotating: true, pulsing: false })

    chat.turns[0].state = 'succeeded'
    chat.tasks[0].state = 'succeeded'
    await expect(spinner).toHaveCount(0)
  })
}
