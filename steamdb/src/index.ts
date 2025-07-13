import { chromium, type Browser, type Page, type BrowserContext } from 'playwright';
import process from 'node:process';

interface SteamProfile {
  display_name: string | null;
  avatar: string | null;
  steam_id: string;
  vanity_url: string | null;
  level: string | null;
  games: string | null;
  games_played: string | null;
  price: string | null;
  price_lowest: string | null;
  price_average: string | null;
  price_hour: string | null;
  hours: string | null;
  hours_average: string | null;
  account_age: string | null;
  url_steam: string;
  url_steamdb: string;
}

interface DebugConfig {
  enabled: boolean;
  verbose: boolean;
  timing: boolean;
  headless: boolean;
}

interface BrowserManager {
  initialize(): Promise<void>;
  close(): Promise<void>;
  getPage(): Page;
  canConnect(url: string): Promise<boolean>;
}

class PlaywrightBrowserManager implements BrowserManager {
  private readonly debug: DebugConfig;
  private browser: Browser | null = null;
  private context: BrowserContext | null = null;
  private page: Page | null = null;

  constructor(debug: DebugConfig) {
    this.debug = debug;
  }

  async canConnect(url: string): Promise<boolean> {
    if (this.page == null) {
      await this.initialize();
    }

    const startTime = Date.now();
    this.log('Testing connection', 'debug');

    try {
      this.log(`Navigating to ${url}`, 'debug');

      const response = await this.page!.goto(url, {
        waitUntil: 'domcontentloaded',
        timeout: 30000
      });

      if (response == null) {
        this.log('No response received', 'error');
        return false;
      }

      const status = response.status();
      this.log(`Response status: ${status}`, 'debug');

      if (status == 200) {
        this.log('Waiting for body selector', 'debug');
        await this.page!.waitForSelector('body', { timeout: 10000 });

        const title = await this.page!.title();
        this.log(`Page title: ${title}`, 'debug');

        const connected = title.includes('SteamDB') || title.includes('Calculator');
        this.log(`Connection test completed in ${Date.now() - startTime}ms: ${connected}`, 'debug');
        return connected;
      }

      return false;
    } catch (error) {
      this.log(`Connection failed: ${error}`, 'error');
      return false;
    }
  }

  async close(): Promise<void> {
    const startTime = Date.now();
    this.log('Closing browser', 'debug');

    try {
      if (this.page) {
        await this.page.close();
        this.log('Page closed', 'debug');
      }
      if (this.context) {
        await this.context.close();
        this.log('Context closed', 'debug');
      }
      if (this.browser) {
        await this.browser.close();
        this.log('Browser closed', 'debug');
      }

      this.log(`Browser cleanup completed in ${Date.now() - startTime}ms`, 'debug');
    } catch (error) {
      this.log(`Error during cleanup: ${error}`, 'error');
    }
  }

  getPage(): Page {
    if (this.page == null) {
      throw new Error('Browser not initialized. Call initialize() first.');
    }
    return this.page;
  }

  async initialize(): Promise<void> {
    const startTime = Date.now();
    this.log('Launching browser', 'debug');

    try {
      this.browser = await chromium.launch({
        headless: this.debug.headless,
        timeout: 60000,
        args: [
          '--no-sandbox',
          '--disable-setuid-sandbox',
          '--disable-dev-shm-usage',
          '--disable-accelerated-2d-canvas',
          '--no-first-run',
          '--no-zygote',
          '--disable-gpu',
          '--disable-web-security',
          '--disable-features=VizDisplayCompositor'
        ]
      });

      this.log('Browser launched, creating context', 'debug');

      this.context = await this.browser.newContext({
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
        viewport: { width: 1920, height: 1080 },
        locale: 'en-US',
        timezoneId: 'America/New_York',
        extraHTTPHeaders: {
          'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
          'Accept-Language': 'en-US,en;q=0.5',
          'Accept-Encoding': 'gzip, deflate, br',
          'DNT': '1',
          'Connection': 'keep-alive',
          'Upgrade-Insecure-Requests': '1',
        }
      });

      this.log('Context created, creating page', 'debug');

      this.page = await this.context.newPage();

      this.log('Setting up resource blocking', 'debug');

      await this.page.route('**/*', (route) => {
        const resourceType = route.request().resourceType();
        if (['image', 'stylesheet', 'font', 'media'].includes(resourceType)) {
          route.abort();
        } else {
          route.continue();
        }
      });

      this.log(`Browser initialized in ${Date.now() - startTime}ms`, 'debug');
    } catch (error) {
      this.log(`Browser initialization failed: ${error}`, 'error');
      throw error;
    }
  }

