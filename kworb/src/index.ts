import { writeFileSync, mkdirSync } from "node:fs";
import { parse } from "node-html-parser";
import { setTimeout } from "node:timers/promises";

interface Video {
  title: string;
  videoId: string;
  views: number;
  dailyViews: number;
  rank: number;
  url: string;
}

async function fetchCategories() {
  const response = await fetch("https://kworb.net/youtube/stats.html", {
    headers: { "User-Agent": "KworbParser" },
  });
  const root = parse(await response.text());

  return root.querySelectorAll('.subcontainer a')
    .map(el => ({
      name: el.text.trim(),
      url: `https://kworb.net/youtube/${el.getAttribute('href')}`,
    }))
    .filter(category => category.url && !category.url.includes('#'));
}

async function parseVideoPage(url: string) {
  const response = await fetch(url, {
    headers: { "User-Agent": "KworbParser" },
  });
  const root = parse(await response.text());
  const rows = root.querySelector('table.addpos tbody')?.querySelectorAll('tr') || [];

  return rows.map((row, index) => {
    const cells = row.querySelectorAll('td');
    const link = cells[0]?.querySelector('a');
    const href = link?.getAttribute('href') || '';
    const videoId = href.replace('video/', '').replace('.html', '');

    return {
      rank: index + 1,
      title: link?.text.trim() || '',
      videoId,
      views: parseInt(cells[1]?.text.replace(/,/g, '') || '0'),
      dailyViews: parseInt(cells[2]?.text.replace(/,/g, '') || '0'),
      url: `https://youtube.com/watch?v=${videoId}`,
    };
  });
}

function saveData(categoryName: string, videos: Video[]) {
  const safeName = categoryName.replace(/[^a-z0-9]/gi, "_").toLowerCase();
  mkdirSync("./output/youtube", { recursive: true });

  writeFileSync(`./output/youtube/${safeName}.csv`,
    "rank,title,videoId,views,dailyViews,url\n" +
    videos.map(v => `${v.rank},"${v.title.replace(/"/g, '""')}",${v.videoId},${v.views},${v.dailyViews},${v.url}`).join('\n')
  );

  writeFileSync(`./output/youtube/${safeName}.md`, [
    `# ${categoryName}\n`,
    "| Rank | Title | Views | Daily Views | URL |",
    "|------|--------|-------|-------------|-----|",
    ...videos.map(v => `| ${v.rank} | ${v.title} | ${v.views.toLocaleString()} | ${v.dailyViews.toLocaleString()} | [Watch](${v.url}) |`)
  ].join('\n'));
}

async function main() {
  console.time("Total execution");

  const categories = await fetchCategories();
  console.log(`Found ${categories.length} categories`);

  for (const category of categories) {
    console.log(`Processing category: ${category.name}`);

    const videos = await parseVideoPage(category.url);

    if (videos.length > 0) {
      saveData(category.name, videos);
      console.log(`Saved ${videos.length} videos for ${category.name}`);
    }

    await setTimeout(1000);
  }

  console.timeEnd("Total execution");
}

main();
