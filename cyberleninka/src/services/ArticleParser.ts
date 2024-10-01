import { Page } from 'puppeteer'
import { Article } from '../interfaces/Article'
import { CONFIG } from '../config/config'
import { downloadFile } from '../utils/fileUtils'
import { playAlert } from '../utils/soundUtils'

export class ArticleParser {
  constructor(private page: Page) {}

  async parseArticle(article: Article): Promise<void> {
    await this.page.goto(article.url)

    const viewerButton = await this.page.$('#btn-viewer')
    if (viewerButton) {
      await viewerButton.click()
      await this.page.waitForNavigation()

      const pageCount = await this.getPageCount()
      if (pageCount > CONFIG.MAX_PAGES_ALERT) {
        await playAlert()
      }

      const downloadUrl = await this.getDownloadUrl()
      if (downloadUrl) {
        await downloadFile(
          downloadUrl,
          `${CONFIG.DOWNLOAD_FOLDER}/${article.title}.pdf`,
        )
      }
    }
  }

  private async getPageCount(): Promise<number> {
    const pageCountElement = await this.page.$('.pages span')
    if (pageCountElement) {
      const pageText = await pageCountElement.evaluate((el) => el.textContent)
      const match = pageText?.match(/\d+\s*\/\s*(\d+)/)
      if (match) {
        return parseInt(match[1], 10)
      }
    }
    return 0
  }

  private async getDownloadUrl(): Promise<string | null> {
    const downloadButton = await this.page.$('.controls .btn[title="Скачать"]')
    if (downloadButton) {
      return await this.page.evaluate((button) => {
        const clickEvent = new MouseEvent('click', {
          bubbles: true,
          cancelable: true,
          view: window,
        })
        button.dispatchEvent(clickEvent)
        return (window as any).downloadUrl
      }, downloadButton)
    }
    return null
  }
}
