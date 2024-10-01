import fs from 'fs'
import path from 'path'
import axios from 'axios'

export async function downloadFile(
  url: string,
  outputPath: string,
): Promise<void> {
  const dir = path.dirname(outputPath)
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true })
  }

  const response = await axios({
    method: 'GET',
    url: url,
    responseType: 'stream',
  })

  const writer = fs.createWriteStream(outputPath)
  response.data.pipe(writer)

  return new Promise((resolve, reject) => {
    writer.on('finish', resolve)
    writer.on('error', reject)
  })
}
