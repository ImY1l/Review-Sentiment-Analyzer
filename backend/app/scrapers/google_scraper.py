# app/scrapers/google_scraper.py
from app.database import reviews_collection, products_collection
from datetime import datetime
import uuid
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

SERPAPI_KEY = os.getenv("SERPAPI_KEY")


# ── SHARED HELPER ────────────────────────────────────────────────────────────

async def _find_place_id(client: httpx.AsyncClient, place_query: str) -> tuple[str | None, dict]:
    """Resolve a place name → place_id using google_maps engine."""
    print(f"  → Searching Google Maps for: {place_query}")
    resp = await client.get('https://serpapi.com/search', params={
        'engine': 'google_maps',
        'q': place_query,
        'api_key': SERPAPI_KEY,
        'hl': 'en',
    })
    data = resp.json()

    if 'error' in data:
        print(f"  → SerpApi error: {data['error']}")
        return None, {}

    local_results = data.get('local_results', [])
    if not local_results:
        print("  → No places found.")
        return None, {}

    place = local_results[0]
    place_id = place.get('place_id')
    return place_id, place


async def _find_google_product_id(client: httpx.AsyncClient, product_query: str) -> tuple[str | None, str | None]:
    """Resolve a product name → Google Shopping product_id."""
    print(f"  → Searching Google Shopping for: {product_query}")
    resp = await client.get('https://serpapi.com/search', params={
        'engine': 'google_shopping',
        'q': product_query,
        'api_key': SERPAPI_KEY,
        'hl': 'en',
        'gl': 'my',
    })
    data = resp.json()

    if 'error' in data:
        print(f"  → SerpApi error: {data['error']}")
        return None, None

    for r in data.get('shopping_results', [])[:5]:
        pid = r.get('product_id')
        if pid:
            print(f"  → Found: {r.get('title')} (id: {pid})")
            return pid, r.get('title', product_query)

    print("  → No product_id found.")
    return None, None


# ── MAPS SCRAPER ─────────────────────────────────────────────────────────────

async def scrape_google_maps_reviews(place_query: str, user_id: str, max_pages: int = 10) -> dict:
    product_id = str(uuid.uuid4())
    products_collection.insert_one({
        'product_id': product_id,
        'platform': 'google_maps',
        'query': place_query,
        'user_id': user_id,
        'scraped_at': datetime.utcnow()
    })

    reviews = []

    async with httpx.AsyncClient(timeout=30) as client:

        # Step 1: place name → place_id
        print(f"Step 1: Finding place_id for '{place_query}'...")
        place_id, place = await _find_place_id(client, place_query)

        if not place_id:
            return {'success': False, 'product_id': product_id, 'reviews_count': 0,
                    'message': f'No place found for: {place_query}'}

        place_name    = place.get('title', place_query)
        overall_rating = place.get('rating')
        total_reviews  = place.get('reviews')
        address        = place.get('address', '')

        print(f"  → Found: {place_name} | place_id: {place_id} | Rating: {overall_rating} | Reviews: {total_reviews}")

        products_collection.update_one(
            {'product_id': product_id},
            {'$set': {
                'place_name': place_name,
                'place_id': place_id,
                'overall_rating': overall_rating,
                'total_reviews': total_reviews,
                'address': address,
                'url': f"https://www.google.com/maps/place/?q=place_id:{place_id}",
            }}
        )

        # Step 2: fetch reviews page by page
        next_page_token = None
        page_num = 0

        while page_num < max_pages:
            print(f"Step 2: Scraping reviews page {page_num + 1}...")

            params = {
                'engine': 'google_maps_reviews',
                'place_id': place_id,
                'api_key': SERPAPI_KEY,
                'hl': 'en',
                'sort_by': 'newestFirst',
            }
            if next_page_token:
                params['next_page_token'] = next_page_token

            try:
                resp = await client.get('https://serpapi.com/search', params=params)
                data = resp.json()
            except Exception as e:
                print(f"  → Request failed: {e}")
                break

            if 'error' in data:
                print(f"  → SerpApi error: {data['error']}")
                break

            page_reviews = data.get('reviews', [])
            print(f"  → Found {len(page_reviews)} reviews on page {page_num + 1}")

            if not page_reviews:
                print("  → No reviews returned, stopping.")
                break

            reviews.extend([{
                'review_id': str(uuid.uuid4()),
                'platform': 'google_maps',
                'product_id': product_id,
                'product_query': place_query,
                'place_name': place_name,
                'reviewer_name': r.get('user', {}).get('name', 'Anonymous'),
                'reviewer_reviews_count': r.get('user', {}).get('reviews', 0),
                'rating': r.get('rating', 0),
                'comment': r.get('snippet', ''),
                'date': r.get('date', ''),
                'likes': r.get('likes', 0),
                'verified': False,
                'user_id': user_id,
                'created_at': datetime.utcnow()
            } for r in page_reviews if r.get('snippet')])

            next_page_token = data.get('serpapi_pagination', {}).get('next_page_token')
            if not next_page_token:
                print("  → No more pages.")
                break

            page_num += 1

    if reviews:
        reviews_collection.insert_many(reviews)

    print(f"Done. Saved {len(reviews)} Google Maps reviews from {page_num + 1} page(s).")
    return {
        'success': True,
        'product_id': product_id,
        'reviews_count': len(reviews),
        'message': f'Scraped {len(reviews)} Google Maps reviews for {place_name}'
    }


