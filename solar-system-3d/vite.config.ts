import { defineConfig } from 'vitest/config'

export default defineConfig({
  server: {
    port: 3000,
    host: true // Dev Containerで外部アクセスを許可
  },
  test: {
    environment: 'jsdom'
  }
})
