# app/scrapers/tripadvisor_scraper.py
from app.database import reviews_collection, products_collection
from datetime import datetime
import uuid
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

SERPAPI_KEY = os.getenv("SERPAPI_KEY")
TA_PAGE_SIZE = 20   # SerpApi TripAdvisor max reviews per page


async def _find_tripadvisor_place_id(client: httpx.AsyncClient, query: str) -> tuple[int | None, dict]:
    """Step 1: Search TripAdvisor to resolve place name → location_id."""
    print(f"  → Searching TripAdvisor for: '{query}'")
    resp = await client.get('https://serpapi.com/search', params={
        'engine':  'tripadvisor',
        'q':       query,
        'api_key': SERPAPI_KEY,
    })
    data = resp.json()

    if 'error' in data:
        print(f"  → SerpApi error: {data['error']}")
        return None, {}

    places = data.get('places', [])
    if not places:
        print("  → No TripAdvisor location found.")
        return None, {}

    first = places[0]
    location_id = first.get('place_id')

    if not location_id:
        print("  → No place_id found in results.")
        return None, {}

    print(f"  → Found: {first.get('title')} | location_id: {location_id}")
    return location_id, first

async def scrape_tripadvisor_reviews(query: str, user_id: str, max_pages: int = 10) -> dict:
    """
    Scrape TripAdvisor reviews for a place (hotel, restaurant, attraction).

    Args:
        query:     Place name (e.g. "Petronas Twin Towers", "Four Seasons KL")
        user_id:   Current user's ID
        max_pages: Max review pages to scrape (20 reviews per page)
    """
    product_id = str(uuid.uuid4())
    products_collection.insert_one({
        'product_id': product_id,
        'platform':   'tripadvisor',
        'query':      query,
        'user_id':    user_id,
        'scraped_at': datetime.utcnow()
    })

    reviews = []

    async with httpx.AsyncClient(timeout=30) as client:

        # ── STEP 1: Resolve place name → TripAdvisor location_id ────────────
        print(f"Step 1: Finding TripAdvisor location_id for '{query}'...")
        location_id, place_info = await _find_tripadvisor_place_id(client, query)

        if not location_id:
            return {
                'success':       False,
                'product_id':    product_id,
                'reviews_count': 0,
                'message':       f'No TripAdvisor location found for: {query}'
            }

        place_name     = place_info.get('title', query)
        overall_rating = place_info.get('rating')
        total_reviews  = place_info.get('reviews')
        place_url      = place_info.get('link', '')

        products_collection.update_one(
            {'product_id': product_id},
            {'$set': {
                'place_name':     place_name,
                'location_id':    location_id,
                'overall_rating': overall_rating,
                'total_reviews':  total_reviews,
                'url':            place_url,
            }}
        )

        # ── STEP 2: Fetch reviews page by page using offset pagination ───────
        page_num = 0

        while page_num < max_pages:
            offset = page_num * TA_PAGE_SIZE
            print(f"Step 2: Scraping reviews page {page_num + 1} (offset {offset})...")

            try:
                resp = await client.get('https://serpapi.com/search', params={
                    'engine':   'tripadvisor_reviews',
                    'place_id': location_id,
                    'api_key':  SERPAPI_KEY,
                    'language': 'en',
                    'sort':     'date_desc',   # newest first
                    'start':    offset,
                    'limit':    TA_PAGE_SIZE,  # max 20
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
                'review_id':       str(uuid.uuid4()),
                'platform':        'tripadvisor',
                'product_id':      product_id,
                'product_query':   query,
                'place_name':      place_name,
                'reviewer_name':   r.get('author', {}).get('display_name', 'Anonymous'),
                'reviewer_username': r.get('author', {}).get('username', ''),
                'reviewer_contributions': r.get('author', {}).get('contributions', 0),
                'rating':          r.get('rating', 0),
                'title':           r.get('title', ''),
                'comment':         r.get('snippet', ''),
                'date':            r.get('date', ''),
                'trip_type':       r.get('trip_info', {}).get('type', ''),   # COUPLES, FAMILY, SOLO etc.
                'trip_date':       r.get('trip_info', {}).get('date', ''),
                'language':        r.get('language', 'en'),
                'helpful_votes':   r.get('votes', 0),
                'verified':        False,
                'user_id':         user_id,
                'created_at':      datetime.utcnow()
            } for r in page_reviews if r.get('snippet')])

            # stop if this is the last page
            if len(page_reviews) < TA_PAGE_SIZE:
                print("  → Last page reached.")
                break

            if not data.get('serpapi_pagination', {}).get('next'):
                print("  → No next page.")
                break

            page_num += 1

    if reviews:
        reviews_collection.insert_many(reviews)

    print(f"Done. Saved {len(reviews)} TripAdvisor reviews from {page_num + 1} page(s).")
    return {
        'success':       True,
        'product_id':    product_id,
        'reviews_count': len(reviews),
        'message':       f'Scraped {len(reviews)} TripAdvisor reviews for {place_name}'
    }


if __name__ == "__main__":
    import asyncio
    asyncio.run(scrape_tripadvisor_reviews("Petronas Twin Towers", "test"))
