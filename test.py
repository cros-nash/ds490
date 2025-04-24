import asyncio

from crawlee.crawlers import PlaywrightCrawler, PlaywrightCrawlingContext

async def main() -> None:
    crawler = PlaywrightCrawler(
        max_requests_per_crawl=10,
    )

    @crawler.router.default_handler
    async def request_handler(context: PlaywrightCrawlingContext) -> None:
        context.log.info(f'Processing {context.request.url}')
        await context.page.wait_for_selector('table.DataTable-Partial')

        html = await context.page.content()
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        projects = []
        for table in soup.find_all('table', class_='DataTable-Partial'):
            previous_h2 = table.find_previous_sibling('h2')
            cycle = previous_h2.text.strip() if previous_h2 else 'Unknown Cycle'
            for row in table.find('tbody').find_all('tr'):
                cols = row.find_all('td')
                if len(cols) > 0:
                    party = cols[0].text.strip()
                    cands = cols[1].text.strip().replace(',', '')
                    total_raised = cols[2].text.strip().replace('$', '').replace(',', '')
                    total_spent = cols[3].text.strip().replace('$', '').replace(',', '')
                    total_cash = cols[4].text.strip().replace('$', '').replace(',', '')
                    total_pacs = cols[5].text.strip().replace('$', '').replace(',', '')
                    total_individuals = cols[6].text.strip().replace('$', '').replace(',', '')
                    data = {
                        'title': f'Financial activity for {party} in {cycle}',
                        'party': party,
                        'cycle': cycle,
                        'cands': cands,
                        'total_raised': total_raised,
                        'total_spent': total_spent,
                        'total_cash': total_cash,
                        'total_pacs': total_pacs,
                        'total_individuals': total_individuals,
                    }
                    await context.push_data(data)
        
                

    await crawler.run(['https://www.opensecrets.org/elections-overview'])


if __name__ == '__main__':
    asyncio.run(main())