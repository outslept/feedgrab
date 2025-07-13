import { SteamDBParser } from './src/index';

async function main() {
  const parser = await SteamDBParser.create('us');

  try {
    const canConnect = await parser.canConnect();

    if (!canConnect) {
      console.error('Connection failed');
      return;
    }

    const steamId = '76561198287455504';
    const profile = await parser.getSteamDBProfile(steamId);

    console.log('\nProfile Data:');
    Object.entries(profile).forEach(([key, value]) => {
      if (value != null) {
        console.log(`${key}: ${value}`);
      }
    });

  } catch (error) {
    console.error('Error:', error);
  } finally {
    await parser.close();
  }
}

main().catch(console.error);
