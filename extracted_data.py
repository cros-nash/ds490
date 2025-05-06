import asyncio

from crawlee.crawlers import PlaywrightCrawler, PlaywrightCrawlingContext

async def request_handler(context: PlaywrightCrawlingContext) -> None:
    context.log.info(f'Processing {context.request.url}')

    if context.request.url.endswith('?page=1'):
        page_numbers = [1, 2]
    else:
        page_numbers = []

    products = []
    for page in page_numbers:
        await context.page.goto(f'https://webscraper.io/test-sites/e-commerce/static/computers/laptops?page={page}')
        await context.page.wait_for_selector('.card.thumbnail')  # Wait for the product elements to load
        product_elements = await context.page.query_selector_all('.card.thumbnail')  # Use Playwright to select product elements
        
        for product in product_elements:
            name_element = await product.query_selector('a.title')
            description_element = await product.query_selector('p.description.card-text')
            price_element = await product.query_selector('h4.price > span')
            
            name = await name_element.text_content() if name_element else ''
            description = await description_element.text_content() if description_element else ''
            price_text = await price_element.text_content() if price_element else ''
            price = float(price_text.replace('$', '').strip()) if price_text else 0.0
            
            products.append({
                'name': name.strip(),
                'description': description.strip(),
                'price': price
            })

    data = {'records': products}
    
    await context.push_data(data)

async def main() -> None:
    crawler = PlaywrightCrawler(
        max_requests_per_crawl=500,
    )

    crawler.router.default_handler(request_handler)  # Register the handler

    await crawler.run(['https://webscraper.io/test-sites/e-commerce/static/computers/laptops?page=1'])

if __name__ == '__main__':
    asyncio.run(main())
