import puppeteer, { Browser as PuppeteerBrowser, Page } from 'puppeteer'

export class Browser {
  private browser: PuppeteerBrowser | null = null
  private page: Page | null = null

  async initialize(): Promise<void> {
    this.browser = await puppeteer.launch({ headless: true })
    this.page = await this.browser.newPage()
  }

  async getPage(): Promise<Page> {
    if (!this.page) {
      throw new Error('Browser not initialized')
    }
    return this.page
  }

  async close(): Promise<void> {
    if (this.browser) {
      await this.browser.close()
    }
  }
}
