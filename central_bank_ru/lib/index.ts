import { createObjectCsvWriter as createCsvWriter } from "csv-writer";
import { format, parse, addDays, differenceInDays } from "date-fns";
import * as cheerio from "cheerio";
import * as ExcelJS from "exceljs";
import * as fs from "node:fs";
import axios from "axios";
import pino from "pino";

const logger = pino({
  level: "info",
  transport: {
    target: "pino-pretty",
    options: { colorize: true },
  },
});

interface Currency {
  digitalCode: string;
  letterCode: string;
  units: number;
  currencyName: string;
  exchangeRate: number;
  date: Date;
}

const formatDate = (date: Date) => format(date, "dd.MM.yyyy");
const parseDateString = (dateString: string) =>
  parse(dateString, "dd.MM.yyyy", new Date());

const generateDateRange = (start: Date, end: Date): Date[] => {
  const days = differenceInDays(end, start);
  return Array.from({ length: days + 1 }, (_, i) => addDays(start, i));
};

async function fetchCurrencyData(date: Date): Promise<string | null> {
  const url = `https://cbr.ru/currency_base/daily/?UniDbQuery.Posted=True&UniDbQuery.To=${formatDate(
    date
  )}`;

  try {
    logger.debug(`Fetching: ${formatDate(date)}`);
    const { data } = await axios.get(url, { timeout: 10000 });
    return data;
  } catch (error) {
    logger.error(`Fetch failed for ${formatDate(date)}: ${error.message}`);
    return null;
  }
}

function parseCurrencyData(html: string, date: Date): Currency[] {
  const $ = cheerio.load(html);
  const currencies: Currency[] = [];

  $("table.data tbody tr")
    .slice(1)
    .each((_, row) => {
      const cols = $(row).find("td");
      currencies.push({
        digitalCode: cols.eq(0).text().trim(),
        letterCode: cols.eq(1).text().trim(),
        units: Number(cols.eq(2).text().trim()),
        currencyName: cols.eq(3).text().trim(),
        exchangeRate: parseFloat(cols.eq(4).text().trim().replace(",", ".")),
        date: date,
      });
    });

  return currencies;
}

async function exportData(
  currencies: Currency[],
  formats: string[] = ["txt", "csv", "xlsx"]
) {
  const date = currencies[0].date;
  const year = format(date, "yyyy");
  const month = format(date, "MM");
  const day = format(date, "dd");

  const baseDir = `data/${year}/${month}/${day}`;
  fs.mkdirSync(baseDir, { recursive: true });

  const baseName = `${baseDir}/currency_${formatDate(date)}`;

  for (const format of formats) {
    try {
      if (format === "txt") {
        const content = currencies
          .map(
            (c) =>
              `${formatDate(c.date)} | ${c.letterCode.padEnd(
                5
              )} | ${c.exchangeRate.toFixed(4)}`
          )
          .join("\n");
        fs.writeFileSync(`${baseName}.txt`, content);
      }

      if (format === "csv") {
        const csvWriter = createCsvWriter({
          path: `${baseName}.csv`,
          header: [
            { id: "date", title: "Date" },
            { id: "digitalCode", title: "Code" },
            { id: "letterCode", title: "Currency" },
            { id: "exchangeRate", title: "Rate" },
          ],
        });
        await csvWriter.writeRecords(currencies);
      }

      if (format === "xlsx") {
        const workbook = new ExcelJS.Workbook();
        const sheet = workbook.addWorksheet("Currencies");
        sheet.addRows(
          currencies.map((c) => [
            formatDate(c.date),
            c.digitalCode,
            c.letterCode,
            c.exchangeRate,
          ])
        );
        await workbook.xlsx.writeFile(`${baseName}.xlsx`);
      }
    } catch (error) {
      logger.error(`Export error (${format}): ${error.message}`);
    }
  }
}

async function main() {
  const startDate = parseDateString("01.07.1992");
  const endDate = new Date();
  const dates = generateDateRange(startDate, endDate);

  logger.info(`Processing ${dates.length} days`);

  for (const date of dates) {
    try {
      const html = await fetchCurrencyData(date);
      if (!html) continue;

      const data = parseCurrencyData(html, date);
      if (data.length > 0) {
        await exportData(data);
        logger.info(`Processed ${formatDate(date)}: ${data.length} currencies`);
      }

      await new Promise((resolve) => setTimeout(resolve, 500)); // :)
    } catch (error) {
      logger.error(`Processing error: ${error.message}`);
    }
  }

  logger.info("Completed!");
}

main().catch((error) => logger.error(error));
