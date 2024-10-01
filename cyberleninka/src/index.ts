import { Browser } from './services/Browser'
import { SearchParser } from './services/SearchParser'
import { ArticleParser } from './services/ArticleParser'

async function main() {
  const browser = new Browser()
  await browser.initialize()

  const page = await browser.getPage()
  const searchParser = new SearchParser(page)
  const articleParser = new ArticleParser(page)

  try {
    const searchQuery = ''
    const articles = await searchParser.search(searchQuery)

    console.log(`Found ${articles.length} articles.`)

    for (const article of articles) {
      console.log(`Processing article: ${article.title}`)
      await articleParser.parseArticle(article)
    }

    console.log('All articles processed successfully.')
  } catch (error) {
    console.error('An error occurred:', error)
  } finally {
    await browser.close()
  }
}

main().catch(console.error)
