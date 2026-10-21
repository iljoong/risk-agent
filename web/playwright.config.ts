import { defineConfig } from '@playwright/test'
import path from 'node:path'

const root = path.resolve(import.meta.dirname, '..')
export default defineConfig({
  testDir: './e2e', workers: 1, retries: 0, timeout: 45000,
  use: { baseURL: 'http://127.0.0.1:18962', headless: true, screenshot: 'only-on-failure' },
  webServer: [
    { command: '.\\.venv\\Scripts\\python.exe .\\backend\\tests\\e2e_server.py api', cwd: root, url: 'http://127.0.0.1:18961/health/live', reuseExistingServer: false, timeout: 45000 },
    { command: '.\\.venv\\Scripts\\python.exe .\\backend\\tests\\e2e_server.py worker', cwd: root, url: 'http://127.0.0.1:18961/health/ready', reuseExistingServer: false, timeout: 45000 },
    { command: 'npm run dev -- --host 127.0.0.1 --port 18962', cwd: path.join(root, 'web'), url: 'http://127.0.0.1:18962', reuseExistingServer: false, env: { VITE_API_BASE_URL: 'http://127.0.0.1:18961' } },
  ],
})
