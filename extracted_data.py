import asyncio

from crawlee.crawlers import PlaywrightCrawler, PlaywrightCrawlingContext

async def main() -> None:
    crawler = PlaywrightCrawler(
        max_requests_per_crawl=500,
    )

    @crawler.router.default_handler
    async def request_handler(context: PlaywrightCrawlingContext) -> None:
        context.log.info(f'Processing {context.request.url}')
        
        html = await context.page.content()
        items = []
        
        for page in range(1, 3):
            selector = f'.col-md-4.col-xl-4.col-lg-4'
            products = context.page.locator(selector)

            count = await products.count()
            for index in range(count):
                product = products.nth(index)
                name = await product.locator('.title').inner_text()
                description = await product.locator('.description.card-text').inner_text()
                price_text = await product.locator('.price span').inner_text()
                price = float(price_text.replace('$', '').replace(',', ''))
                
                items.append({
                    'name': name,
                    'description': description,
                    'price': price
                })
                
            if page < 2:
                next_page_link = f'https://webscraper.io/test-sites/e-commerce/static/computers/laptops?page={page + 1}'
                await context.page.goto(next_page_link)

        data = {'items': items}
        
        await context.push_data(data)
        
    await crawler.run(['https://webscraper.io/test-sites/e-commerce/static/computers/laptops'])


if __name__ == '__main__':
    asyncio.run(main())
