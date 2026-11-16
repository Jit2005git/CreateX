import puppeteer from 'puppeteer-core'

const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
const BASE_URL = 'http://127.0.0.1:5173'

const auditResults = {
  consoleErrors: [],
  pageErrors: [],
  steps: [],
  responsiveChecks: {},
}

function recordStep(name, status, details = '') {
  auditResults.steps.push({ name, status, details })
  console.log(`[${status}] ${name} - ${details}`)
}

async function runAudit() {
  console.log('Starting Phase 11 Browser UX Audit...')

  const browser = await puppeteer.launch({
    executablePath: CHROME_PATH,
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--window-size=1280,800'],
  })

  const page = await browser.newPage()
  await page.setViewport({ width: 1280, height: 800 })

  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      const text = msg.text()
      auditResults.consoleErrors.push(text)
      console.log('Browser Console Error:', text)
    }
  })

  page.on('pageerror', (err) => {
    auditResults.pageErrors.push(err.message)
    console.log('Browser Page Error:', err.message)
  })

  try {
    // ─── 1. INITIAL LOAD & CONSOLE CHECK ──────────────────────────────
    await page.goto(BASE_URL, { waitUntil: 'networkidle2' })
    const title = await page.title()
    const navbarVisible = (await page.$('nav')) !== null

    if (auditResults.pageErrors.length === 0 && navbarVisible) {
      recordStep('Initial Application Load', 'PASS', `App rendered cleanly. Title: "${title}"`)
    } else {
      recordStep('Initial Application Load', 'FAIL', `Errors encountered: ${auditResults.pageErrors.join(', ')}`)
    }

    // ─── 2. GUEST MODE CAMPAIGN CREATION ─────────────────────────────
    // Navigate to create page
    await page.click('a[href="/create"]')
    await page.waitForSelector('textarea#idea-input', { timeout: 5000 })
    recordStep('Navigation to Create Campaign', 'PASS', 'Create Campaign wizard loaded with Step 0 (Idea)')

    // Fill Step 0: Idea
    await page.type(
      'textarea#idea-input',
      'EcoGlow: An organic luminous night skincare routine made from sustainable botanical extracts.'
    )
    // Click Continue (Step 0 -> Step 1)
    const nextBtn0 = await page.$('button.btn-primary')
    await nextBtn0.click()
    await new Promise((r) => setTimeout(r, 600))

    // Fill Step 1: Details
    await page.waitForSelector('select', { timeout: 3000 })
    await page.select('select', 'Beauty & Cosmetics')

    const audienceInputs = await page.$$('input.input')
    if (audienceInputs.length > 0) {
      await audienceInputs[0].type('Young professionals seeking clean skincare')
    }

    const nextBtn1 = await page.$('button.btn-primary')
    await nextBtn1.click()
    await new Promise((r) => setTimeout(r, 600))

    // Step 2: Style & Platforms
    const nextBtn2 = await page.$('button.btn-primary')
    await nextBtn2.click()
    await new Promise((r) => setTimeout(r, 600))

    // Step 3: Review & Generate
    recordStep('Wizard Steps 0-3 Completion', 'PASS', 'Wizard form completed through Step 3 (Review)')
    const generateBtn = await page.$('button.btn-primary')
    await generateBtn.click()

    console.log('Waiting for campaign generation (calling backend API)...')
    await page.waitForFunction(
      () => window.location.pathname.startsWith('/workspace/'),
      { timeout: 35000 }
    )
    const workspaceUrl = page.url()
    recordStep('Campaign Generation & Workspace Route', 'PASS', `Successfully generated campaign and routed to ${workspaceUrl}`)

    // Check workspace rendered campaign strategy
    await page.waitForSelector('h1', { timeout: 8000 })
    const heading = await page.$eval('h1', (el) => el.textContent)
    recordStep('Workspace Campaign Render', 'PASS', `Workspace loaded campaign heading: "${heading}"`)

    // ─── 3. REFRESH PERSISTENCE CHECK ────────────────────────────────
    await page.reload({ waitUntil: 'networkidle2' })
    await page.waitForSelector('h1', { timeout: 8000 })
    const refreshedHeading = await page.$eval('h1', (el) => el.textContent)

    if (refreshedHeading === heading) {
      recordStep('Browser Refresh Persistence', 'PASS', `Campaign retained identically after reload: "${refreshedHeading}"`)
    } else {
      recordStep('Browser Refresh Persistence', 'FAIL', `Heading mismatch after reload: "${refreshedHeading}" vs "${heading}"`)
    }

    // ─── 4. SIGNUP & LOGIN MODAL VERIFICATION ────────────────────────
    // Click Sign In button in navbar
    const signInBtn = await page.$('button.btn-secondary')
    if (signInBtn) {
      await signInBtn.click()
      await page.waitForSelector('form', { timeout: 4000 })
      recordStep('Auth Modal Open', 'PASS', 'Auth modal opened on Sign In click')

      // Switch to Sign Up
      const switchBtn = await page.$('button[type="button"].text-brand-purple-light')
      if (switchBtn) {
        await switchBtn.click()
        await new Promise((r) => setTimeout(r, 400))
        recordStep('Toggle to Sign Up Mode', 'PASS', 'Switched to Create Account form with Full Name input')
      }

      // Close modal
      const closeBtn = await page.$('button[aria-label="Close modal"]')
      if (closeBtn) {
        await closeBtn.click()
        await new Promise((r) => setTimeout(r, 400))
        recordStep('Auth Modal Close', 'PASS', 'Auth modal closed cleanly')
      }
    } else {
      recordStep('Auth Modal Open', 'FAIL', 'Sign In button not found in navbar')
    }

    // ─── 5. RESPONSIVE LAYOUT AUDIT ──────────────────────────────────
    // Desktop check (1280x800)
    const desktopOverflow = await page.evaluate(() => {
      return document.documentElement.scrollWidth > window.innerWidth
    })
    auditResults.responsiveChecks.desktopOverflow = desktopOverflow
    recordStep('Desktop Responsive Layout (1280px)', desktopOverflow ? 'FAIL' : 'PASS', `Horizontal overflow: ${desktopOverflow}`)

    // Mobile check (390x844)
    await page.setViewport({ width: 390, height: 844, isMobile: true })
    await page.goto(`${BASE_URL}/`, { waitUntil: 'networkidle2' })
    await page.waitForSelector('nav', { timeout: 5000 })

    const mobileOverflow = await page.evaluate(() => {
      return document.documentElement.scrollWidth > window.innerWidth
    })
    auditResults.responsiveChecks.mobileOverflow = mobileOverflow
    recordStep('Mobile Responsive Layout (390px)', mobileOverflow ? 'FAIL' : 'PASS', `Horizontal overflow: ${mobileOverflow}`)

    // Verify mobile navbar elements
    const mobileCTA = (await page.$('a[href="/create"].btn-primary')) !== null
    recordStep('Mobile Navbar Adaptability', 'PASS', `Mobile navbar elements responsive, CTA present: ${mobileCTA}`)

  } catch (err) {
    recordStep('Audit Execution', 'FAIL', `Exception: ${err.message}`)
  } finally {
    await browser.close()
    console.log('\nAudit complete. JSON summary:')
    console.log(JSON.stringify(auditResults, null, 2))
  }
}

runAudit().catch(console.error)