  private log(message: string, level: 'info' | 'error' | 'debug' = 'info'): void {
    if (!this.debug.enabled && level == 'debug') return;
    if (!this.debug.verbose && level == 'debug') return;

    const timestamp = this.debug.timing ? `[${Date.now()}] ` : '';
    const prefix = level == 'error' ? 'ERROR: ' : level == 'debug' ? 'DEBUG: ' : '';
    console.log(`${timestamp}${prefix}${message}`);
  }
}

class SteamDBParser {
  private readonly baseUrl = 'https://steamdb.info/calculator/';
  private readonly browserManager: BrowserManager;
  private readonly currency: string;
  private readonly debug: DebugConfig;

  private constructor(currency: string, browserManager: BrowserManager, debug: DebugConfig) {
    this.currency = currency;
    this.browserManager = browserManager;
    this.debug = debug;
    this.log('Parser initialized');
  }

  static async create(currency: string = 'us'): Promise<SteamDBParser> {
    const debug: DebugConfig = {
      enabled: process.env.DEBUG == '1' || process.env.DEBUG == 'true',
      verbose: process.env.VERBOSE == '1' || process.env.VERBOSE == 'true',
      timing: process.env.TIMING == '1' || process.env.TIMING == 'true',
      headless: process.env.HEADLESS != '0' && process.env.HEADLESS != 'false'
    };

    const browserManager = new PlaywrightBrowserManager(debug);
    await browserManager.initialize();

    return new SteamDBParser(currency, browserManager, debug);
  }

  async canConnect(): Promise<boolean> {
    return this.browserManager.canConnect(this.baseUrl);
  }

  async close(): Promise<void> {
    await this.browserManager.close();
  }

  async getSteamDBProfile(steamId: string | number): Promise<SteamProfile> {
    const steamIdStr = String(steamId);

    if (!this.isSteamId(steamIdStr)) {
      throw new Error(`Invalid Steam ID: ${steamIdStr}`);
    }

    const steamDBUrl = `${this.baseUrl}${steamIdStr}/?cc=${this.currency}`;
    const startTime = Date.now();

    const profile: SteamProfile = {
      display_name: null,
      avatar: null,
      steam_id: steamIdStr,
      vanity_url: null,
      level: null,
      games: null,
      games_played: null,
      price: null,
      price_lowest: null,
      price_average: null,
      price_hour: null,
      hours: null,
      hours_average: null,
      account_age: null,
      url_steam: `http://steamcommunity.com/profiles/${steamIdStr}`,
      url_steamdb: steamDBUrl
    };

    this.log(`Navigating to: ${steamDBUrl}`, 'debug');

    const page = this.browserManager.getPage();
    const response = await page.goto(steamDBUrl, {
      waitUntil: 'domcontentloaded',
      timeout: 30000
    });

    if (response == null || response.status() != 200) {
      throw new Error(`Page load failed: ${response?.status()}`);
    }

    this.log('Waiting for calculator wrapper', 'debug');
    await page.waitForSelector('div.calculator-wrapper', { timeout: 15000 });
    await page.waitForTimeout(3000);

    this.log('Page loaded, parsing content', 'debug');

    await this.parseAdditional(page, profile);
    await this.parseHeader(page, profile);
    await this.parseStats(page, profile);

    this.log(`Profile parsing completed in ${Date.now() - startTime}ms`, 'debug');

    return profile;
  }

  isSteamId(steamId: string | number): boolean {
    const steamIdStr = String(steamId);
    const isValid = steamIdStr.length == 17 && /^\d+$/.test(steamIdStr);
    this.log(`Steam ID validation: ${steamIdStr} -> ${isValid}`, 'debug');
    return isValid;
  }

  private async extractText(page: Page, selector: string, attribute?: string): Promise<string | null> {
    try {
      const element = await page.$(selector);
      if (element == null) {
        this.log(`Selector not found: ${selector}`, 'debug');
        return null;
      }

      const result = attribute
        ? await element.getAttribute(attribute)
        : (await element.textContent())?.trim() || null;

      this.log(`Extracted from ${selector}: ${result}`, 'debug');
      return result;
    } catch (error) {
      this.log(`Extract error for ${selector}: ${error}`, 'error');
      return null;
    }
  }

