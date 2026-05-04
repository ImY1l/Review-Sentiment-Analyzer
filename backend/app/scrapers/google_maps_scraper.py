from app.database import reviews_collection, products_collection
from datetime import datetime
import uuid
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

SERPAPI_KEY = os.getenv("SERPAPI_KEY")


async def scrape_google_reviews(place_query: str, user_id: str, max_pages: int = 10) -> dict:
    product_id = str(uuid.uuid4())
    products_collection.insert_one({
        'product_id': product_id,
        'platform': 'google',
        'query': place_query,
        'user_id': user_id,
        'scraped_at': datetime.utcnow()
    })

    reviews = []
    next_page_token = None
    page_num = 0

    async with httpx.AsyncClient(timeout=30) as client:

        while page_num < max_pages:
            print(f"Scraping Google reviews page {page_num + 1}...")

            # --- Build request params ---
            params = {
                'engine': 'google_maps_reviews',
                'q': place_query,
                'api_key': SERPAPI_KEY,
                'hl': 'en',
                'sort_by': 'newestFirst',
            }
            if next_page_token:
                params['next_page_token'] = next_page_token

            try:
                response = await client.get('https://serpapi.com/search', params=params)
                data = response.json()
            except Exception as e:
                print(f"  → Request failed: {e}")
                break

            # --- Check for API errors ---
            if 'error' in data:
                print(f"  → SerpApi error: {data['error']}")
                break

            # --- Save place info on first page ---
            if page_num == 0:
                place_info = data.get('place_info', {})
                place_url = f"https://www.google.com/maps/search/{place_query.replace(' ', '+')}"
                products_collection.update_one(
                    {'product_id': product_id},
                    {'$set': {
                        'url': place_url,
                        'place_name': place_info.get('title', place_query),
                        'overall_rating': place_info.get('rating', None),
                        'total_reviews': place_info.get('reviews', None),
                        'address': place_info.get('address', ''),
                    }}
                )
                print(f"  → Place: {place_info.get('title', place_query)} "
                      f"| Rating: {place_info.get('rating')} "
                      f"| Total reviews: {place_info.get('reviews')}")

            # --- Extract reviews ---
            page_reviews = data.get('reviews', [])
            print(f"  → Found {len(page_reviews)} reviews on page {page_num + 1}")

            if not page_reviews:
                print("  → No reviews returned, stopping.")
                break

            reviews.extend([{
                'review_id': str(uuid.uuid4()),
                'platform': 'google',
                'product_id': product_id,
                'product_query': place_query,
                'reviewer_name': r.get('user', {}).get('name', 'Anonymous'),
                'reviewer_reviews_count': r.get('user', {}).get('reviews', 0),
                'rating': r.get('rating', 0),
                'comment': r.get('snippet', ''),
                'date': r.get('date', ''),
                'likes': r.get('likes', 0),
                'verified': False,  # Google doesn't have verified purchase
                'user_id': user_id,
                'created_at': datetime.utcnow()
            } for r in page_reviews if r.get('snippet')])

            # --- Pagination ---
            pagination = data.get('serpapi_pagination', {})
            next_page_token = pagination.get('next_page_token')

            if not next_page_token:
                print("  → No more pages available.")
                break

            page_num += 1

    # --- Save to DB ---
    if reviews:
        reviews_collection.insert_many(reviews)

    print(f"Done. Saved {len(reviews)} Google reviews from {page_num + 1} page(s).")
    return {
        'success': True,
        'product_id': product_id,
        'reviews_count': len(reviews),
        'message': f'Scraped {len(reviews)} Google reviews across {page_num + 1} pages'
    }


if __name__ == "__main__":
    import asyncio
    asyncio.run(scrape_google_reviews("Apple Store Kuala Lumpur", "test"))
