from app.database import reviews_collection, products_collection
from datetime import datetime
import uuid
import httpx
import os
import asyncio
import json
from dotenv import load_dotenv

load_dotenv()

SERPAPI_KEY = os.getenv("SERPAPI_KEY")

async def _get_serp_data(client: httpx.AsyncClient, params: dict):
    """
    Send request to SerpApi and return JSON response.
    """

    params["api_key"] = SERPAPI_KEY

    # Defaults
    params.setdefault("hl", "en")
    params.setdefault("gl", "us")

    try:
        response = await client.get(
            "https://serpapi.com/search.json",
            params=params
        )

        # Debug bad requests
        if response.status_code == 400:
            print("\n❌ SERPAPI 400 ERROR")
            print(response.text)

        response.raise_for_status()

        return response.json()

    except Exception as e:
        print(f"\n❌ Request Failed: {str(e)}")
        return {
            "error": str(e)
        }

async def scrape_google_maps_reviews(
    query: str,
    user_id: str,
    max_pages: int = 10
) -> dict:
    """
    Scrape Google Maps reviews using SerpApi.
    """

    internal_product_id = str(uuid.uuid4())

    async with httpx.AsyncClient(timeout=30) as client:

        search_params = {
            "engine": "google_maps",
            "q": query,
            "type": "search"
        }

        data = await _get_serp_data(client, search_params)

        if "error" in data:
            return {
                "success": False,
                "message": data["error"]
            }

        place = None

        # Sometimes place_results exists
        if data.get("place_results"):
            place = data["place_results"]

        # Sometimes local_results exists
        elif data.get("local_results"):
            place = data["local_results"][0]

        if not place:
            return {
                "success": False,
                "message": f"No Google Maps results found for '{query}'"
            }

        data_id = (
            place.get("data_id")
            or place.get("place_id")
            or place.get("id")
        )

        if not data_id:
            print("\n❌ PLACE RESPONSE:")
            print(json.dumps(place, indent=2))

            return {
                "success": False,
                "message": "Could not find data_id/place_id"
            }

        product_name = (
            place.get("title")
            or place.get("name")
            or query
        )

        print(f"\n✅ FOUND PLACE")
        print(f"Name: {product_name}")
        print(f"Data ID: {data_id}")

        reviews = []
        next_page_token = None

        for page in range(max_pages):

            print(f"\n📄 FETCHING PAGE {page + 1}")

            review_params = {
                "engine": "google_maps_reviews",
                "data_id": data_id,
                "sort_by": "newestFirst"
            }

            if next_page_token:
                review_params["next_page_token"] = next_page_token

            review_data = await _get_serp_data(client, review_params)

            # DEBUG FAILED RESPONSE
            if "error" in review_data:
                print("\n❌ REVIEW API ERROR")
                print(json.dumps(review_data, indent=2))
                break

            # print(json.dumps(review_data, indent=2))

            page_reviews = review_data.get("reviews", [])

            if not page_reviews:
                print("\n⚠️ No reviews found on this page")

                # Sometimes Google blocks reviews
                if "search_metadata" in review_data:
                    print(json.dumps(review_data["search_metadata"], indent=2))

                break

            print(f"✅ Found {len(page_reviews)} reviews")

            for review in page_reviews:

                review_doc = {
                    "review_id": str(uuid.uuid4()),
                    "platform": "google_maps",
                    "product_id": internal_product_id,

                    "reviewer_name": (
                        review.get("user", {}).get("name")
                        or review.get("author_name")
                        or "Anonymous"
                    ),

                    "rating": (
                        review.get("rating")
                        or 0
                    ),

                    "comment": (
                        review.get("snippet")
                        or review.get("text")
                        or ""
                    ),

                    "date": (
                        review.get("date")
                        or review.get("relative_date")
                        or ""
                    ),

                    "user_id": user_id,
                    "created_at": datetime.utcnow()
                }

                reviews.append(review_doc)

            next_page_token = (
                review_data.get("serpapi_pagination", {})
                .get("next_page_token")
            )

            if not next_page_token:
                print("\n✅ No more pages")
                break

            await asyncio.sleep(2)

        if reviews:

            reviews_collection.insert_many(reviews)

            print(f"\n✅ Inserted {len(reviews)} reviews into MongoDB")

        else:
            print("\n⚠️ No reviews inserted")

        products_collection.update_one(
            {
                "product_id": internal_product_id
            },
            {
                "$setOnInsert": {
                    "product_id": internal_product_id,
                    "name": product_name,
                    "platform": "google_maps",
                    "user_id": user_id,
                    "created_at": datetime.utcnow()
                }
            },
            upsert=True
        )

        return {
            "success": True,
            "product_id": internal_product_id,
            "product_name": product_name,
            "reviews_count": len(reviews)
        }

async def scrape_google(
    query: str,
    user_id: str,
    category: str = "location",
    max_pages: int = 10
):
    """
    Unified Google scraper.
    """

    if category == "location":
        return await scrape_google_maps_reviews(
            query=query,
            user_id=user_id,
            max_pages=max_pages
        )

    return {
        "success": False,
        "message": 'Invalid category. Only "location" is supported.'
    }
