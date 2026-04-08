from playwright.async_api import async_playwright
from app.database import reviews_collection, products_collection
from datetime import datetime
import asyncio
import uuid

async def scrape_lazada(product_query: str, user_id: str, max_pages: int = 10) -> dict:
    product_id = str(uuid.uuid4())
    product_doc = {
        'product_id': product_id,
        'platform': 'lazada',
        'query': product_query,
        'user_id': user_id,
        'scraped_at': datetime.utcnow()
    }
    products_collection.insert_one(product_doc)

    reviews = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1366, 'height': 768},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = await context.new_page()

        try:
            # 1. Go to Lazada
            print("Step 1: Going to Lazada...")
            await page.goto('https://www.lazada.com.my/', timeout=60000, wait_until='domcontentloaded')
            await page.wait_for_timeout(2000)

            # 2. Search product
            print("Step 2: Searching product...")
            await page.fill('#q', product_query)
            await page.press('#q', 'Enter')
            await page.wait_for_timeout(4000)

            # 3. Open first product
            print("Step 3: Opening first product...")
            product_url = None
            product_elements = await page.locator('a[href*="/products/"], a[href*=".html"]').all()
            for link in product_elements[:5]:
                href = await link.get_attribute('href')
                if href and ('.html' in href or '/products/' in href):
                    product_url = href if href.startswith('http') else 'https:' + href
                    break

            if not product_url:
                return {'success': False, 'reviews_count': 0, 'message': 'No product link found'}

            print(f"Product URL: {product_url}")
            products_collection.update_one({'product_id': product_id}, {'$set': {'url': product_url}})
            await page.goto(product_url, wait_until='networkidle', timeout=60000)
            await page.wait_for_timeout(3000)

            # 4. Scroll down to the review section
            print("Step 4: Scrolling to reviews section...")
            await page.evaluate("""
                (() => {
                    const el =
                        document.querySelector('#module_product_review') ||
                        document.querySelector('[id*="review"]');
                    if (el) el.scrollIntoView({ behavior: 'instant', block: 'start' });
                    else window.scrollTo(0, document.body.scrollHeight);
                })();
            """)
            await page.wait_for_timeout(3000)

            # 5. Paginate through review sub-pages
            page_num = 1
            while page_num <= max_pages:
                print(f"Scraping review page {page_num}...")

                # Scroll review section into view (if needed)
                await page.evaluate("""
                    (() => {
                        const el =
                            document.querySelector('#module_product_review') ||
                            document.querySelector('[id*="review"]');
                        if (el) el.scrollIntoView({ behavior: 'instant', block: 'start' });
                    })();
                """)
                await page.wait_for_timeout(2000)

                # Extract reviews using Lazada-specific selectors
                js_reviews = await page.evaluate("""
                    (() => {
                        const root = document.querySelector('#module_product_review') || document;
                        const items = Array.from(root.querySelectorAll('.item'));

                        return items.map(el => {

                            // --- REVIEWER ---
                            const reviewer = el.querySelector('.reviewer')?.textContent?.trim() || 'Anonymous';

                            // --- DATE ---
                            const date = el.querySelector('.time')?.textContent?.trim() || '';

                            // --- RATING: count filled (yellow) stars ---
                            // Each star is a .i-rate-star div containing an SVG with 2 paths.
                            // The second path is yellow (filled) or grey (empty).
                            // We count stars where the second path's fill is yellow.
                            const starDivs = Array.from(el.querySelectorAll('.i-rate-star'));
                            let rating = 0;
                            starDivs.forEach(function(starDiv) {
                                const paths = starDiv.querySelectorAll('path');
                                if (paths.length >= 2) {
                                    const fillStyle = paths[1].getAttribute('style') || '';
                                    if (fillStyle.includes('255, 200, 60')) rating += 1;
                                }
                            });

                            // --- VARIANT (Color, Storage, etc.) ---
                            const variant = el.querySelector('.item-content-main-content-skuInfo')
                                            ?.textContent?.trim() || '';

                            // --- FULL COMMENT: use the reviews div which excludes sku info ---
                            const comment = el.querySelector('.item-content-main-content-reviews')
                                            ?.textContent?.trim() || '';

                            return { reviewer, rating, comment, date, variant };
                        }).filter(function(r) { return r.comment.length > 0; });
                    })();
                """)

                print(f"  → Found {len(js_reviews)} reviews on page {page_num}")
                reviews.extend([{
                    'review_id': str(uuid.uuid4()),
                    'platform': 'lazada',
                    'product_id': product_id,
                    'product_query': product_query,
                    'reviewer_name': r['reviewer'],
                    'rating': r['rating'],
                    'comment': r['comment'],
                    'variant': r['variant'],
                    'date': r['date'],
                    'user_id': user_id,
                    'created_at': datetime.utcnow()
                } for r in js_reviews])

                if page_num >= max_pages:
                    break

                # We find the correct number inside the container and click it.
                next_page_num = page_num + 1
                clicked = await page.evaluate(
                    """
                    (nextPage) => {
                        // 1. Find the pagination container anchored inside the review module
                        //    It always contains text matching "Page X out of Y"
                        const allDivs = Array.from(document.querySelectorAll(
                            '#module_product_review *,' +
                            '[id*="review"] *,' +
                            '[class*="review"] *'
                        ));

                        // Find the pagination root: it's the element whose text
                        // contains "out of" (e.g. "Page 1 out of 73")
                        const pagerRoot = allDivs.find(el => {
                            const t = el.textContent || '';
                            return /page\\s*\\d+\\s*out\\s*of\\s*\\d+/i.test(t) && el.children.length > 0;
                        });

                        if (!pagerRoot) {
                            console.log('Pager root not found');
                            return false;
                        }

                        // 2. Inside pagerRoot, find a clickable element whose
                        //    trimmed text is exactly the next page number
                        const targetText = String(nextPage);
                        const buttons = Array.from(pagerRoot.querySelectorAll('button, a, span, li'));
                        const btn = buttons.find(el => {
                            const text = (el.textContent || '').trim();
                            if (text !== targetText) return false;
                            const rect = el.getBoundingClientRect();
                            return rect.width > 0 && rect.height > 0;
                        });

                        if (!btn) {
                            console.log('Next page button not found for page', nextPage);
                            return false;
                        }

                        btn.scrollIntoView({ behavior: 'instant', block: 'center' });
                        btn.click();
                        return true;
                    }
                    """,
                    next_page_num
                )

                if not clicked:
                    print(f"  → No pagination button found for page {next_page_num}, stopping.")
                    break

                # Wait for new reviews to load
                await page.wait_for_timeout(4000)
                page_num += 1

            # Save to DB
            if reviews:
                reviews_collection.insert_many(reviews)
            print(f"Done. Saved {len(reviews)} reviews from {page_num} pages.")

            await browser.close()
            return {
                'success': True,
                'reviews_count': len(reviews),
                'message': f'Scraped {len(reviews)} reviews across {page_num} pages'
            }

        except Exception as e:
            print(f"Error: {str(e)}")
            await browser.close()
            return {'success': False, 'reviews_count': 0, 'message': str(e)}


if __name__ == "__main__":
    asyncio.run(scrape_lazada("iphone 15", "test"))