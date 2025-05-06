import asyncio

from crawlee.crawlers import PlaywrightCrawler, PlaywrightCrawlingContext

async def main() -> None:
    crawler = PlaywrightCrawler(
        max_requests_per_crawl=500,
    )

    @crawler.router.default_handler
    async def request_handler(context: PlaywrightCrawlingContext) -> None:
        context.log.info(f'Processing {context.request.url}')
        
        items = []
        # Navigate through the pages using context.page.goto()
        for page_num in range(1, 3):
            await context.page.goto(f'https://webscraper.io/test-sites/e-commerce/static/computers/laptops?page={page_num}')
            product_cards = await context.page.query_selector_all('.col-md-4.col-xl-4.col-lg-4')
            for card in product_cards:
                name = await card.query_selector('.title')
                description = await card.query_selector('.description.card-text')
                price = await card.query_selector('.price span')

                name_text = await name.inner_text()
                description_text = await description.inner_text()
                price_text = await price.inner_text()

                items.append({
                    'name': name_text,
                    'description': description_text,
                    'price': float(price_text.replace('$', ''))
                })

        data = {'items': items}
        
        await context.push_data(data)
        
    await crawler.run(['https://webscraper.io/test-sites/e-commerce/static/computers/laptops?page=1'])


if __name__ == '__main__':
    asyncio.run(main())