# ── PRODUCT SCRAPER ──────────────────────────────────────────────────────────

async def scrape_google_product_reviews(product_query: str, user_id: str, max_pages: int = 10) -> dict:
    product_id = str(uuid.uuid4())
    products_collection.insert_one({
        'product_id': product_id,
        'platform': 'google_shopping',
        'query': product_query,
        'user_id': user_id,
        'scraped_at': datetime.utcnow()
    })

    reviews = []

    async with httpx.AsyncClient(timeout=30) as client:

        # Step 1: product name → Google Shopping product_id
        print(f"Step 1: Finding Google Shopping product_id for '{product_query}'...")
        google_product_id, product_title = await _find_google_product_id(client, product_query)

        if not google_product_id:
            return {'success': False, 'product_id': product_id, 'reviews_count': 0,
                    'message': f'No Google Shopping product found for: {product_query}'}

        products_collection.update_one(
            {'product_id': product_id},
            {'$set': {'google_product_id': google_product_id, 'product_title': product_title}}
        )

        # Step 2: fetch reviews page by page
        next_page_token = None
        page_num = 0

        while page_num < max_pages:
            print(f"Step 2: Scraping Google Shopping reviews page {page_num + 1}...")

            params = {
                'engine': 'google_immersive_product',
                'q': product_query,
                'product_id': google_product_id,
                'reviews': 'true',
                'api_key': SERPAPI_KEY,
                'hl': 'en',
                'gl': 'my',
            }
            if next_page_token:
                params['next_page_token'] = next_page_token

            try:
                resp = await client.get('https://serpapi.com/search', params=params)
                data = resp.json()
            except Exception as e:
                print(f"  → Request failed: {e}")
                break

            if 'error' in data:
                print(f"  → SerpApi error: {data['error']}")
                break

            if page_num == 0:
                product_results  = data.get('product_results', {})
                reviews_summary  = data.get('reviews_results', {}).get('user_reviews', {})
                products_collection.update_one(
                    {'product_id': product_id},
                    {'$set': {
                        'product_title':    product_results.get('title', product_title),
                        'overall_rating':   product_results.get('rating'),
                        'total_reviews':    product_results.get('reviews'),
                        'rating_breakdown': reviews_summary.get('ratings', []),
                    }}
                )
                print(f"  → Product: {product_results.get('title', product_title)} "
                      f"| Rating: {product_results.get('rating')} "
                      f"| Total: {product_results.get('reviews')} reviews")

            page_reviews = (
                data.get('reviews_results', {})
                    .get('user_reviews', {})
                    .get('review', [])
            )
            print(f"  → Found {len(page_reviews)} reviews on page {page_num + 1}")

            if not page_reviews:
                print("  → No reviews returned, stopping.")
                break

            reviews.extend([{
                'review_id': str(uuid.uuid4()),
                'platform': 'google_shopping',
                'product_id': product_id,
                'product_query': product_query,
                'reviewer_name': r.get('user', 'Anonymous'),
                'rating': r.get('rating', 0),
                'title': r.get('title', ''),
                'comment': r.get('snippet', ''),
                'date': r.get('date', ''),
                'source': r.get('source', ''),
                'verified': False,
                'user_id': user_id,
                'created_at': datetime.utcnow()
            } for r in page_reviews if r.get('snippet')])

            next_page_token = data.get('serpapi_pagination', {}).get('next_page_token')
            if not next_page_token:
                print("  → No more pages.")
                break

            page_num += 1

    if reviews:
        reviews_collection.insert_many(reviews)

    print(f"Done. Saved {len(reviews)} Google Shopping reviews from {page_num + 1} page(s).")
    return {
        'success': True,
        'product_id': product_id,
        'reviews_count': len(reviews),
        'message': f'Scraped {len(reviews)} Google Shopping reviews for {product_title}'
    }


# ── UNIFIED ENTRY POINT (called by your API route) ───────────────────────────

async def scrape_google(query: str, user_id: str, google_type: str = 'product', max_pages: int = 10) -> dict:
    """
    Unified entry point for all Google scraping.

    google_type:
        'maps'    → scrapes Google Maps reviews for a place/business
        'product' → scrapes Google Shopping reviews for a product
    """
    if google_type == 'maps':
        return await scrape_google_maps_reviews(query, user_id, max_pages)
    elif google_type == 'product':
        return await scrape_google_product_reviews(query, user_id, max_pages)
    else:
        return {'success': False, 'reviews_count': 0,
                'message': f'Unknown google_type: {google_type}. Use "maps" or "product".'}


if __name__ == "__main__":
    import asyncio
    # Test maps
    asyncio.run(scrape_google("Apple Store Kuala Lumpur", "test", google_type="maps"))
    # Test product
    # asyncio.run(scrape_google("iPhone 15", "test", google_type="product"))
