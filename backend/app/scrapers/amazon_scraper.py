from playwright.async_api import async_playwright
from app.database import reviews_collection, products_collection
from datetime import datetime
import asyncio
import uuid
import os


async def is_login_page(page) -> bool:
    try:
        return await page.evaluate("""
            (() => {
                const url = window.location.href;
                const urlIndicates = ['signin', 'ap/', 'auth-page', 'login', 'ap\\x2fsignin'].some(x => url.includes(x));
                const hasLoginForm =
                    !!document.querySelector('input[name="email"]') ||
                    !!document.querySelector('input[name="phoneNumber"]') ||
                    !!document.querySelector('input[type="password"]') ||
                    !!document.querySelector('#auth-signin-button') ||
                    !!document.querySelector('#continue') ||
                    !!document.querySelector('form[name="signIn"]');
                return urlIndicates || hasLoginForm;
            })();
        """)
    except Exception:
        return False


async def wait_for_amazon_login(page):
    print("Waiting for you to complete login (phone + password)...")
    await page.wait_for_timeout(2000)
    consecutive_clear = 0
    while True:
        try:
            await page.wait_for_load_state('domcontentloaded', timeout=8000)
            on_login = await is_login_page(page)
            if on_login:
                consecutive_clear = 0
                await page.wait_for_timeout(1500)
            else:
                consecutive_clear += 1
                if consecutive_clear >= 3:
                    print("Login complete! Continuing scraper...")
                    return
                await page.wait_for_timeout(1500)
        except Exception as e:
            print(f"  (navigation in progress, waiting... {e})")
            consecutive_clear = 0
            await page.wait_for_timeout(2000)


