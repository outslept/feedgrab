import fs from 'fs'
import path from 'path'
import logger from '../config/logger'
import { NewsItem } from '../interfaces/NewsItem'

export async function saveToJSON(
  data: NewsItem[],
  filename: string,
): Promise<void> {
  try {
    const dir = './output'
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true })
    }
    const filePath = path.join(dir, filename)
    fs.writeFileSync(filePath, JSON.stringify(data, null, 2))
    logger.info(`Data saved to ${filePath}`)
  } catch (error) {
    logger.error('Error saving data to JSON:', error)
    throw new Error('Failed to save data to JSON')
  }
}
