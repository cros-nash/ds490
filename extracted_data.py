import asyncio

from crawlee.crawlers import PlaywrightCrawler, PlaywrightCrawlingContext

async def main() -> None:
    crawler = PlaywrightCrawler(
        max_requests_per_crawl=500,
    )

    @crawler.router.default_handler
    async def request_handler(context: PlaywrightCrawlingContext) -> None:
        context.log.info(f'Processing {context.request.url}')
        
        if context.request.url.endswith('page=1') or context.request.url.endswith('page=2'):
            await context.page.wait_for_selector('.card.thumbnail')
            products = await context.page.query_selector_all('.card.thumbnail')
            records = []
            for product in products:
                name_element = await product.query_selector('.title')
                name = await name_element.evaluate('(el) => el.innerText.trim()')
                
                description_element = await product.query_selector('.description.card-text')
                description = await description_element.evaluate('(el) => el.innerText.trim()')
                
                price_element = await product.query_selector('[itemprop="price"]')
                price_text = await price_element.evaluate('(el) => el.innerText.replace("$", "").trim()')
                price = float(price_text)
                
                records.append({'name': name, 'description': description, 'price': price})

            data = {'records': records}
        
            await context.push_data(data)
        
    await crawler.run(['https://webscraper.io/test-sites/e-commerce/static/computers/laptops?page=1', 
                       'https://webscraper.io/test-sites/e-commerce/static/computers/laptops?page=2'])


if __name__ == '__main__':
    asyncio.run(main())
