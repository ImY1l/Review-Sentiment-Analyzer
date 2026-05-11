# app/scrapers/shopee_scraper.py
from playwright.async_api import async_playwright
from app.database import reviews_collection, products_collection
from datetime import datetime
import asyncio
import uuid

async def _dismiss_popups(page):
    """Dismiss language selector and/or ad popup — in any order, within 6 seconds."""
    print("  → Checking for popups...")
    deadline = 6  # seconds total to watch for popups
    dismissed = []

    for _ in range(deadline * 2):  # check every 500ms
        await page.wait_for_timeout(500)

        # 1. Language selector — click "English" if visible
        if 'language' not in dismissed:
            try:
                lang_btn = page.locator('button:has-text("English")').first
                if await lang_btn.is_visible(timeout=300):
                    await lang_btn.click()
                    dismissed.append('language')
                    print("  → Dismissed language selector")
                    await page.wait_for_timeout(500)
                    continue
            except Exception:
                pass

        # 2. Ad popup — click the X close button if visible
        if 'ad' not in dismissed:
            try:
                close_btn = page.locator(
                    'button.shopee-popup__close-btn, '
                    '[class*="close"], '
                    'button[aria-label="close"], '
                    'svg[class*="close"]'
                ).first
                if await close_btn.is_visible(timeout=300):
                    await close_btn.click()
                    dismissed.append('ad')
                    print("  → Dismissed ad popup")
                    await page.wait_for_timeout(500)
                    continue
            except Exception:
                pass

        # Both dismissed — no need to keep waiting
        if len(dismissed) >= 2:
            break

    print(f"  → Popups handled: {dismissed if dismissed else 'none found'}")


