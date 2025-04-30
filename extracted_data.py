import asyncio
import re

from crawlee.crawlers import PlaywrightCrawler, PlaywrightCrawlingContext

def clean_title(title):
    # Standardize event titles
    clean_title = re.sub(r'Web Summit.*', 'Web Summit', title)
    clean_title = re.sub(r'Visa’s Global Product Drop Event.*', 'Visa’s Global Product Drop Event', clean_title)
    
    # Remove unnecessary suffixes like "REGISTER FOR LIVESTREAM", "HYBRID", "VIRTUAL" indicators
    clean_title = re.sub(r"(REGISTER FOR LIVESTREAM|HYBRID|VIRTUAL)", "", clean_title)
    return clean_title.strip()

async def main() -> None:
    crawler = PlaywrightCrawler(
        max_requests_per_crawl=500,
    )

    @crawler.router.default_handler
    async def request_handler(context: PlaywrightCrawlingContext) -> None:
        context.log.info(f'Processing {context.request.url}')
        
        page = context.page
        events = []
        
        # Extract the events information
        event_divs = await page.query_selector_all('div.rhov:not(:contains("Earnings"))')
        
        for event_div in event_divs:
            date_element = await event_div.query_selector('div:nth-child(1)')
            title_element = await event_div.query_selector('div:nth-child(2)')
            location_element = await event_div.query_selector('div:nth-child(3)')
            
            date = await date_element.text_content() if date_element else ''
            title = await title_element.text_content() if title_element else ''
            location = await location_element.text_content() if location_element else ''
            
            # Clean and normalize text
            title = clean_title(title)
            if location.strip() == '':
                location = 'NA'
            
            event_data = {
                'title': title,
                'date': date,
                'location': location
            }
            
            events.append(event_data)
        
        data = {'events': events}
        
        await context.push_data(data)
        
    await crawler.run(['https://www.techmeme.com/events'])

if __name__ == '__main__':
    asyncio.run(main())
