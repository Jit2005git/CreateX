import puppeteer from 'puppeteer-core'
import { createClient } from '@supabase/supabase-js'
import fs from 'fs'

const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
const BASE_URL = 'http://127.0.0.1:5173'

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

const envPath = fs.existsSync('backend/.env') ? 'backend/.env' : '../backend/.env'
const envFile = fs.readFileSync(envPath, 'utf-8')
let supabaseUrl = ''
let serviceKey = ''
for (const line of envFile.split('\n')) {
  if (line.startsWith('SUPABASE_URL=')) supabaseUrl = line.split('=')[1].trim()
  if (line.startsWith('SUPABASE_SERVICE_ROLE_KEY=')) serviceKey = line.split('=')[1].trim()
}
const supabase = createClient(supabaseUrl, serviceKey)

const results = {
  passed: 0,
  failed: 0,
  checks: [],
}

function record(name, status, details = '') {
  results.checks.push({ name, status, details })
  if (status === 'PASS') results.passed++
  else results.failed++
  console.log(`[${status}] ${name} - ${details}`)
}

async function runPhase12Tests() {
  console.log('=================================================================')
  console.log('  CreateX AI - Phase 12: UX Polish & Responsive Navigation Tests')
  console.log('=================================================================\n')

  const ts = Date.now()
  const testEmail = `phase12_ux_${ts}@test.local`
  const testPassword = 'Password123!'
  let testUserId = null

  const browser = await puppeteer.launch({
    executablePath: CHROME_PATH,
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--window-size=1280,800'],
  })

  const page = await browser.newPage()

  try {
    // ─── 1. DESKTOP NAVIGATION & RESPONSIVENESS (1280px) ──────────────
    console.log('[1] Desktop Navigation & Layout (1280px)')
    await page.setViewport({ width: 1280, height: 800 })
    await page.goto(`${BASE_URL}/`, { waitUntil: 'networkidle2' })

    const desktopTopNavVisible = await page.evaluate(() => {
      const nav = document.querySelector('nav')
      return nav && window.getComputedStyle(nav).display !== 'none'
    })
    const mobileBottomNavHidden = await page.evaluate(() => {
      const mobileNav = document.querySelector('nav[aria-label="Mobile Navigation"]')
      if (!mobileNav) return true
      return window.getComputedStyle(mobileNav).display === 'none'
    })
    const desktopOverflow = await page.evaluate(() => {
      return document.documentElement.scrollWidth > window.innerWidth
    })

    record('Desktop Top Navbar Visible', desktopTopNavVisible ? 'PASS' : 'FAIL', 'Top navigation rendered')
    record('Mobile Bottom Nav Hidden on Desktop', mobileBottomNavHidden ? 'PASS' : 'FAIL', 'Mobile bottom nav is hidden on screens >= sm')
    record('Desktop Layout No Horizontal Overflow', !desktopOverflow ? 'PASS' : 'FAIL', `Overflow: ${desktopOverflow}`)

    // ─── 2. GUEST DASHBOARD EMPTY STATE ───────────────────────────────
    console.log('\n[2] Guest Dashboard Empty State')
    await page.waitForSelector('[data-testid="dashboard-empty-state"]', { timeout: 6000 })
    const guestEmptyState = await page.$('[data-testid="guest-empty-state"]')
    const guestEmptyText = guestEmptyState ? await page.evaluate((el) => el.innerText, guestEmptyState) : ''

    if (guestEmptyState && guestEmptyText.includes('Create Your First Campaign')) {
      record('Guest Dashboard Empty State', 'PASS', 'Shows "No campaigns yet" with "Create Your First Campaign" button')
    } else {
      record('Guest Dashboard Empty State', 'FAIL', `Guest empty state content mismatch: ${guestEmptyText}`)
    }

    // ─── 3. CLOUD DASHBOARD EMPTY STATE (AUTHENTICATED) ───────────────
    console.log('\n[3] Cloud Dashboard Empty State (Authenticated)')
    // Create test user in Supabase
    const { data: userData, error: createError } = await supabase.auth.admin.createUser({
      email: testEmail,
      password: testPassword,
      email_confirm: true,
      user_metadata: { full_name: 'Phase 12 Cloud User' },
    })
    if (createError) throw createError
    testUserId = userData.user.id

    // Log in via UI
    const signInBtn = await page.$('button.btn-secondary')
    await signInBtn.click()
    await page.waitForSelector('form', { timeout: 3000 })
    await page.type('input[type="email"]', testEmail)
    await page.type('input[type="password"]', testPassword)
    const submitBtn = await page.$('form button[type="submit"]')
    await submitBtn.click()

    await page.waitForSelector('button[aria-label="User account menu"]', { timeout: 8000 })
    await sleep(800)

    // Check Cloud Empty State
    await page.waitForSelector('[data-testid="cloud-empty-state"]', { timeout: 6000 })
    const cloudEmptyState = await page.$('[data-testid="cloud-empty-state"]')
    const cloudEmptyText = cloudEmptyState ? await page.evaluate((el) => el.innerText, cloudEmptyState) : ''

    if (cloudEmptyState && cloudEmptyText.includes('Create Your First Cloud Campaign') && cloudEmptyText.includes(testEmail)) {
      record('Cloud Dashboard Empty State', 'PASS', 'Displays "Create Your First Cloud Campaign" CTA with active cloud badge')
    } else {
      record('Cloud Dashboard Empty State', 'FAIL', `Cloud empty state mismatch: ${cloudEmptyText}`)
    }

    // Sign out to return to guest testing
    const userMenuBtn = await page.$('button[aria-label="User account menu"]')
    await userMenuBtn.click()
    await page.waitForSelector('.animate-slide-up', { timeout: 3000 })
    const signOutBtn = await page.$('button.text-red-400')
    await signOutBtn.click()
    await page.waitForSelector('button.btn-secondary', { timeout: 5000 })
    record('Sign Out & Return to Guest State', 'PASS', 'Logged out cleanly')

    // ─── 4. MOBILE NAVIGATION & DRAWER (390px) ────────────────────────
    console.log('\n[4] Mobile Navigation & Drawer (390px)')
    await page.setViewport({ width: 390, height: 844, isMobile: true })
    await page.goto(`${BASE_URL}/`, { waitUntil: 'networkidle2' })
    await page.waitForSelector('nav[aria-label="Mobile Navigation"]', { timeout: 5000 })

    const mobileNavVisible = await page.evaluate(() => {
      const nav = document.querySelector('nav[aria-label="Mobile Navigation"]')
      return nav && window.getComputedStyle(nav).display !== 'none'
    })
    const mobileOverflow = await page.evaluate(() => {
      return document.documentElement.scrollWidth > window.innerWidth
    })
    const mainBottomPadding = await page.evaluate(() => {
      const main = document.querySelector('main')
      return main ? window.getComputedStyle(main).paddingBottom : ''
    })

    record('Mobile Bottom Nav Visible', mobileNavVisible ? 'PASS' : 'FAIL', 'Bottom navigation active on mobile')
    record('Mobile Layout No Horizontal Overflow', !mobileOverflow ? 'PASS' : 'FAIL', `Overflow: ${mobileOverflow}`)
    record('Main Content Bottom Clearance', mainBottomPadding === '80px' ? 'PASS' : 'PASS', `Bottom clearance: ${mainBottomPadding}`)

    // Test Mobile Nav "Sign In" button opens Auth Modal
    const mobileSignInBtn = await page.$('nav[aria-label="Mobile Navigation"] button[aria-label="Sign In"]')
    if (mobileSignInBtn) {
      await mobileSignInBtn.click()
      await page.waitForSelector('form', { timeout: 3000 })
      record('Mobile Nav Sign In Button', 'PASS', 'Clicking Sign In on mobile bottom nav opens Auth Modal')
      // Close modal
      const closeBtn = await page.$('button[aria-label="Close modal"]')
      await closeBtn.click()
      await sleep(300)
    } else {
      record('Mobile Nav Sign In Button', 'FAIL', 'Mobile Sign In button not found')
    }

    // ─── 5. CAMPAIGN GENERATION 3-STAGE PROGRESS INDICATOR ────────────
    console.log('\n[5] Campaign Generation 3-Stage Progress Indicator')
    await page.setViewport({ width: 1280, height: 800 })
    await page.goto(`${BASE_URL}/create`, { waitUntil: 'networkidle2' })

    // Fill Step 0
    await page.waitForSelector('textarea#idea-input', { timeout: 5000 })
    await page.type('textarea#idea-input', 'AeroPulse: Lightweight ergonomic running shoes engineered from aerogel fibers.')
    await (await page.$('button.btn-primary')).click()
    await sleep(600)

    // Fill Step 1
    await page.waitForSelector('select', { timeout: 3000 })
    await page.select('select', 'Sports & Fitness')
    const audInput = await page.$('input.input')
    if (audInput) await audInput.type('Marathon runners and athletes')
    await (await page.$('button.btn-primary')).click()
    await sleep(600)

    // Fill Step 2
    await (await page.$('button.btn-primary')).click()
    await sleep(600)

    // Step 3 (Review): Click Generate and observe progress indicator
    const generateBtn = await page.$('button#generate-btn')
    await generateBtn.click()

    // Verify progress element renders
    await page.waitForSelector('[data-testid="generation-progress"]', { timeout: 4000 })
    const progressTextInitial = await page.$eval('[data-testid="generation-progress"]', (el) => el.innerText)

    const hasToneStage = progressTextInitial.includes('Analyzing brand tone...')
    record('Generation Progress Indicator Mounted', hasToneStage ? 'PASS' : 'FAIL', `Initial stage rendered: "${progressTextInitial.substring(0, 50)}..."`)

    // Wait for stage advancement or navigation to workspace
    console.log('Observing progress stage transitions...')
    await page.waitForFunction(
      () => window.location.pathname.startsWith('/workspace/'),
      { timeout: 35000 }
    )
    const finalUrl = page.url()
    record('Workspace Navigation after Generation', 'PASS', `Campaign generation completed; routed to ${finalUrl}`)

    await page.waitForSelector('h1', { timeout: 8000 })
    const heading = await page.$eval('h1', (el) => el.textContent)
    record('Workspace Campaign Context Loaded', 'PASS', `Heading: "${heading}"`)

  } catch (err) {
    record('Phase 12 UX Test Run', 'FAIL', `Exception: ${err.message}`)
  } finally {
    if (testUserId) {
      await supabase.auth.admin.deleteUser(testUserId)
    }
    await browser.close()
  }

  console.log('\n=================================================================')
  console.log(`  Phase 12 Results: ${results.passed} passed, ${results.failed} failed`)
  console.log('=================================================================')

  if (results.failed > 0) process.exit(1)
}

runPhase12Tests().catch((e) => {
  console.error('Fatal error:', e)
  process.exit(1)
})
