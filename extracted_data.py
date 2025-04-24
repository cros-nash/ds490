from crawlee.crawlers import PlaywrightCrawlingContext
from crawlee.router import Router

router = Router[PlaywrightCrawlingContext]()

@router.default_handler
async def default_handler(context: PlaywrightCrawlingContext) -> None:
    context.log.info(f'default_handler is processing {context.request.url}')

    await context.wait_for_selector('.projects')

    await context.enqueue_links(selector='a.dropdown-item', label='CATEGORY')

@router.handler('CATEGORY')
async def category_handler(context: PlaywrightCrawlingContext) -> None:
    context.log.info(f'category_handler is processing {context.request.url}')

    await context.wait_for_selector('.projects')

    await context.enqueue_links(selector='a.grid-item > div.card.hoverable', label='DETAIL')

    # No pagination logic needed

@router.handler('DETAIL')
async def detail_handler(context: PlaywrightCrawlingContext) -> None:
    context.log.info(f'detail_handler is processing {context.request.url}')

    data = {'projects': []}

    project_title = await context.selector('h4.card-title').text()
    project_description = await context.selector('p.card-text').text()
    data['projects'].append({
        'title': {'type': 'string', 'description': project_title},
        'description': {'type': 'string', 'description': project_description},
    })

    await context.push_data(data)

