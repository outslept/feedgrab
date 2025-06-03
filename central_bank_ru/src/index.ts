import { parse } from "node-html-parser";
import { Workbook } from "exceljs";
import { mkdirSync, writeFileSync } from "node:fs";

interface Currency {
  digitalCode: string;
  letterCode: string;
  units: number;
  currencyName: string;
  exchangeRate: number;
  date: Date;
}

const log = (message: string) => console.log(`[${new Date().toISOString()}] ${message}`);
const logError = (message: string) => console.error(`[${new Date().toISOString()}] ERROR: ${message}`);

const formatDate = (date: Date) =>
  `${date.getDate().toString().padStart(2, '0')}.${(date.getMonth() + 1).toString().padStart(2, '0')}.${date.getFullYear()}`;

const parseDate = (dateString: string) => {
  const [day, month, year] = dateString.split('.').map(Number);
  return new Date(year, month - 1, day);
};

const generateDateRange = (start: Date, end: Date): Date[] => {
  const dates: Date[] = [];
  for (const current = new Date(start); current <= end; current.setDate(current.getDate() + 1)) {
    dates.push(new Date(current));
  }
  return dates;
};

async function fetchCurrencyData(date: Date): Promise<string | null> {
  try {
    const response = await fetch(
      `https://cbr.ru/currency_base/daily/?UniDbQuery.Posted=True&UniDbQuery.To=${formatDate(date)}`,
      { signal: AbortSignal.timeout(10000) }
    );

    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return await response.text();
  } catch (error) {
    logError(`Fetch failed for ${formatDate(date)}: ${error.message}`);
    return null;
  }
}

function parseCurrencyData(html: string, date: Date): Currency[] {
  return parse(html)
    .querySelectorAll("table.data tbody tr")
    .slice(1)
    .map(row => {
      const cols = row.querySelectorAll("td");
      return {
        digitalCode: cols[0].text.trim(),
        letterCode: cols[1].text.trim(),
        units: Number(cols[2].text.trim()),
        currencyName: cols[3].text.trim(),
        exchangeRate: parseFloat(cols[4].text.trim().replace(",", ".")),
        date
      };
    })
    .filter(c => c.digitalCode);
}

async function exportData(currencies: Currency[]) {
  const date = currencies[0].date;
  const baseDir = `data/${date.getFullYear()}/${(date.getMonth() + 1).toString().padStart(2, '0')}/${date.getDate().toString().padStart(2, '0')}`;

  mkdirSync(baseDir, { recursive: true });

  const baseName = `${baseDir}/currency_${formatDate(date)}`;

  // TXT
  writeFileSync(`${baseName}.txt`, currencies
    .map(c => `${formatDate(c.date)} | ${c.letterCode.padEnd(5)} | ${c.exchangeRate.toFixed(4)}`)
    .join("\n"));

  // CSV
  writeFileSync(`${baseName}.csv`,
    "Date,Code,Currency,Rate\n" +
    currencies.map(c => `${formatDate(c.date)},${c.digitalCode},${c.letterCode},${c.exchangeRate}`).join("\n")
  );

  // XLSX
  const workbook = new Workbook();
  workbook.addWorksheet("Currencies").addRows(
    currencies.map(c => [formatDate(c.date), c.digitalCode, c.letterCode, c.exchangeRate])
  );
  await workbook.xlsx.writeFile(`${baseName}.xlsx`);
}

async function main() {
  const dates = generateDateRange(parseDate("01.07.1992"), new Date());

  log(`Processing ${dates.length} days`);

  for (const date of dates) {
    const html = await fetchCurrencyData(date);
    if (!html) continue;

    const data = parseCurrencyData(html, date);
    if (data.length > 0) {
      await exportData(data);
      log(`Processed ${formatDate(date)}: ${data.length} currencies`);
    }

    await new Promise(resolve => setTimeout(resolve, 500));
  }

  log("Completed!");
}

main()
