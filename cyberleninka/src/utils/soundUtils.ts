import player from 'play-sound'
import { CONFIG } from '../config/config'

export function playAlert(): Promise<void> {
  return new Promise((resolve, reject) => {
    player().play(CONFIG.SOUND_ALERT_FILE, (err) => {
      if (err) reject(err)
      else resolve()
    })
  })
}
