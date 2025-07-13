# Steamdb Parser

TypeScript parser for extracting Steam profile data from SteamDB calculator pages using Playwrightw.

## Usage

```ts
import { SteamDBParser } from './src/index';

const parser = SteamDBParser.create('us');
const profile = parser.getSteamDBProfile('76561198287455504');
console.log(profile);
await parser.close();
```

## Environment Variables

- `DEBUG=1` - Enable debug logs
- `VERBOSE=0` - Enable verbose output
- `TIMING=1` - Add timestamp to logs
- `HEADLESS=0` - Run browser in visible mode

## Data Structure

Extracts: display name, avatar, level, games count, playtime, account value, vanity URL, account age.
