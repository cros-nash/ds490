import asyncio
from crawlee.crawlers import PlaywrightCrawler, PlaywrightCrawlingContext
from crawlee.storages import Dataset
import itertools

async def main() -> None:
    crawler = PlaywrightCrawler(
        max_requests_per_crawl=500,
    )

    @crawler.router.default_handler
    async def request_handler(context: PlaywrightCrawlingContext) -> None:
        context.log.info(f'Processing {context.request.url}')
        
        page = context.page
        title_elements = await page.query_selector_all('div.component-wrap h2')
        table_elements = await page.query_selector_all('table.DataTable-Partial')
        
        tables = []
        for title, table in zip(title_elements, table_elements):
            title_text = await title.text_content()
            rows = await table.query_selector_all('tbody tr')
            for row in rows:
                cell_handle = await row.query_selector('td.color-category')
                party = await cell_handle.inner_text() if cell_handle else 'N/A'
                
                columns = await row.query_selector_all('td.number')
                if len(columns) >= 6:
                    cands = await columns[0].inner_text()
                    total_raised = await columns[1].inner_text()
                    total_spent = await columns[2].inner_text()
                    total_cash = await columns[3].inner_text()
                    total_pacs = await columns[4].inner_text()
                    total_individuals = await columns[5].inner_text()

                    tables.append({
                        'title': title_text.strip(),
                        'party': party.strip(),
                        'cycle': context.request.url.split('=')[-1],
                        'cands': cands.strip(),
                        'total_raised': total_raised.strip(),
                        'total_spent': total_spent.strip(),
                        'total_cash': total_cash.strip(),
                        'total_pacs': total_pacs.strip(),
                        'total_individuals': total_individuals.strip(),
                    })

        data = {
            'tables': tables
        }

        await context.push_data(data)

    cycles = [str(year) for year in range(1990, 2025, 2)]
    urls = [f'https://www.opensecrets.org/elections-overview?cycle={cycle}' for cycle in cycles]
    
    await crawler.run(urls)

if __name__ == '__main__':
    asyncio.run(main())
