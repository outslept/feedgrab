import { writeFileSync, mkdirSync } from "fs";
import { stringify } from "csv-stringify/sync";
import axios from "axios";
import * as cheerio from "cheerio";
import PQueue from "p-queue";

interface Video {
  title: string;
  videoId: string;
  views: number;
  dailyViews: number;
  rank: number;
  url: string;
}

interface Category {
  name: string;
  url: string;
}

const CONFIG = {
  BASE_URL: "https://kworb.net/youtube",
  REQUEST_DELAY: 1000,
  OUTPUT_DIR: "./output/youtube",
  SELECTORS: {
    VIDEO_ROWS: "table.addpos tbody tr",
    VIDEO_LINK: "td:nth-child(1) a",
    VIEWS: "td:nth-child(2)",
    DAILY_VIEWS: "td:nth-child(3)",
    CATEGORY_LINKS: ".subcontainer a",
  },
  HEADERS: {
    "User-Agent":
      "KworbParser (GitHub: outslept; contact me if issues arise; sorry for any inconvenience)",
  },
};

const queue = new PQueue({
  concurrency: 3,
  interval: CONFIG.REQUEST_DELAY,
  carryoverConcurrencyCount: true,
});

async function fetchCategories(): Promise<Category[]> {
  try {
    const { data } = await axios.get(`${CONFIG.BASE_URL}/stats.html`, {
      headers: CONFIG.HEADERS,
    });

    const $ = cheerio.load(data);
    return $(CONFIG.SELECTORS.CATEGORY_LINKS)
      .map((_, el) => {
        const href = $(el).attr("href");
        const name = $(el).text().trim();
        return {
          name,
          url: href ? `${CONFIG.BASE_URL}/${href}` : "",
        };
      })
      .get()
      .filter(
        (category): category is Category =>
          Boolean(category.url) && !category.url.includes("#")
      );
  } catch (error) {
    console.error("Error fetching categories:", error);
    return [];
  }
}

async function parseVideoPage(url: string): Promise<Video[]> {
  try {
    const { data } = await axios.get(url, { headers: CONFIG.HEADERS });
    const $ = cheerio.load(data);

    return $(CONFIG.SELECTORS.VIDEO_ROWS)
      .map((index, element): Video => {
        const $row = $(element);
        const $link = $row.find(CONFIG.SELECTORS.VIDEO_LINK);
        const href = $link.attr("href") || "";
        const videoId = href.replace("video/", "").replace(".html", "");

        return {
          rank: index + 1,
          title: $link.text().trim(),
          videoId,
          views: parseInt(
            $row.find(CONFIG.SELECTORS.VIEWS).text().replace(/,/g, ""),
            10
          ),
          dailyViews: parseInt(
            $row.find(CONFIG.SELECTORS.DAILY_VIEWS).text().replace(/,/g, ""),
            10
          ),
          url: `https://youtube.com/watch?v=${videoId}`,
        };
      })
      .get();
  } catch (error) {
    console.error(`Error parsing video page ${url}:`, error);
    return [];
  }
}

function saveData(categoryName: string, videos: Video[]) {
  const safeName = categoryName.replace(/[^a-z0-9]/gi, "_").toLowerCase();
  mkdirSync(CONFIG.OUTPUT_DIR, { recursive: true });

  // Save as CSV
  const csvData = stringify(videos, {
    header: true,
    columns: ["rank", "title", "videoId", "views", "dailyViews", "url"],
  });
  writeFileSync(`${CONFIG.OUTPUT_DIR}/${safeName}.csv`, csvData);

  // Save as Markdown
  const markdown = generateMarkdown(categoryName, videos);
  writeFileSync(`${CONFIG.OUTPUT_DIR}/${safeName}.md`, markdown);
}

function generateMarkdown(categoryName: string, videos: Video[]): string {
  const header =
    `# ${categoryName}\n\n` +
    "| Rank | Title | Views | Daily Views | URL |\n" +
    "|------|--------|-------|-------------|-----|\n";

  const rows = videos
    .map(
      (video) =>
        `| ${video.rank} | ${
          video.title
        } | ${video.views.toLocaleString()} | ${video.dailyViews.toLocaleString()} | [Watch](${
          video.url
        }) |`
    )
    .join("\n");

  return header + rows;
}

async function processCategory(category: Category) {
  console.log(`Processing category: ${category.name}`);

  const videos = await queue.add(async () => parseVideoPage(category.url));

  if (Array.isArray(videos) && videos.length > 0) {
    saveData(category.name, videos);
    console.log(`✓ Saved ${videos.length} videos for ${category.name}`);
  } else {
    console.log(`No videos found for ${category.name}`);
  }
}

async function main() {
  try {
    console.time("Total execution");

    const categories = await fetchCategories();
    console.log(`Found ${categories.length} categories`);

    const categoryQueue = new PQueue({
      concurrency: 2,
      interval: 1000,
    });

    await categoryQueue.addAll(
      categories.map((category) => async () => {
        await processCategory(category);
      })
    );

    console.timeEnd("Total execution");
  } catch (error) {
    console.error("Critical error:", error);
    process.exit(1);
  }
}

main();
