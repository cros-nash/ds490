import asyncio

from crawlee.crawlers import PlaywrightCrawler, PlaywrightCrawlingContext
import itertools
from bs4 import BeautifulSoup

async def main() -> None:
    crawler = PlaywrightCrawler(
        max_requests_per_crawl=500,
    )

    @crawler.router.default_handler
    async def request_handler(context: PlaywrightCrawlingContext) -> None:
        context.log.info(f'Processing {context.request.url}')
        
        content = await context.page.content()
        document = BeautifulSoup(content, 'html.parser')

        cycle = context.request.url.split('=')[-1]

        tables = []
        for election_group in document.select('.component-wrap:has(h2)'):
            title = election_group.find('h2').text
            
            for row in election_group.select('.DataTable-Partial tbody tr'):
                cells = row.find_all('td')
                party = cells[0].text
                
                tables.append({
                    'title': title,
                    'party': party,
                    'cycle': cycle,
                    'cands': cells[1].text,
                    'total_raised': cells[2].text,
                    'total_spent': cells[3].text,
                    'total_cash': cells[4].text,
                    'total_pacs': cells[5].text,
                    'total_individuals': cells[6].text,
                })

        data = {'tables': tables}
        
        await context.push_data(data)
        
    start_url = "https://www.opensecrets.org/elections-overview"
    cycle_options = [1990, 1992, 1994, 1996, 1998, 2000, 2002, 2004, 2006, 2008, 2010, 2012,
                     2014, 2016, 2018, 2020, 2022, 2024]
    
    cycle_urls = [f"{start_url}?cycle={cycle}" for cycle in cycle_options]

    await crawler.run(cycle_urls)

if __name__ == '__main__':
    asyncio.run(main())
