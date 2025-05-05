import asyncio

from crawlee.crawlers import PlaywrightCrawler, PlaywrightCrawlingContext

async def main() -> None:
    crawler = PlaywrightCrawler(
        max_requests_per_crawl=500,
    )

    @crawler.router.default_handler
    async def request_handler(context: PlaywrightCrawlingContext) -> None:
        context.log.info(f'Processing {context.request.url}')
        
        elements = await context.page.query_selector_all('article.col--6')
        
        examples = []
        
        for element in elements:
            name = await (await element.query_selector('h2.cardTitle_rnsV')).text_content()
            if name in ["Crawl all links on website", "Crawl multiple URLs"]:
                examples.append({
                    'name': name,
                    'description': await (await element.query_selector('p.cardDescription_PWke')).text_content(),
                    'url': await (await element.query_selector('a.cardContainer_fWXF')).get_attribute('href')
                })
        
        data = {'examples': examples}
        
        await context.push_data(data)
        
    await crawler.run(['https://crawlee.dev/python/docs/examples'])


if __name__ == '__main__':
    asyncio.run(main())
