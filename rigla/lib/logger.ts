import fs from 'node:fs'
import path from 'node:path'
import process from 'node:process'
import pino from 'pino'

const logsDir = path.join(process.cwd(), 'logs')
if (!fs.existsSync(logsDir)) {
  fs.mkdirSync(logsDir, { recursive: true })
}

const fileFormat = {
  target: 'pino-pretty',
  options: {
    colorize: false,
    ignore: 'pid,hostname',
    translateTime: 'yyyy-mm-dd HH:MM:ss',
    messageFormat: '[{level}] {msg}',
  },
}

const streams = [
  {
    stream: pino.transport({
      target: 'pino-pretty',
      options: {
        colorize: true,
        ignore: 'pid,hostname',
        translateTime: 'yyyy-mm-dd HH:MM:ss',
      },
    }),
    level: 'info',
  },
  {
    stream: pino.transport({
      ...fileFormat,
      options: {
        ...fileFormat.options,
        destination: path.join(logsDir, 'error.log'),
      },
    }),
    level: 'error',
  },
  {
    stream: pino.transport({
      ...fileFormat,
      options: {
        ...fileFormat.options,
        destination: path.join(logsDir, 'warning.log'),
      },
    }),
    level: 'warn',
  },
]

export const logger = pino(
  {
    level: 'info',
    timestamp: pino.stdTimeFunctions.isoTime,
  },
  pino.multistream(streams),
)

process.on('uncaughtException', (error) => {
  logger.fatal(error, 'Uncaught Exception')
  process.exit(1)
})

process.on('unhandledRejection', (reason, promise) => {
  logger.fatal(
    {
      reason,
      promise,
    },
    'Unhandled Rejection',
  )
  process.exit(1)
})
