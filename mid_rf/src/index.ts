import { NewsFeedFetcher } from './services/NewsFeedFetcher'
import { saveToJSON } from './utils/fileUtils'
import logger from './config/logger'

async function main() {
  const fetcher = new NewsFeedFetcher()
  try {
    await fetcher.initialize()

    const newsItems = await fetcher.getContent(1)

    await saveToJSON(newsItems, 'news_feed.json')

    logger.info(`Total news items fetched: ${newsItems.length}`)
  } catch (error) {
    logger.error('An error occurred:', error)
  } finally {
    await fetcher.close()
  }
}

main().catch((error) => {
  logger.error('Unhandled error in main function:', error)
  process.exit(1)
})
