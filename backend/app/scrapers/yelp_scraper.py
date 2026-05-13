# app/scrapers/yelp_scraper.py
from app.database import reviews_collection, products_collection
from datetime import datetime
import uuid
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

SERPAPI_KEY = os.getenv("SERPAPI_KEY")
YELP_PAGE_SIZE = 49


def _is_relevant_result(result: dict, query: str, location: str) -> bool:
    """
    Validate that the Yelp result is actually relevant to the query.
    Rejects results that are geographically wrong or name-mismatched.
    """
    title       = (result.get('title') or '').lower()
    result_addr = (result.get('neighborhoods') or result.get('location', {}).get('display_address', [''])[0] or '').lower()
    query_lower = query.lower()
    loc_lower   = location.lower()

    # 1. Name must have at least one meaningful word in common
    query_words = [w for w in query_lower.split() if len(w) > 2]
    name_match  = any(w in title for w in query_words)

    # 2. Location must roughly match — extract country/city from location string
    #    e.g. "Kuala Lumpur, Malaysia" → check for "malaysia" or "kuala lumpur"
    loc_parts     = [p.strip().lower() for p in loc_lower.replace(',', ' ').split()]
    location_match = any(part in result_addr for part in loc_parts if len(part) > 2)

    print(f"  → Validating: '{result.get('title')}' | addr: '{result_addr}'")
    print(f"     name_match={name_match} | location_match={location_match}")

    return name_match and location_match


async def _find_yelp_place_id(
    client: httpx.AsyncClient,
    query: str,
    location: str
) -> tuple[str | None, dict]:
    print(f"  → Searching Yelp for: '{query}' in '{location}'")
    resp = await client.get('https://serpapi.com/search', params={
        'engine':    'yelp',
        'find_desc': query,
        'find_loc':  location,
        'api_key':   SERPAPI_KEY,
        'sortby':    'review_count',
    })
    data = resp.json()

    if 'error' in data:
        print(f"  → SerpApi error: {data['error']}")
        return None, {}

    results = data.get('organic_results', [])
    if not results:
        print("  → No Yelp results found.")
        return None, {}

    # Pick first result that has a place_id AND passes relevance validation
    for r in results[:5]:
        place_ids = r.get('place_ids', [])
        if not place_ids:
            continue
        if _is_relevant_result(r, query, location):
            print(f"  → Accepted: {r.get('title')} | "
                  f"Rating: {r.get('rating')} | Reviews: {r.get('reviews')}")
            return place_ids[0], r
        else:
            print(f"  → Rejected (irrelevant): {r.get('title')}")

    print("  → No relevant Yelp business found.")
    return None, {}


async def scrape_yelp_reviews(
    query: str,
    user_id: str,
    location: str = 'Malaysia',
    max_pages: int = 10
) -> dict:
    product_id = str(uuid.uuid4())
    products_collection.insert_one({
        'product_id': product_id,
        'platform':   'yelp',
        'name':       query,
        'location':   location,
        'user_id':    user_id,
        'scraped_at': datetime.utcnow()
    })

    reviews = []

    async with httpx.AsyncClient(timeout=30) as client:

        # ── STEP 1: Resolve business name → Yelp place_id ───────────────────
        print(f"Step 1: Finding Yelp place_id for '{query}' in '{location}'...")
        place_id, place_info = await _find_yelp_place_id(client, query, location)

        if not place_id:
            return {
                'success':       False,
                'product_id':    product_id,
                'reviews_count': 0,
                'message':       f'No relevant Yelp business found for "{query}" in {location}. '
                                 f'Note: Yelp coverage outside the US is limited.'
            }

        place_name     = place_info.get('title', query)
        overall_rating = place_info.get('rating')
        total_reviews  = place_info.get('reviews')
        address        = place_info.get('neighborhoods', '')
        place_url      = place_info.get('link', '')

        products_collection.update_one(
            {'product_id': product_id},
            {'$set': {
                'name':           place_name,
                'place_id':       place_id,
                'overall_rating': overall_rating,
                'total_reviews':  total_reviews,
                'address':        address,
                'url':            place_url,
            }}
        )

        # ── STEP 2: Fetch reviews page by page ──────────────────────────────
        page_num = 0
        while page_num < max_pages:
            offset = page_num * YELP_PAGE_SIZE
            print(f"Step 2: Scraping reviews page {page_num + 1} (offset {offset})...")

            try:
                resp = await client.get('https://serpapi.com/search', params={
                    'engine':   'yelp_reviews',
                    'place_id': place_id,
                    'api_key':  SERPAPI_KEY,
                    'sortby':   'date_desc',
                    'start':    offset,
                    'num':      YELP_PAGE_SIZE,
                })
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
                'review_id':              str(uuid.uuid4()),
                'platform':               'yelp',
                'product_id':             product_id,
                'product_query':          query,
                'place_name':             place_name,
                'reviewer_name':          r.get('user', {}).get('name', 'Anonymous'),
                'reviewer_location':      r.get('user', {}).get('address', ''),
                'reviewer_reviews_count': r.get('user', {}).get('reviews', 0),
                'reviewer_friends_count': r.get('user', {}).get('friends', 0),
                'rating':                 r.get('rating', 0),
                'comment':                r.get('comment', {}).get('text', ''),
                'date':                   r.get('date', ''),
                'verified':               False,
                'user_id':                user_id,
                'created_at':             datetime.utcnow()
            } for r in page_reviews if r.get('comment', {}).get('text')])

            if len(page_reviews) < YELP_PAGE_SIZE:
                print("  → Last page reached.")
                break

            if not data.get('serpapi_pagination', {}).get('next'):
                print("  → No next page.")
                break

            page_num += 1

    if reviews:
        reviews_collection.insert_many(reviews)

    print(f"Done. Saved {len(reviews)} Yelp reviews from {page_num + 1} page(s).")
    return {
        'success':       True,
        'product_id':    product_id,
        'reviews_count': len(reviews),
        'message':       f'Scraped {len(reviews)} Yelp reviews for {place_name}'
    }


if __name__ == "__main__":
    import asyncio
    asyncio.run(scrape_yelp_reviews("Apple Store", "test", location="Kuala Lumpur, Malaysia"))
