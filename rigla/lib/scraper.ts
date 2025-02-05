import type { Page } from 'puppeteer'
import PQueue from 'p-queue'
import { logger } from './logger'

export interface Product {
  name: string
  price: string
  brand: string
  availability: string
  imageUrl: string
  category: string
}

export interface Category {
  name: string
  url: string
}

export async function getCategories(page: Page): Promise<Category[]> {
  logger.info('Fetching categories...')
  await page.goto('https://www.rigla.ru', { waitUntil: 'networkidle2' })

  const categories = await page.evaluate((baseUrl) => {
    const categories: Category[] = []
    document.querySelectorAll('.navigation-item').forEach((item) => {
      const link = item.querySelector('a')
      if (
        link instanceof HTMLAnchorElement
        && !link.href.includes('sales')
        && !link.href.includes('discounts')
      ) {
        categories.push({
          name: link.textContent?.trim() ?? '',
          url: new URL(link.href, baseUrl).href,
        })
      }
    })
    return categories.filter(c => Boolean(c.name))
  }, 'https://www.rigla.ru')

  logger.info(`Found ${categories.length} categories`)
  return categories
}

async function getProducts(page: Page, category: Category): Promise<Product[]> {
  logger.info(`Processing category: ${category.name}`)
  await page.goto(category.url, { waitUntil: 'networkidle2' })

  const lastPage = await page.evaluate(() => {
    const lastPageElement = document.querySelector('.pagination__item._last')
    return lastPageElement
      ? Number.parseInt(lastPageElement.textContent?.trim() ?? '1')
      : 1
  })

  logger.info(`Category ${category.name} has ${lastPage} pages`)

  const products: Product[] = []
  const queue = new PQueue({ concurrency: 1, interval: 1000, intervalCap: 1 })

  for (let currentPage = 1; currentPage <= lastPage; currentPage++) {
    await queue.add(async () => {
      logger.info(
        `Processing ${category.name} - page ${currentPage}/${lastPage}`,
      )
      await page.goto(`${category.url}?page=${currentPage}`, {
        waitUntil: 'networkidle2',
      })

      const pageProducts = await page.evaluate((categoryName) => {
        return Array.from(document.querySelectorAll('.product')).map(
          productElement => ({
            name:
              productElement
                .querySelector('.product__title')
                ?.textContent
                ?.trim() ?? '',
            price:
              productElement
                .querySelector('.product__active-price-number')
                ?.textContent
                ?.trim() ?? '',
            brand:
              productElement
                .querySelector('.product-brand__link')
                ?.textContent
                ?.trim() ?? '',
            availability:
              productElement
                .querySelector('.stock-type')
                ?.textContent
                ?.trim() ?? '',
            imageUrl:
              (
                productElement.querySelector(
                  '.product__img',
                ) as HTMLImageElement
              )?.src ?? '',
            category: categoryName,
          }),
        )
      }, category.name)

      products.push(...pageProducts)
      logger.info(
        `Found ${pageProducts.length} products on page ${currentPage}`,
      )
      await new Promise(resolve => setTimeout(resolve, 2000))
    })
  }

  await queue.onIdle()
  logger.info(
    `Finished processing category ${category.name}, found ${products.length} products total`,
  )
  return products
}

export { getProducts }
