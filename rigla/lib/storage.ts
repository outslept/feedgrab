import type { Product } from './scraper'
import { existsSync, mkdirSync, writeFileSync } from 'node:fs'
import path from 'node:path'
import { createObjectCsvWriter } from 'csv-writer'
import * as XLSX from 'xlsx'
import { logger } from './logger'

async function saveProducts(
  products: Product[],
  categoryName: string,
): Promise<void> {
  logger.info(
    `Saving ${products.length} products for category ${categoryName}`,
  )
  const categoryDir = path.join('./data', categoryName)
  if (!existsSync(categoryDir)) {
    mkdirSync(categoryDir, { recursive: true })
  }

  const txtContent = products
    .map(
      p =>
        `Name: ${p.name}\nPrice: ${p.price}\nBrand: ${p.brand}\nAvailability: ${p.availability}\nImage: ${p.imageUrl}\n\n`,
    )
    .join('')
  writeFileSync(path.join(categoryDir, `${categoryName}.txt`), txtContent)
  logger.info(`Saved TXT file for ${categoryName}`)

  const csvWriter = createObjectCsvWriter({
    path: path.join(categoryDir, `${categoryName}.csv`),
    header: [
      { id: 'name', title: 'Name' },
      { id: 'price', title: 'Price' },
      { id: 'brand', title: 'Brand' },
      { id: 'availability', title: 'Availability' },
      { id: 'imageUrl', title: 'Image URL' },
      { id: 'category', title: 'Category' },
    ],
  })
  await csvWriter.writeRecords(products)
  logger.info(`Saved CSV file for ${categoryName}`)

  const worksheet = XLSX.utils.json_to_sheet(products)
  const workbook = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(workbook, worksheet, 'Products')
  XLSX.writeFile(workbook, path.join(categoryDir, `${categoryName}.xlsx`))
  logger.info(`Saved XLSX file for ${categoryName}`)
}

export { saveProducts }
