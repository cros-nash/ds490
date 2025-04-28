import asyncio

from crawlee.crawlers import PlaywrightCrawler, PlaywrightCrawlingContext

async def main() -> None:
    crawler = PlaywrightCrawler(
        max_requests_per_crawl=100,
    )

    @crawler.router.default_handler
    async def request_handler(context: PlaywrightCrawlingContext) -> None:
        context.log.info(f'Processing {context.request.url}')
        await context.page.wait_for_selector('.col-md-4.col-xl-4.col-lg-4')

        await context.enqueue_links(selector='.col-md-4.col-xl-4.col-lg-4 a.title', label='DETAIL')

        next_button = await context.page.query_selector('button.next')
        if next_button:
            await next_button.click()
            await context.page.wait_for_timeout(1000)

        data = []
        products = await context.page.query_selector_all('.col-md-4.col-xl-4.col-lg-4')
        for product in products:
            name = await product.query_selector('h4 a.title')
            name = await name.inner_text() if name else ""
            description = await product.query_selector('p.description.card-text')
            description = await description.inner_text() if description else ""
            price = await product.query_selector('h4.price float-end.card-title span')
            price = int(float(await price.inner_text().replace('$', '').strip())) if price else 0
            
            data.append({
                'name': name,
                'description': description,
                'price': price
            })
        
        await context.push_data({'functions': data})
        
    await crawler.run(['https://webscraper.io/test-sites/e-commerce/static/computers/laptops'])


if __name__ == '__main__':
    asyncio.run(main())

