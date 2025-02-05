import type { Browser, Page } from 'puppeteer'
import puppeteer from 'puppeteer-extra'
import StealthPlugin from 'puppeteer-extra-plugin-stealth'
import { logger } from './logger'

export interface BrowserContext {
  browser: Browser
  page: Page
}

export async function initializeBrowser(): Promise<BrowserContext> {
  logger.info('Initializing browser...')
  puppeteer.use(StealthPlugin())

  const browser = await puppeteer.launch({
    headless: true,
    args: [
      '--disable-dev-shm-usage',
      '--disable-accelerated-2d-canvas',
      '--disable-gpu',
      '--disable-background-timer-throttling',
      '--disable-backgrounding-occluded-windows',
      '--disable-renderer-backgrounding',
      '--disable-features=IsolateOrigins,site-per-process',
      '--metrics-recording-only',
      '--no-first-run',
    ],
  })

  const page = await browser.newPage()
  await page.setUserAgent(
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
  )
  await page.setViewport({
    width: 1366,
    height: 768,
  })

  logger.info('Browser initialized successfully')
  return { browser, page }
}
