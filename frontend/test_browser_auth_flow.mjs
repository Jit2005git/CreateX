import puppeteer from 'puppeteer-core'
import { createClient } from '@supabase/supabase-js'
import fs from 'fs'

const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
const BASE_URL = 'http://127.0.0.1:5173'

// Read backend/.env to get Supabase admin credentials for test user setup and cleanup
const envPath = fs.existsSync('backend/.env') ? 'backend/.env' : '../backend/.env'
const envFile = fs.readFileSync(envPath, 'utf-8')
let supabaseUrl = ''
let serviceKey = ''
for (const line of envFile.split('\n')) {
  if (line.startsWith('SUPABASE_URL=')) supabaseUrl = line.split('=')[1].trim()
  if (line.startsWith('SUPABASE_SERVICE_ROLE_KEY=')) serviceKey = line.split('=')[1].trim()
}

const supabase = createClient(supabaseUrl, serviceKey)

async function runAuthFlow() {
  console.log('Starting Browser Auth Flow & User Experience Audit...')
  const ts = Date.now()
  const testEmail = `browser_auth_${ts}@test.local`
  const testPassword = 'Password123!'
  const testName = 'Browser Test User'

  let testUserId = null
  const authResults = { steps: [] }

  function record(name, status, details = '') {
    authResults.steps.push({ name, status, details })
    console.log(`[${status}] ${name} - ${details}`)
  }

  try {
    // 1. Pre-provision test user with confirmed email
    const { data: userData, error: createError } = await supabase.auth.admin.createUser({
      email: testEmail,
      password: testPassword,
      email_confirm: true,
      user_metadata: { full_name: testName }
    })
    if (createError) throw createError
    testUserId = userData.user.id
    record('Pre-provision Test Account', 'PASS', `User ID: ${testUserId.substring(0, 8)}...`)

    // 2. Launch browser
    const browser = await puppeteer.launch({
      executablePath: CHROME_PATH,
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox', '--window-size=1280,800'],
    })

    const page = await browser.newPage()
    await page.setViewport({ width: 1280, height: 800 })

    await page.goto(BASE_URL, { waitUntil: 'networkidle2' })

    // 3. Open Login modal
    const signInBtn = await page.$('button.btn-secondary')
    await signInBtn.click()
    await page.waitForSelector('form', { timeout: 3000 })
    record('Open Login Modal', 'PASS', 'Sign In modal displayed')

    // 4. Fill credentials & submit
    await page.type('input[type="email"]', testEmail)
    await page.type('input[type="password"]', testPassword)
    const submitBtn = await page.$('form button[type="submit"]')
    await submitBtn.click()

    // 5. Verify user menu appears in Navbar
    await page.waitForSelector('button[aria-label="User account menu"]', { timeout: 8000 })
    record('Authentication Success', 'PASS', 'User authenticated; account button appeared in Navbar')

    // 6. Open user account dropdown
    const userMenuBtn = await page.$('button[aria-label="User account menu"]')
    await userMenuBtn.click()
    await page.waitForSelector('.animate-slide-up', { timeout: 3000 })

    const dropdownText = await page.$eval('.animate-slide-up', (el) => el.innerText)
    const showsEmail = dropdownText.includes(testEmail)
    const showsBadge = dropdownText.includes('Cloud Account')

    if (showsEmail && showsBadge) {
      record('Account Menu Details', 'PASS', `Dropdown displays user email and "Cloud Account" badge`)
    } else {
      record('Account Menu Details', 'FAIL', `Dropdown text missing expected details: ${dropdownText}`)
    }

    // 7. Test Sign Out
    const signOutBtn = await page.$('button.text-red-400')
    await signOutBtn.click()
    await page.waitForSelector('button.btn-secondary', { timeout: 5000 })
    record('Sign Out Action', 'PASS', 'Sign out successful; Navbar restored "Sign In" button')

    // 8. Verify guest dashboard state
    await page.goto(`${BASE_URL}/`, { waitUntil: 'networkidle2' })
    const isGuest = (await page.$('button.btn-secondary')) !== null
    record('Guest Session Restoration', isGuest ? 'PASS' : 'FAIL', 'Guest mode active after sign out')

    await browser.close()
  } catch (err) {
    record('Browser Auth Flow Execution', 'FAIL', err.message)
  } finally {
    if (testUserId) {
      await supabase.auth.admin.deleteUser(testUserId)
      record('Test Account Teardown', 'PASS', `Deleted test user ${testUserId.substring(0, 8)}...`)
    }
  }

  console.log('\nAuth Flow Complete. Summary:')
  console.log(JSON.stringify(authResults, null, 2))
}

runAuthFlow().catch(console.error)