async def scrape_shopee(product_query: str, user_id: str, max_pages: int = 10) -> dict:
    product_id = str(uuid.uuid4())
    products_collection.insert_one({
        'product_id': product_id,
        'platform':   'shopee',
        'query':      product_query,
        'user_id':    user_id,
        'scraped_at': datetime.utcnow()
    })

    reviews = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1366, 'height': 768},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = await context.new_page()

        try:
            # 1. Go to Shopee Malaysia
            print("Step 1: Going to Shopee...")
            await page.goto('https://shopee.com.my/', timeout=60000, wait_until='domcontentloaded')
            await page.wait_for_timeout(2000)

            # Handle any popups on homepage
            await _dismiss_popups(page)

            # 2. Search product
            print("Step 2: Searching product...")
            search_box = page.locator(
                'input[placeholder*="search" i], '
                'input[class*="search"], '
                'input[type="search"]'
            ).first
            await search_box.fill(product_query)
            await search_box.press('Enter')
            await page.wait_for_timeout(4000)

            # Dismiss any popup that appeared after search
            await _dismiss_popups(page)

            # 3. Open first product
            print("Step 3: Opening first product...")
            product_url = None

            # Shopee product links contain /i. or shopee.com.my/<shop>/<product>-i.
            product_elements = await page.locator(
                'a[href*="-i."], a[href*="/product/"]'
            ).all()

            for link in product_elements[:5]:
                href = await link.get_attribute('href')
                if href and ('-i.' in href or '/product/' in href):
                    product_url = href if href.startswith('http') else 'https://shopee.com.my' + href
                    break

            if not product_url:
                await browser.close()
                return {'success': False, 'product_id': product_id, 'reviews_count': 0,
                        'message': 'No product link found'}

            print(f"  → Product URL: {product_url}")
            products_collection.update_one(
                {'product_id': product_id},
                {'$set': {'url': product_url}}
            )

            await page.goto(product_url, wait_until='domcontentloaded', timeout=60000)
            await page.wait_for_timeout(3000)

            # Dismiss any popup on product page
            await _dismiss_popups(page)

            # 4. Scroll down to reviews section
            print("Step 4: Scrolling to reviews section...")
            await page.evaluate("""
                (() => {
                    const el =
                        document.querySelector('[class*="product-ratings"]') ||
                        document.querySelector('[class*="ratings"]') ||
                        document.querySelector('[class*="review"]');
                    if (el) el.scrollIntoView({ behavior: 'instant', block: 'start' });
                    else window.scrollTo(0, document.body.scrollHeight * 0.7);
                })();
            """)
            await page.wait_for_timeout(2000)

            # Scroll again to trigger lazy load
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(2000)
            await page.evaluate("""
                (() => {
                    const el =
                        document.querySelector('[class*="product-ratings"]') ||
                        document.querySelector('[class*="ratings"]') ||
                        document.querySelector('[class*="review"]');
                    if (el) el.scrollIntoView({ behavior: 'instant', block: 'start' });
                })();
            """)
            await page.wait_for_timeout(2000)

            # 5. Paginate through review sub-pages
            page_num = 1
            while page_num <= max_pages:
                print(f"Scraping review page {page_num}...")

                # Keep review section in view
                await page.evaluate("""
                    (() => {
                        const el =
                            document.querySelector('[class*="product-ratings"]') ||
                            document.querySelector('[class*="ratings"]') ||
                            document.querySelector('[class*="review"]');
                        if (el) el.scrollIntoView({ behavior: 'instant', block: 'start' });
                    })();
                """)
                await page.wait_for_timeout(1500)

                # Extract reviews
                js_reviews = await page.evaluate("""
                    (() => {
                        // Shopee review items
                        const items = Array.from(document.querySelectorAll(
                            '[class*="shopee-product-rating"], ' +
                            '[class*="product-rating__item"], ' +
                            '[class*="review-item"]'
                        ));

                        return items.map(function(el) {

                            // --- REVIEWER ---
                            const reviewer =
                                el.querySelector('[class*="author"], [class*="buyer"], [class*="name"]')
                                  ?.textContent?.trim() || 'Anonymous';

                            // --- DATE ---
                            const date =
                                el.querySelector('[class*="time"], [class*="date"]')
                                  ?.textContent?.trim() || '';

                            // --- RATING: count filled stars ---
                            const filledStars = el.querySelectorAll(
                                'svg[class*="star--active"], '   +
                                '[class*="star--on"], '          +
                                '[class*="icon-star-active"]'
                            ).length;
                            // fallback: aria-label e.g. "4 stars"
                            let rating = filledStars;
                            if (rating === 0) {
                                const ariaEl = el.querySelector('[aria-label*="star"]');
                                if (ariaEl) {
                                    const m = (ariaEl.getAttribute('aria-label') || '').match(/(\\d+)/);
                                    if (m) rating = parseInt(m[1]);
                                }
                            }

                            // --- FULL COMMENT ---
                            const comment =
                                el.querySelector('[class*="content"], [class*="text"], [class*="comment"]')
                                  ?.textContent?.trim() || '';

                            // --- VARIANT (Color, Size, etc.) ---
                            const variant =
                                el.querySelector('[class*="variant"], [class*="sku"]')
                                  ?.textContent?.trim() || '';

                            // --- HELPFUL / LIKES ---
                            const likes = parseInt(
                                el.querySelector('[class*="like"], [class*="helpful"]')
                                  ?.textContent?.trim() || '0'
                            ) || 0;

                            return { reviewer, rating, comment, date, variant, likes };
                        }).filter(function(r) { return r.comment.length > 0; });
                    })();
                """)

                print(f"  → Found {len(js_reviews)} reviews on page {page_num}")

                if len(js_reviews) > 0:
                    reviews.extend([{
                        'review_id':     str(uuid.uuid4()),
                        'platform':      'shopee',
                        'product_id':    product_id,
                        'product_query': product_query,
                        'reviewer_name': r['reviewer'],
                        'rating':        r['rating'],
                        'comment':       r['comment'],
                        'variant':       r['variant'],
                        'date':          r['date'],
                        'likes':         r['likes'],
                        'user_id':       user_id,
                        'created_at':    datetime.utcnow()
                    } for r in js_reviews])

                if page_num >= max_pages:
                    break

                # ── PAGINATION: click the next page number button ────────────
                # Shopee pagination looks like: < 1 2 3 4 5 ... >
                # The active page is highlighted in red
                next_page_num = page_num + 1
                clicked = await page.evaluate(
                    """
                    (nextPage) => {
                        // Find the ratings/review section root
                        const root =
                            document.querySelector('[class*="product-ratings"]') ||
                            document.querySelector('[class*="ratings"]')         ||
                            document.querySelector('[class*="review"]')          ||
                            document;

                        // Find all visible buttons/spans with the exact next page number
                        const targetText = String(nextPage);
                        const candidates = Array.from(root.querySelectorAll(
                            'button, a, li, span, div'
                        ));

                        const btn = candidates.find(function(el) {
                            const text = (el.textContent || '').trim();
                            if (text !== targetText) return false;
                            const rect = el.getBoundingClientRect();
                            if (rect.width === 0 || rect.height === 0) return false;
                            // Must be near the bottom of the page (pagination area)
                            if (rect.top < window.innerHeight * 0.4) return false;
                            return true;
                        });

                        if (!btn) return false;
                        btn.scrollIntoView({ behavior: 'instant', block: 'center' });
                        btn.click();
                        return true;
                    }
                    """,
                    next_page_num
                )

                if not clicked:
                    print(f"  → No pagination button for page {next_page_num}, stopping.")
                    break

                await page.wait_for_timeout(3000)
                page_num += 1

            # Save to DB
            if reviews:
                reviews_collection.insert_many(reviews)

            print(f"Done. Saved {len(reviews)} Shopee reviews from {page_num} page(s).")
            await browser.close()
            return {
                'success':       True,
                'product_id':    product_id,
                'reviews_count': len(reviews),
                'message':       f'Scraped {len(reviews)} Shopee reviews across {page_num} pages'
            }

        except Exception as e:
            print(f"Error: {str(e)}")
            await browser.close()
            return {'success': False, 'product_id': product_id,
                    'reviews_count': 0, 'message': str(e)}


if __name__ == "__main__":
    asyncio.run(scrape_shopee("iPhone 15", "test"))
