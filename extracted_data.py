import asyncio

from crawlee.crawlers import PlaywrightCrawler, PlaywrightCrawlingContext
from bs4 import BeautifulSoup

async def main() -> None:
    crawler = PlaywrightCrawler(
        max_requests_per_crawl=500,
    )

    @crawler.router.default_handler
    async def request_handler(context: PlaywrightCrawlingContext) -> None:
        context.log.info(f'Processing {context.request.url}')
        
        page = await context.page.content()
        soup = BeautifulSoup(page, 'html.parser')
        
        events = []
        for event in soup.select('.rhov'):
            date = event.select_one('div:nth-child(1)').get_text(strip=True)
            title = event.select_one('div:nth-child(2)').get_text(strip=True)
            location = event.select_one('div:nth-child(3)').get_text(strip=True)
            events.append({'title': title, 'date': date, 'location': location})
        
        data = {'events': events}
        
        await context.push_data(data)
        
    await crawler.run(['http://www.techmeme.com/events'])


if __name__ == '__main__':
    asyncio.run(main())
