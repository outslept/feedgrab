import { Page } from 'puppeteer'
import { Article } from '../interfaces/Article'
import { CONFIG } from '../config/config'

export class SearchParser {
  constructor(private page: Page) {}

  async search(query: string): Promise<Article[]> {
    await this.page.goto(`${CONFIG.SEARCH_URL}?q=${encodeURIComponent(query)}`)

    return this.page.evaluate(() => {
      const articles: Article[] = []
      const articleElements = document.querySelectorAll('.search-results li')

      articleElements.forEach((element) => {
        const titleElement = element.querySelector('h2.title a')
        const authorElement = element.querySelector('span')
        const abstractElement = element.querySelector('div p')
        const journalElement = element.querySelector('.span-block a')

        if (
          titleElement &&
          authorElement &&
          abstractElement &&
          journalElement
        ) {
          articles.push({
            title: titleElement.textContent || '',
            author: authorElement.textContent || '',
            url: (titleElement as HTMLAnchorElement).href,
            abstract: abstractElement.textContent || '',
            year:
              element
                .querySelector('.span-block')
                ?.textContent?.split('/')[0]
                .trim() || '',
            journal: journalElement.textContent || '',
          })
        }
      })

      return articles
    })
  }
}