  private log(message: string, level: 'info' | 'error' | 'debug' = 'info'): void {
    if (!this.debug.enabled && level == 'debug') return;
    if (!this.debug.verbose && level == 'debug') return;

    const timestamp = this.debug.timing ? `[${Date.now()}] ` : '';
    const prefix = level == 'error' ? 'ERROR: ' : level == 'debug' ? 'DEBUG: ' : '';
    console.log(`${timestamp}${prefix}${message}`);
  }

  private async parseAdditional(page: Page, profile: SteamProfile): Promise<void> {
    this.log('Parsing additional info', 'debug');

    try {
      const vanityRow = await page.$('table.table-steamids tr:has(td:text("Vanity URL"))');
      if (vanityRow) {
        const vanityLink = await vanityRow.$('td:nth-child(2) a');
        if (vanityLink) {
          const href = await vanityLink.getAttribute('href');
          if (href) {
            const vanityMatch = href.match(/\/id\/([^\/]+)/);
            profile.vanity_url = vanityMatch ? vanityMatch[1] : href;
            this.log(`Vanity URL: ${profile.vanity_url}`, 'debug');
          }
        }
      }
    } catch (error) {
      this.log(`Additional info parse error: ${error}`, 'error');
    }
  }

  private async parseHeader(page: Page, profile: SteamProfile): Promise<void> {
    this.log('Parsing header info', 'debug');

    profile.avatar = await this.extractText(page, 'img.avatar', 'src');
    profile.display_name = await this.extractText(page, 'h1.header-title a.player-name');
    profile.level = await this.extractText(page, 'ul.player-info li span.friendPlayerLevel');

    const accountAgeElement = await page.$('ul.player-info li:has(img[src*="steamyears"]) span span.number');
    if (accountAgeElement) {
      profile.account_age = await accountAgeElement.textContent();
      this.log(`Account age extracted: ${profile.account_age}`, 'debug');
    }

    const priceElement = await page.$('div.prices span.number-price');
    if (priceElement) {
      const spans = await priceElement.$$('span');
      if (spans.length >= 2) {
        profile.price = await spans[0].textContent();
        profile.price_lowest = await spans[1].textContent();
        this.log(`Prices extracted - total: ${profile.price}, lowest: ${profile.price_lowest}`, 'debug');
      }
    }
  }

  private async parseStats(page: Page, profile: SteamProfile): Promise<void> {
    this.log('Parsing game stats', 'debug');

    const gamesPlayedElement = await page.$('div.row-stats div.span6 div.progress-desc span.number');
    if (gamesPlayedElement) {
      profile.games_played = await gamesPlayedElement.textContent();
      this.log(`Games played: ${profile.games_played}`, 'debug');
    }

    const totalGamesElement = await page.$('div.row-stats div.span6 div.progress-desc strong.number');
    if (totalGamesElement) {
      profile.games = await totalGamesElement.textContent();
      this.log(`Total games: ${profile.games}`, 'debug');
    }

    const avgPriceElement = await page.$('div.row-stats div.span3:nth-child(1) b');
    if (avgPriceElement) {
      profile.price_average = await avgPriceElement.textContent();
      this.log(`Average price: ${profile.price_average}`, 'debug');
    }

    const pricePerHourElement = await page.$('div.row-stats div.span3:nth-child(2) b');
    if (pricePerHourElement) {
      profile.price_hour = await pricePerHourElement.textContent();
      this.log(`Price per hour: ${profile.price_hour}`, 'debug');
    }

    const hoursElement = await page.$('div.row-stats div.span3:nth-child(3) b');
    if (hoursElement) {
      profile.hours = await hoursElement.textContent();
      this.log(`Total hours: ${profile.hours}`, 'debug');
    }

        const avgHoursElement = await page.$('div.row-stats div.span3:nth-child(4) b');
    if (avgHoursElement) {
      profile.hours_average = await avgHoursElement.textContent();
      this.log(`Average hours: ${profile.hours_average}`, 'debug');
    }
  }
}

export { SteamDBParser, type SteamProfile, type BrowserManager, type DebugConfig };
