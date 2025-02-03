import { writeFileSync, mkdirSync } from "fs";
import { stringify } from "csv-stringify/sync";
import axios from "axios";
import * as cheerio from "cheerio";
import PQueue from "p-queue";

type EntityType = "artist" | "release" | "release-group" | "recording";
type Entity = {
  id: string;
  name: string;
  count: number;
  url: string;
  related: string | undefined;
};

const CONFIG = {
  BASE_URL: "https://musicbrainz.org",
  GENRES_URL: "https://musicbrainz.org/genres",
  REQUEST_DELAY: 1000,
  OUTPUT_DIR: "./output/genres",
  ENTITY_TYPES: [
    "artist",
    "release",
    "release-group",
    "recording",
  ] as EntityType[],
  SELECTORS: {
    GENRE_LIST: '#content ul > li a[href^="/genre/"]',
    ENTITY_COUNT: "#content > p:first-child",
    PAGINATION: '.pagination a[href*="page="]',
    ENTITY_ITEMS: "#content ul > li",
  },
  HEADERS: {
    "User-Agent":
      "MusicBrainzParser (GitHub: outslept; contact me if issues arise; sorry for any inconvenience)",
  },
};

const queue = new PQueue({
  concurrency: 5,
  interval: 1000,
  carryoverConcurrencyCount: true,
});

async function fetchGenres(): Promise<Array<{ id: string; name: string }>> {
  try {
    const { data } = await axios.get(CONFIG.GENRES_URL, {
      timeout: 10000,
      headers: CONFIG.HEADERS,
    });

    const $ = cheerio.load(data);
    return $(CONFIG.SELECTORS.GENRE_LIST)
      .map((_, el) => {
        const href = $(el).attr("href");
        const id = href?.split("/").pop() ?? "";
        const name = $(el).find("bdi").text().trim();
        return { id, name };
      })
      .get()
      .filter((g) => g.id && g.name);
  } catch (error) {
    console.error("Error fetching genres:", error);
    return [];
  }
}

async function processEntityPage(
  url: string,
  entityType: EntityType
): Promise<Entity[]> {
  try {
    const { data } = await axios.get(url, { headers: CONFIG.HEADERS });
    const $ = cheerio.load(data);

    return $(CONFIG.SELECTORS.ENTITY_ITEMS)
      .map((_, li) => {
        const element = $(li);
        const link = element.find(`a[href^="/${entityType}"]`).first();
        const href = link.attr("href");

        if (!href) return null;

        const text = element.text();
        const countMatch = /\d+/.exec(text);
        const count = countMatch ? parseInt(countMatch[0], 10) : 0;

        return {
          id: href.split("/")[2],
          name: link.find("bdi").text().trim(),
          count,
          url: `${CONFIG.BASE_URL}${href}`,
          related: element.find('a[href^="/artist"]').attr("href"),
        };
      })
      .get()
      .filter((e): e is Entity => e !== null);
  } catch (error) {
    console.error(`Error processing entity page ${url}:`, error);
    return [];
  }
}

async function processGenre(genre: { id: string; name: string }) {
  const genreData: Record<EntityType, Entity[]> = {
    artist: [],
    release: [],
    "release-group": [],
    recording: [],
  };

  for (const entityType of CONFIG.ENTITY_TYPES) {
    const baseUrl = `${CONFIG.BASE_URL}/tag/${encodeURIComponent(
      genre.name
    )}/${entityType}`;

    try {
      const { data } = await axios.get(baseUrl, { headers: CONFIG.HEADERS });
      const $ = cheerio.load(data);

      const countText = $(CONFIG.SELECTORS.ENTITY_COUNT).text();
      const countMatch = /\d+/.exec(countText.replace(/,/g, ""));
      const totalItems = countMatch ? parseInt(countMatch[0], 10) : 0;
      const totalPages = Math.ceil(totalItems / 25) || 1;

      const pagePromises = Array.from(
        { length: totalPages },
        (_, i) => i + 1
      ).map((page) =>
        queue.add(() =>
          processEntityPage(`${baseUrl}?page=${page}`, entityType).catch(
            (error) => {
              console.error(`Error processing page ${page}: ${error}`);
              return [];
            }
          )
        )
      );

      const pages = await Promise.all(pagePromises);
      genreData[entityType] = pages
        .flat()
        .filter((e): e is Entity => e !== undefined);
    } catch (error) {
      console.error(
        `Error processing ${entityType} for ${genre.name}: ${error}`
      );
    }
  }

  saveGenreData(genre.name, genreData);
}

function saveGenreData(genreName: string, data: Record<EntityType, Entity[]>) {
  const safeName = genreName.replace(/[^a-z0-9]/gi, "_");
  mkdirSync(`${CONFIG.OUTPUT_DIR}/${safeName}`, { recursive: true });

  for (const [entityType, entities] of Object.entries(data)) {
    const csvData = stringify(entities, {
      header: true,
      columns: ["id", "name", "count", "url", "related"],
    });

    writeFileSync(
      `${CONFIG.OUTPUT_DIR}/${safeName}/${entityType}.csv`,
      csvData
    );
  }
}

async function main() {
  try {
    console.time("Total execution");
    const genres = await fetchGenres();

    const genreQueue = new PQueue({
      concurrency: 2,
      interval: 1000,
    });

    await genreQueue.addAll(
      genres.map((genre) => async () => {
        await processGenre(genre);
      })
    );

    console.timeEnd("Total execution");
  } catch (error) {
    console.error("Critical error:", error);
    process.exit(1);
  }
}

main();
