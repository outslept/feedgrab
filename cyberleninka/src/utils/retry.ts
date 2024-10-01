import { CONFIG } from '../config/config'

export async function retry<T>(
    fn: () => Promise<T>,
    maxRetries: number = CONFIG.MAX_RETRIES
): Promise<T> {
    let lastError: Error | null = null;

    for (let i = 0; i < maxRetries; i++) {
        try {
            return await fn()
        } catch (error) {
            console.warn(`Attemp ${i + 1} failed. Retrying...`)
            lastError = error as Error;
            await new Promise(resolve => setTimeout(resolve, CONFIG.RETRY_DELAY))
        }
    }

    throw lastError || new Error('Max retries reached')
}
