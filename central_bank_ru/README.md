# CBR Currency Parser

A TypeScript parser for extracting currency exchange rates from the Central Bank of Russia (CBR) website.

## Overview

This tool parses historical currency exchange rates from CBR's web interface and exports data in multiple formats (TXT, CSV, XLSX). While CBR provides an official API for this data, I've decided not to take an easy road with this.

## Usage

```typescript
npm run scrape
```

Data will be saved to `data/YYYY/MM/DD/` directory structure.

## Output Formats

- **TXT**
- **CSV**
- **XLSX**

