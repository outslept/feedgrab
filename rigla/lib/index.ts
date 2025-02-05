import process from 'node:process'
import PQueue from 'p-queue'
import { initializeBrowser } from './browser'
import { logger } from './logger'
import { getCategories, getProducts } from './scraper'
import { saveProducts } from './storage'

async function main(): Promise<void> {
  logger.info('Starting parser...')
  const { browser, page } = await initializeBrowser()

  try {
    const categories = await getCategories(page)
    const queue = new PQueue({
      concurrency: 1,
      interval: 1000,
      intervalCap: 1,
    })

    for (const category of categories) {
      await queue.add(async () => {
        const products = await getProducts(page, category)
        await saveProducts(products, category.name)
        await new Promise(resolve => setTimeout(resolve, 3000))
      })
    }

    await queue.onIdle()
    logger.info('Scraping completed successfully')
  }
  catch (error) {
    logger.error(
      error instanceof Error ? error.message : 'Unknown error occurred',
    )
  }
  finally {
    await browser.close()
    logger.info('Browser closed')
  }
}

main().catch((error) => {
  logger.error('Fatal error:', error)
  process.exit(1)
})
