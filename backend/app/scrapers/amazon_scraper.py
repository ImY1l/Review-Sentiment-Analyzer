from app.database import reviews_collection, products_collection
from datetime import datetime
import uuid
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

SERPAPI_KEY = os.getenv("SERPAPI_KEY")


async def _find_asin(client: httpx.AsyncClient, product_query: str) -> tuple[str | None, dict]:
    """Step 1: Search Amazon to resolve product name → ASIN."""
    print(f"  → Searching Amazon for: '{product_query}'")
    resp = await client.get('https://serpapi.com/search', params={
        'engine':        'amazon',
        'k':             product_query,
        'api_key':       SERPAPI_KEY,
        'amazon_domain': 'amazon.com',
        'language':      'en_US',
    })
    data = resp.json()

    if 'error' in data:
        print(f"  → SerpApi error: {data['error']}")
        return None, {}

    results = data.get('organic_results', [])
    if not results:
        print("  → No Amazon results found.")
        return None, {}

    # Pick first result with a valid ASIN
    for r in results[:5]:
        asin = r.get('asin')
        if asin:
            print(f"  → Found: {r.get('title', '')[:60]} | ASIN: {asin} "
                  f"| Rating: {r.get('rating')} | Reviews: {r.get('reviews')}")
            return asin, r

    print("  → No ASIN found in results.")
    return None, {}


async def scrape_amazon_reviews(product_query: str, user_id: str, max_pages: int = 10) -> dict:
    """
    Scrape Amazon reviews for a product using SerpApi.
    No login, no Playwright, no session files needed.

    Args:
        product_query: Product name (e.g. "iPhone 15")
        user_id:       Current user's ID
        max_pages:     Max review pages (10 reviews per page from amazon_product)
    """
    product_id = str(uuid.uuid4())
    products_collection.insert_one({
        'product_id': product_id,
        'platform':   'amazon',
        'query':      product_query,
        'user_id':    user_id,
        'scraped_at': datetime.utcnow()
    })

    reviews = []

    async with httpx.AsyncClient(timeout=30) as client:

        # ── STEP 1: Resolve product name → ASIN ─────────────────────────────
        print(f"Step 1: Finding ASIN for '{product_query}'...")
        asin, product_info = await _find_asin(client, product_query)

        if not asin:
            return {
                'success':       False,
                'product_id':    product_id,
                'reviews_count': 0,
                'message':       f'No Amazon product found for: {product_query}'
            }

        product_title  = product_info.get('title', product_query)
        overall_rating = product_info.get('rating')
        total_reviews  = product_info.get('reviews')
        product_url    = f"https://www.amazon.com/dp/{asin}"
        price          = product_info.get('price')

        products_collection.update_one(
            {'product_id': product_id},
            {'$set': {
                'asin':           asin,
                'product_title':  product_title,
                'overall_rating': overall_rating,
                'total_reviews':  total_reviews,
                'price':          price,
                'url':            product_url,
            }}
        )

        # ── STEP 2: Fetch product info first ────────────────────────────────
        print(f"Step 2: Getting product info for ASIN {asin}...")
        try:
            resp = await client.get('https://serpapi.com/search', params={
                'engine':        'amazon_product',
                'asin':          asin,
                'api_key':       SERPAPI_KEY,
                'amazon_domain': 'amazon.com',
                'language':      'en_US',
            })
            data = resp.json()
            product_results = data.get('product_results', {})
            products_collection.update_one(
                {'product_id': product_id},
                {'$set': {
                    'product_title':  product_results.get('title', product_title),
                    'overall_rating': product_results.get('rating', overall_rating),
                    'total_reviews':  product_results.get('reviews', total_reviews),
                    'description':    product_results.get('description', ''),
                    'brand':          product_results.get('brand', ''),
                }}
            )
            print(f"  → Product: {product_results.get('title', product_title)[:60]} "
                  f"| Rating: {product_results.get('rating')} "
                  f"| Total reviews: {product_results.get('reviews')}")
        except Exception as e:
            print(f"  → Product info failed: {e}")

        # ── STEP 3: Fetch reviews from amazon_product reviews_information ────
        page_num = 1
        while page_num <= max_pages:
            print(f"Step 3: Scraping reviews page {page_num}...")

            try:
                resp = await client.get('https://serpapi.com/search', params={
                    'engine':        'amazon_product',
                    'asin':          asin,
                    'api_key':       SERPAPI_KEY,
                    'amazon_domain': 'amazon.com',
                    'language':      'en_US',
                    'page':          page_num,
                })
                data = resp.json()
            except Exception as e:
                print(f"  → Request failed: {e}")
                break

            if 'error' in data:
                print(f"  → SerpApi error: {data['error']}")
                break

            # Reviews live inside reviews_information → authors_reviews
            reviews_info = data.get('reviews_information', {})
            page_reviews = reviews_info.get('authors_reviews', [])
            print(f"  → Found {len(page_reviews)} reviews on page {page_num}")

            if not page_reviews:
                print("  → No reviews returned, stopping.")
                break

            reviews.extend([{
                'review_id':     str(uuid.uuid4()),
                'platform':      'amazon',
                'product_id':    product_id,
                'product_query': product_query,
                'product_title': product_title,
                'asin':          asin,
                'reviewer_name': r.get('author', 'Anonymous'),
                'rating':        r.get('rating', 0),
                'title':         r.get('title', ''),
                'comment':       r.get('text', ''),
                'date':          r.get('date', ''),
                'verified':      r.get('verified_purchase', False),
                'helpful_votes': r.get('helpful_votes', ''),
                'variant':       r.get('product', {}).get('flavor_name', '') or
                                 r.get('product', {}).get('size', ''),
                'user_id':       user_id,
                'created_at':    datetime.utcnow()
            } for r in page_reviews if r.get('text')])

            # Check next page
            if not data.get('serpapi_pagination', {}).get('next'):
                print("  → No more pages.")
                break

            page_num += 1

    if reviews:
        reviews_collection.insert_many(reviews)

    print(f"Done. Saved {len(reviews)} Amazon reviews.")
    return {
        'success':       True,
        'product_id':    product_id,
        'reviews_count': len(reviews),
        'message':       f'Scraped {len(reviews)} Amazon reviews for {product_title}'
    }

if __name__ == "__main__":
    import asyncio
    asyncio.run(scrape_amazon_reviews("iPhone 15", "test"))