async def scrape_amazon(product_query: str, user_id: str, max_pages: int = 10) -> dict:
    product_id = str(uuid.uuid4())
    product_doc = {
        'product_id': product_id,
        'platform': 'amazon',
        'query': product_query,
        'user_id': user_id,
        'scraped_at': datetime.utcnow()
    }
    products_collection.insert_one(product_doc)

    reviews = []
    SESSION_FILE = 'amazon_session.json'

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            storage_state=SESSION_FILE if os.path.exists(SESSION_FILE) else None,
            viewport={'width': 1366, 'height': 768},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = await context.new_page()

        try:
            # 1. Go to Amazon
            print("Step 1: Going to Amazon...")
            await page.goto('https://www.amazon.com/', timeout=60000, wait_until='domcontentloaded')
            await page.wait_for_timeout(2000)

            # 2. Search product
            print("Step 2: Searching product...")
            await page.fill('#twotabsearchtextbox', product_query)
            await page.press('#twotabsearchtextbox', 'Enter')
            await page.wait_for_timeout(4000)

            # 3. Open first product
            print("Step 3: Opening first product...")
            product_url = None
            product_elements = await page.locator('a[href*="/dp/"]').all()
            for link in product_elements[:5]:
                href = await link.get_attribute('href')
                if href and '/dp/' in href:
                    product_url = href if href.startswith('http') else 'https://www.amazon.com' + href
                    break

            if not product_url:
                return {'success': False, 'product_id': product_id, 'reviews_count': 0, 'message': 'No product link found'}

            print(f"Product URL: {product_url}")
            products_collection.update_one({'product_id': product_id}, {'$set': {'url': product_url}})
            await page.goto(product_url, wait_until='domcontentloaded', timeout=60000)
            await page.wait_for_timeout(3000)

            # 4. Scroll to bottom twice to trigger lazy-loaded review links
            print("Step 4: Scrolling to load reviews section...")
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(2000)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(2000)

            # 5. Find "See all reviews" link
            print("Step 5: Finding 'See all reviews' link...")
            see_all_href = None
            selectors = [
                'a[data-hook="see-all-reviews-link-foot"]',
                'a[data-hook="see-all-reviews-link-foot-text"]',
                'a[href*="/product-reviews/"]',
                'a[href*="customer-reviews"]',
            ]
            for selector in selectors:
                try:
                    el = page.locator(selector).first
                    href = await el.get_attribute('href', timeout=3000)
                    if href:
                        see_all_href = href
                        print(f"  → Found via selector: {selector}")
                        break
                except Exception:
                    continue

            # Fallback: scan all links
            if not see_all_href:
                print("  → Trying fallback: scanning all links...")
                all_links = await page.locator('a').all()
                for link in all_links:
                    try:
                        href = await link.get_attribute('href', timeout=1000)
                        if href and 'product-reviews' in href:
                            see_all_href = href
                            print(f"  → Found via fallback scan: {href}")
                            break
                    except Exception:
                        continue

            if not see_all_href:
                print("  → ERROR: Could not find reviews link. Dumping page links for debug...")
                all_links = await page.locator('a').all()
                for link in all_links[:40]:
                    try:
                        href = await link.get_attribute('href', timeout=500)
                        text = await link.text_content(timeout=500)
                        if href:
                            print(f"    [{text.strip()[:40] if text else ''}] → {href[:80]}")
                    except Exception:
                        continue
                return {'success': False, 'product_id': product_id, 'reviews_count': 0, 'message': 'Could not find See all reviews link'}

            reviews_base_url = see_all_href if see_all_href.startswith('http') else 'https://www.amazon.com' + see_all_href
            reviews_base_url = reviews_base_url.split('pageNumber=')[0].rstrip('&?')
            print(f"  → Reviews base URL: {reviews_base_url}")

            # ← first_page_url is now defined BEFORE the login check uses it
            first_page_url = f"{reviews_base_url}?pageNumber=1"

            # 6. Navigate to reviews page 1 (may trigger login)
            print("Step 6: Navigating to reviews page...")
            await page.goto(first_page_url, wait_until='domcontentloaded', timeout=60000)
            await page.wait_for_timeout(3000)

            # Handle login if triggered
            if await is_login_page(page):
                print("\n" + "="*50)
                print("Amazon is asking you to log in.")
                print("Please log in manually in the browser window.")
                print("The scraper will automatically continue once done.")
                print("="*50 + "\n")

                await wait_for_amazon_login(page)

                await context.storage_state(path=SESSION_FILE)
                print(f"Session saved to {SESSION_FILE} — next run will skip login.\n")

                print("Navigating back to reviews page...")
                await page.goto(first_page_url, wait_until='domcontentloaded', timeout=60000)
                await page.wait_for_timeout(3000)

                # Handle any second challenge (OTP etc.)
                if await is_login_page(page):
                    print("Amazon requires another step — please complete it in the browser...")
                    await wait_for_amazon_login(page)
                    await page.goto(first_page_url, wait_until='domcontentloaded', timeout=60000)
                    await page.wait_for_timeout(3000)

            # 7. Paginate through review pages
            page_num = 1
            while page_num <= max_pages:
                paginated_url = f"{reviews_base_url}?pageNumber={page_num}"
                print(f"Scraping review page {page_num}...")

                if page_num > 1:
                    await page.goto(paginated_url, wait_until='domcontentloaded', timeout=60000)
                    await page.wait_for_timeout(3000)

                # Check for mid-scrape session expiry
                if await is_login_page(page):
                    print("Login required mid-scrape. Please log in in the browser...")
                    await wait_for_amazon_login(page)
                    await context.storage_state(path=SESSION_FILE)
                    print("Session re-saved.\n")
                    await page.goto(paginated_url, wait_until='domcontentloaded', timeout=60000)
                    await page.wait_for_timeout(3000)

                await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
                await page.wait_for_timeout(1500)

                # Extract reviews with retry
                js_reviews = []
                for attempt in range(2):
                    try:
                        js_reviews = await page.evaluate("""
                            (() => {
                                const items = Array.from(document.querySelectorAll('[data-hook="review"]'));
                                return items.map(function(el) {
                                    const reviewer =
                                        el.querySelector('.a-profile-name')?.textContent?.trim() || 'Anonymous';
                                    const date =
                                        el.querySelector('[data-hook="review-date"]')?.textContent?.trim() || '';
                                    let rating = 0;
                                    const starEl = el.querySelector(
                                        '[data-hook="review-star-rating"], [data-hook="cmps-review-star-rating"]'
                                    );
                                    if (starEl) {
                                        const ariaLabel = starEl.querySelector('.a-icon-alt')?.textContent || '';
                                        const match = ariaLabel.match(/(\\d+(?:\\.\\d+)?)/);
                                        if (match) rating = Math.round(parseFloat(match[1]));
                                    }
                                    const title =
                                        el.querySelector('[data-hook="review-title"] span:not(.a-icon-alt)')
                                          ?.textContent?.trim() || '';
                                    const comment =
                                        el.querySelector('[data-hook="review-body"] span')
                                          ?.textContent?.trim() || '';
                                    const variant =
                                        el.querySelector('[data-hook="format-strip"]')
                                          ?.textContent?.trim() || '';
                                    const verified = !!el.querySelector('[data-hook="avp-badge"]');
                                    return { reviewer, rating, title, comment, date, variant, verified };
                                }).filter(function(r) { return r.comment.length > 0; });
                            })();
                        """)
                        break
                    except Exception as e:
                        print(f"  → Evaluate attempt {attempt + 1} failed: {e}")
                        await page.wait_for_timeout(3000)
                        await page.wait_for_load_state('domcontentloaded', timeout=10000)

                print(f"  → Found {len(js_reviews)} reviews on page {page_num}")

                if len(js_reviews) == 0:
                    print("  → No reviews found, stopping pagination.")
                    break

                reviews.extend([{
                    'review_id': str(uuid.uuid4()),
                    'platform': 'amazon',
                    'product_id': product_id,
                    'product_query': product_query,
                    'reviewer_name': r['reviewer'],
                    'rating': r['rating'],
                    'title': r['title'],
                    'comment': r['comment'],
                    'variant': r['variant'],
                    'date': r['date'],
                    'verified': r['verified'],
                    'user_id': user_id,
                    'created_at': datetime.utcnow()
                } for r in js_reviews])

                if page_num >= max_pages:
                    break

                has_next = await page.evaluate("""
                    (() => {
                        const next = document.querySelector('li.a-last a');
                        return !!next && !next.closest('li')?.classList.contains('a-disabled');
                    })();
                """)

                if not has_next:
                    print("  → No next page, stopping pagination.")
                    break

                page_num += 1
                await page.wait_for_timeout(2000)

            if reviews:
                reviews_collection.insert_many(reviews)
            print(f"Done. Saved {len(reviews)} reviews from {page_num} pages.")

            await browser.close()
            return {
                'success': True,
                'product_id': product_id,
                'reviews_count': len(reviews),
                'message': f'Scraped {len(reviews)} reviews across {page_num} pages'
            }

        except Exception as e:
            print(f"Error: {str(e)}")
            await browser.close()
            return {'success': False, 'product_id': product_id, 'reviews_count': 0, 'message': str(e)}


if __name__ == "__main__":
    asyncio.run(scrape_amazon("iphone 15", "test"))