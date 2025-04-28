import asyncio

from crawlee.crawlers import PlaywrightCrawler, PlaywrightCrawlingContext

async def main() -> None:
    crawler = PlaywrightCrawler(
        max_requests_per_crawl=500,
    )

    @crawler.router.default_handler
    async def request_handler(context: PlaywrightCrawlingContext) -> None:
        context.log.info(f'Processing {context.request.url}')
        
        product_elements = await context.page.query_selector_all('div.col-md-4.col-xl-4.col-lg-4')
        items = []

        for product_element in product_elements:
            name = await product_element.query_selector('h4 > a.title')
            name_text = await name.inner_text() if name else ''

            description = await product_element.query_selector('p.description.card-text')
            description_text = await description.inner_text() if description else ''

            price = await product_element.query_selector('h4.price > span')
            price_text = await price.inner_text() if price else ''
            price_value = float(price_text.replace('$', '').replace(',', '')) if price_text else 0.0

            items.append({
                'name': name_text,
                'description': description_text,
                'price': price_value
            })

        data = {'items': items}
        
        await context.push_data(data)
        
    await crawler.run(['https://webscraper.io/test-sites/e-commerce/static/computers/laptops?page=1', 'https://webscraper.io/test-sites/e-commerce/static/computers/laptops?page=2'])


if __name__ == '__main__':
    asyncio.run(main())