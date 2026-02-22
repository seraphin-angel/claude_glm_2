import { Client } from 'pg'

const TEST_DB_URL = process.env.TEST_DATABASE_URL
  ?? 'postgresql://todouser:todopass@host.docker.internal:5433/todos_test?schema=public'

async function globalSetup() {
  const client = new Client({ connectionString: TEST_DB_URL })
  try {
    await client.connect()
    await client.query('DELETE FROM todos')
  } finally {
    await client.end()
  }
}

export default globalSetup
