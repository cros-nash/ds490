import asyncio

from crawlee.crawlers import PlaywrightCrawler, PlaywrightCrawlingContext
from bs4 import BeautifulSoup
import itertools
import time

async def main() -> None:
    crawler = PlaywrightCrawler(
        max_requests_per_crawl=500,
    )

    @crawler.router.default_handler
    async def request_handler(context: PlaywrightCrawlingContext) -> None:
        context.log.info(f'Processing {context.request.url}')
        
        page = await context.page.content()
        soup = BeautifulSoup(page, 'html.parser')
        
        cases = []
        for case_row in soup.select('table.case-list tr'):
            case_number = case_row.select_one('.case-number').text.strip()
            filing_date = case_row.select_one('.filing-date').text.strip()
            plaintiff_name = case_row.select_one('.plaintiff-name').text.strip()
            defendant_name = case_row.select_one('.defendant-name').text.strip()
            case_outcome = case_row.select_one('.case-outcome').text.strip()
            county = case_row.select_one('.county').text.strip()
            
            case_history = []
            for event in case_row.select('.case-history .event'):
                event_date = event.select_one('.event-date').text.strip()
                event_description = event.select_one('.event-description').text.strip()
                case_history.append({
                    'event_date': event_date,
                    'event_description': event_description
                })
            
            cases.append({
                'case_number': case_number,
                'filing_date': filing_date,
                'plaintiff_name': plaintiff_name,
                'defendant_name': defendant_name,
                'case_outcome': case_outcome,
                'case_history': case_history,
                'county': county
            })
        
        data = {'cases': cases}
        
        await context.push_data(data)
        
        time.sleep(1)  # Implementing delay between requests
        
    await crawler.run(['https://www.oscn.net/dockets/Search.aspx'])


if __name__ == '__main__':
    asyncio.run(main())
