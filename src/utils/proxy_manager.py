import aiohttp
import random
import logging

class ProxyManager:
    def __init__(self, proxy_sources):
        self.proxy_sources = proxy_sources
        self.proxies = []
        self.logger = logging.getLogger('proxy_manager')

    async def refresh_proxies(self):
        new_proxies = []
        for source in self.proxy_sources:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(source) as response:
                        if response.status == 200:
                            text = await response.text()
                            new_proxies.extend(text.strip().split('\n'))
            except Exception as e:
                self.logger.error(f"Ошибка при обновлении прокси из источника {source}: {str(e)}")
        
        self.proxies = new_proxies
        self.logger.info(f"Обновлено {len(self.proxies)} прокси")

    def get_proxy(self):
        if not self.proxies:
            return None
        return random.choice(self.proxies)

    async def remove_proxy(self, proxy):
        if proxy in self.proxies:
            self.proxies.remove(proxy)
            self.logger.info(f"Удален прокси {proxy}")
        if len(self.proxies) < 10:
            await self.refresh_proxies()