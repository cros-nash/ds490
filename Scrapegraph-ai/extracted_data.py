import asyncio
from crawlee.crawlers import PlaywrightCrawler, PlaywrightCrawlingContext

async def main() -> None:
    crawler = PlaywrightCrawler(
        max_requests_per_crawl=10,
    )

    @crawler.router.default_handler
    async def request_handler(context: PlaywrightCrawlingContext) -> None:
        context.log.info(f'Processing {context.request.url}')
        
        try:
            # Verify and update actual selector based on live site inspection
            await context.page.wait_for_load_state('networkidle')  # Ensure all network requests are completed

            articles = []
            elements = await context.page.query_selector_all('.actual-article-container-class')  # Update based on live site
            
            for element in elements:
                title_el = await element.query_selector('.actual-title-class')  # Update based on live site
                description_el = await element.query_selector('.actual-description-class')  # Update based on live site
                category_el = await element.query_selector('.actual-category-class')  # Update based on live site
                content_el = await element.query_selector('.actual-content-class')  # Update based on live site

                article_data = {
                    'title': {
                        'type': 'string',
                        'description': await title_el.text_content() if title_el else ''
                    },
                    'description': {
                        'type': 'string',
                        'description': await description_el.text_content() if description_el else ''
                    },
                    'category': {
                        'type': 'string',
                        'description': await category_el.text_content() if category_el else ''
                    },
                    'content': {
                        'type': 'string',
                        'description': await content_el.text_content() if content_el else ''
                    }
                }
                
                articles.append(article_data)
            
            data = {'articles': articles}
            
            await context.push_data(data)
        
        except Exception as e:
            context.log.error(f'An error occurred: {e}')
        
    await crawler.run(['https://getpocket.com/explore/pocket-hits'])

if __name__ == '__main__':
    asyncio.run(main())
