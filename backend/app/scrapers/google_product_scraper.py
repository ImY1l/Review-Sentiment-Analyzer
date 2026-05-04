from app.database import reviews_collection, products_collection
from datetime import datetime
import uuid
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

SERPAPI_KEY = os.getenv("SERPAPI_KEY")


async def _find_product_id(client: httpx.AsyncClient, product_query: str) -> tuple[str | None, str | None]:
    """Step 1: Search Google Shopping to get the product_id for a query."""
    print(f"  → Searching Google Shopping for: {product_query}")
    response = await client.get('https://serpapi.com/search', params={
        'engine': 'google_shopping',
        'q': product_query,
        'api_key': SERPAPI_KEY,
        'hl': 'en',
        'gl': 'my',  # Malaysia — change to 'us' if needed
    })
    data = response.json()

    if 'error' in data:
        print(f"  → SerpApi error: {data['error']}")
        return None, None

    results = data.get('shopping_results', [])
    if not results:
        print("  → No shopping results found.")
        return None, None

    # Pick first result that has a product_id
    for r in results[:5]:
        product_id_val = r.get('product_id')
        title = r.get('title', '')
        if product_id_val:
            print(f"  → Found product: {title} (id: {product_id_val})")
            return product_id_val, title

    print("  → No product_id found in results.")
    return None, None


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

        # Step 1: Find the Google Shopping product_id from the query
        google_product_id, product_title = await _find_product_id(client, product_query)
        if not google_product_id:
            return {
                'success': False,
                'product_id': product_id,
                'reviews_count': 0,
                'message': f'No Google Shopping product found for: {product_query}'
            }

        products_collection.update_one(
            {'product_id': product_id},
            {'$set': {'google_product_id': google_product_id, 'product_title': product_title}}
        )

        # Step 2: Fetch reviews page by page
        next_page_token = None
        page_num = 0

        while page_num < max_pages:
            print(f"Scraping Google Shopping reviews page {page_num + 1}...")

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
                response = await client.get('https://serpapi.com/search', params=params)
                data = response.json()
            except Exception as e:
                print(f"  → Request failed: {e}")
                break

            if 'error' in data:
                print(f"  → SerpApi error: {data['error']}")
                break

            # Save product info on first page
            if page_num == 0:
                product_results = data.get('product_results', {})
                reviews_summary = data.get('reviews_results', {}).get('user_reviews', {})
                products_collection.update_one(
                    {'product_id': product_id},
                    {'$set': {
                        'product_title': product_results.get('title', product_title),
                        'overall_rating': product_results.get('rating'),
                        'total_reviews': product_results.get('reviews'),
                        'rating_breakdown': reviews_summary.get('ratings', []),
                    }}
                )
                print(f"  → Product: {product_results.get('title', product_title)} "
                      f"| Rating: {product_results.get('rating')} "
                      f"| Total: {product_results.get('reviews')} reviews")

            # Extract reviews
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
                'source': r.get('source', ''),   # e.g. "Best Buy", "Amazon" — Google aggregates from multiple sites
                'verified': False,
                'user_id': user_id,
                'created_at': datetime.utcnow()
            } for r in page_reviews if r.get('snippet')])

            # Pagination
            pagination = data.get('serpapi_pagination', {})
            next_page_token = pagination.get('next_page_token')

            if not next_page_token:
                print("  → No more pages available.")
                break

            page_num += 1

    if reviews:
        reviews_collection.insert_many(reviews)

    print(f"Done. Saved {len(reviews)} Google Shopping reviews from {page_num + 1} page(s).")
    return {
        'success': True,
        'product_id': product_id,
        'reviews_count': len(reviews),
        'message': f'Scraped {len(reviews)} Google Shopping reviews across {page_num + 1} pages'
    }


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
    next_page_token = None
    page_num = 0

    async with httpx.AsyncClient(timeout=30) as client:

        while page_num < max_pages:
            print(f"Scraping Google Maps reviews page {page_num + 1}...")

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

            if 'error' in data:
                print(f"  → SerpApi error: {data['error']}")
                break

            if page_num == 0:
                place_info = data.get('place_info', {})
                products_collection.update_one(
                    {'product_id': product_id},
                    {'$set': {
                        'url': f"https://www.google.com/maps/search/{place_query.replace(' ', '+')}",
                        'place_name': place_info.get('title', place_query),
                        'overall_rating': place_info.get('rating'),
                        'total_reviews': place_info.get('reviews'),
                        'address': place_info.get('address', ''),
                    }}
                )
                print(f"  → Place: {place_info.get('title', place_query)} "
                      f"| Rating: {place_info.get('rating')} "
                      f"| Total: {place_info.get('reviews')} reviews")

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

            pagination = data.get('serpapi_pagination', {})
            next_page_token = pagination.get('next_page_token')

            if not next_page_token:
                print("  → No more pages available.")
                break

            page_num += 1

    if reviews:
        reviews_collection.insert_many(reviews)

    print(f"Done. Saved {len(reviews)} Google Maps reviews from {page_num + 1} page(s).")
    return {
        'success': True,
        'product_id': product_id,
        'reviews_count': len(reviews),
        'message': f'Scraped {len(reviews)} Google Maps reviews across {page_num + 1} pages'
    }


if __name__ == "__main__":
    import asyncio
    # Test product reviews
    asyncio.run(scrape_google_product_reviews("iPhone 15", "test"))
    # Test maps reviews
    # asyncio.run(scrape_google_maps_reviews("Apple Store Kuala Lumpur", "test"))
