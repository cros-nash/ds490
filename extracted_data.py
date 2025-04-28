import asyncio

from crawlee.crawlers import PlaywrightCrawler, PlaywrightCrawlingContext

async def main() -> None:
    crawler = PlaywrightCrawler(
        max_requests_per_crawl=500,
    )

    @crawler.router.default_handler
    async def request_handler(context: PlaywrightCrawlingContext) -> None:
        context.log.info(f'Processing {context.request.url}')

        await context.page.wait_for_selector('.DataTable-Partial')

        election_cycle_dropdown = context.page.locator('.js-customSelect').first
        election_cycle = await election_cycle_dropdown.evaluate('element => element.value')

        tables = []
        tables_elements = await context.page.query_selector_all('.component-wrap')
        for table_elem in tables_elements:
            position_title_element = await table_elem.query_selector('h2')
            if position_title_element:
                position_title = await position_title_element.text_content()
            else:
                position_title = ''

            data_rows = await table_elem.query_selector_all('tbody tr')
            for row in data_rows:
                party_element = await row.query_selector('td.color-category, td.color-category.blue, td.color-category.red')
                if party_element:
                    party = await party_element.text_content()
                else:
                    party = 'Unknown'

                cands_element = await row.query_selector('td:nth-child(2)')
                cands = cands_element.text_content() if cands_element else ''

                total_raised_element = await row.query_selector('td:nth-child(3)')
                total_raised = total_raised_element.text_content() if total_raised_element else ''

                total_spent_element = await row.query_selector('td:nth-child(4)')
                total_spent = total_spent_element.text_content() if total_spent_element else ''

                total_cash_element = await row.query_selector('td:nth-child(5)')
                total_cash = total_cash_element.text_content() if total_cash_element else ''

                total_pacs_element = await row.query_selector('td:nth-child(6)')
                total_pacs = total_pacs_element.text_content() if total_pacs_element else ''

                total_individuals_element = await row.query_selector('td:nth-child(7)')
                total_individuals = total_individuals_element.text_content() if total_individuals_element else ''

                tables.append({
                    'title': position_title,
                    'party': party,
                    'cycle': election_cycle,
                    'cands': cands,
                    'total_raised': total_raised,
                    'total_spent': total_spent,
                    'total_cash': total_cash,
                    'total_pacs': total_pacs,
                    'total_individuals': total_individuals,
                })

        data = {'tables': tables}

        await context.push_data(data)
        
    await crawler.run(['https://www.opensecrets.org/elections-overview'])

if __name__ == '__main__':
    asyncio.run(main())
