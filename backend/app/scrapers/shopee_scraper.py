# app/scrapers/shopee_scraper.py

from playwright.async_api import async_playwright
from app.database import reviews_collection, products_collection
from datetime import datetime
import asyncio
import uuid


async def _wait(page, seconds: float = 2.0):
    await page.wait_for_timeout(int(seconds * 1000))


# ─────────────────────────────────────────────────────────────────────────────
# HANDLE LANGUAGE POPUP
# ─────────────────────────────────────────────────────────────────────────────
async def _handle_language_popup(page) -> bool:
    try:
        print("  → Waiting for language popup...")

        selectors = [
            'button:has-text("English")',
            'button:has-text("EN")',
            'button >> text=English',
            'text=English',
        ]

        for selector in selectors:
            try:
                btn = page.locator(selector).first

                await btn.wait_for(state='visible', timeout=5000)

                print(f"  → Found language button: {selector}")

                await _wait(page, 1.5)

                await btn.click(force=True)

                await _wait(page, 3)

                print("  → English selected.")
                return True

            except Exception:
                continue

        print("  → No language popup found.")
        return False

    except Exception as e:
        print(f"  → Language popup error: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# HANDLE AD POPUP
# ─────────────────────────────────────────────────────────────────────────────
async def _handle_ad_popup(page) -> bool:
    try:
        print("  → Looking for ad popup...")

        selectors = [
            'button[aria-label="Close"]',
            'svg[class*="close"]',
            '[class*="close"]',
            '[class*="dismiss"]',
            'button.shopee-popup__close-btn',
            '[class*="popup"] button',
        ]

        for selector in selectors:
            try:
                btn = page.locator(selector).first

                if await btn.is_visible(timeout=3000):

                    print(f"  → Closing popup using: {selector}")

                    await _wait(page, 1)

                    await btn.click(force=True)

                    await _wait(page, 2)

                    print("  → Popup closed.")
                    return True

            except Exception:
                continue

        print("  → No ad popup found.")
        return False

    except Exception as e:
        print(f"  → Ad popup error: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# FIND SEARCH BOX
# ─────────────────────────────────────────────────────────────────────────────
async def _find_search_box(page):

    selectors = [
        'input[class*="shopee-searchbar-input"]',
        'input[placeholder*="Search" i]',
        'input[placeholder*="search" i]',
        'input[class*="search-bar__input"]',
        'input[type="search"]',
        'form input',
    ]

    for selector in selectors:
        try:
            el = page.locator(selector).first

            if await el.is_visible(timeout=3000):
                print(f"  → Search box found: {selector}")
                return el

        except Exception:
            continue

    print("  → Search box not found.")
    return None


# ─────────────────────────────────────────────────────────────────────────────
# MAIN SCRAPER
# ─────────────────────────────────────────────────────────────────────────────
async def scrape_shopee(
    product_query: str,
    user_id: str,
    max_pages: int = 10
) -> dict:

    product_id = str(uuid.uuid4())

    products_collection.insert_one({
        'product_id': product_id,
        'platform': 'shopee',
        'query': product_query,
        'user_id': user_id,
        'scraped_at': datetime.utcnow()
    })

    reviews = []

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=False,
            slow_mo=300
        )

        context = await browser.new_context(
            viewport={'width': 1366, 'height': 768},
            locale='en-US',
            java_script_enabled=True,
            bypass_csp=True,
            user_agent=(
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            )
        )

        page = await context.new_page()

        # Hide webdriver
        await page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        })
        """)

        try:

            # ─────────────────────────────────────────────────────────────
            # STEP 1: OPEN SHOPEE
            # ─────────────────────────────────────────────────────────────
            print("Step 1: Going to Shopee...")

            await page.goto(
                'https://shopee.com.my/',
                timeout=60000,
                wait_until='domcontentloaded'
            )

            await page.wait_for_load_state('networkidle')

            await _wait(page, 3)

            # Debug screenshot
            await page.screenshot(path="debug_homepage.png")

            # Handle language popup
            await _handle_language_popup(page)

            # Handle ad popup
            await _handle_ad_popup(page)

            await _wait(page, 2)

            # ─────────────────────────────────────────────────────────────
            # STEP 2: SEARCH PRODUCT
            # ─────────────────────────────────────────────────────────────
            print("Step 2: Searching product...")

            search_box = await _find_search_box(page)

            if not search_box:

                await page.screenshot(path="searchbox_error.png")

                await browser.close()

                return {
                    'success': False,
                    'product_id': product_id,
                    'reviews_count': 0,
                    'message': 'Search box not found'
                }

            await search_box.click(force=True)

            await _wait(page, 1)

            await search_box.fill(product_query)

            await _wait(page, 1)

            await search_box.press('Enter')

            print("  → Search submitted.")

            await page.wait_for_load_state('networkidle')

            await _wait(page, 4)

            # Close popup after search
            await _handle_ad_popup(page)

            # ─────────────────────────────────────────────────────────────
            # STEP 3: OPEN FIRST PRODUCT
            # ─────────────────────────────────────────────────────────────
            print("Step 3: Opening first product...")

            await page.wait_for_selector('a[href]', timeout=15000)

            links = await page.locator('a[href]').all()

            print(f"  → Total links found: {len(links)}")

            product_url = None

            for link in links[:50]:

                try:
                    href = await link.get_attribute('href')

                    if href and ('-i.' in href or '/product/' in href):

                        if href.startswith('http'):
                            product_url = href
                        else:
                            product_url = 'https://shopee.com.my' + href

                        print(f"  → Product URL found:")
                        print(product_url)

                        break

                except Exception:
                    continue

            if not product_url:

                await page.screenshot(path="product_error.png")

                await browser.close()

                return {
                    'success': False,
                    'product_id': product_id,
                    'reviews_count': 0,
                    'message': 'No product link found'
                }

            products_collection.update_one(
                {'product_id': product_id},
                {'$set': {'url': product_url}}
            )

            await page.goto(
                product_url,
                wait_until='domcontentloaded',
                timeout=60000
            )

            await page.wait_for_load_state('networkidle')

            await _wait(page, 4)

            # Close popup again
            await _handle_ad_popup(page)

            # ─────────────────────────────────────────────────────────────
            # STEP 4: SCROLL TO REVIEWS
            # ─────────────────────────────────────────────────────────────
            print("Step 4: Scrolling to reviews...")

            for _ in range(5):
                await page.mouse.wheel(0, 3000)
                await _wait(page, 1)

            await _wait(page, 3)

            # ─────────────────────────────────────────────────────────────
            # STEP 5: SCRAPE REVIEWS
            # ─────────────────────────────────────────────────────────────
            page_num = 1

            while page_num <= max_pages:

                print(f"Scraping review page {page_num}...")

                await _wait(page, 2)

                js_reviews = await page.evaluate("""
                (() => {

                    const items = Array.from(document.querySelectorAll(
                        '[class*="shopee-product-rating"],' +
                        '[class*="review"],' +
                        '[class*="rating"]'
                    ));

                    return items.map(el => {

                        const reviewer =
                            el.querySelector('[class*="author"], [class*="name"]')
                            ?.textContent?.trim() || 'Anonymous';

                        const comment =
                            el.querySelector('[class*="content"], [class*="comment"]')
                            ?.textContent?.trim() || '';

                        const date =
                            el.querySelector('[class*="time"], [class*="date"]')
                            ?.textContent?.trim() || '';

                        const rating = el.querySelectorAll(
                            'svg[class*="star"]'
                        ).length;

                        return {
                            reviewer,
                            comment,
                            date,
                            rating
                        };

                    }).filter(r => r.comment.length > 0);

                })();
                """)

                print(f"  → Found {len(js_reviews)} reviews")

                for r in js_reviews:

                    reviews.append({
                        'review_id': str(uuid.uuid4()),
                        'platform': 'shopee',
                        'product_id': product_id,
                        'product_query': product_query,
                        'reviewer_name': r['reviewer'],
                        'rating': r['rating'],
                        'comment': r['comment'],
                        'date': r['date'],
                        'user_id': user_id,
                        'created_at': datetime.utcnow()
                    })

                if page_num >= max_pages:
                    break

                # Try next page
                try:

                    next_btn = page.locator(
                        'button.shopee-icon-button--right'
                    ).first

                    if await next_btn.is_visible(timeout=5000):

                        await next_btn.click(force=True)

                        await _wait(page, 3)

                        page_num += 1

                    else:
                        print("  → No next page button.")
                        break

                except Exception:
                    print("  → Pagination ended.")
                    break

            # ─────────────────────────────────────────────────────────────
            # SAVE REVIEWS
            # ─────────────────────────────────────────────────────────────
            if reviews:
                reviews_collection.insert_many(reviews)

            print(f"Done. Saved {len(reviews)} reviews.")

            await browser.close()

            return {
                'success': True,
                'product_id': product_id,
                'reviews_count': len(reviews),
                'message': f'Scraped {len(reviews)} Shopee reviews'
            }

        except Exception as e:

            print(f"Error: {str(e)}")

            await page.screenshot(path="fatal_error.png")

            await browser.close()

            return {
                'success': False,
                'product_id': product_id,
                'reviews_count': 0,
                'message': str(e)
            }


# ─────────────────────────────────────────────────────────────────────────────
# TEST
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    asyncio.run(
        scrape_shopee("iPhone 15", "test_user")
    )
