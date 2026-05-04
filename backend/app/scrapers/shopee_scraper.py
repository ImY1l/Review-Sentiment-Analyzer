from playwright.async_api import async_playwright
from app.database import reviews_collection, products_collection
from datetime import datetime
import asyncio
import uuid
import os

async def scrape_shopee(product_query: str, user_id: str, max_pages: int = 10) -> dict:
    product_id = str(uuid.uuid4())
    product_doc = {
        'product_id': product_id,
        'platform': 'shopee',
        'query': product_query,
        'user_id': user_id,
        'scraped_at': datetime.utcnow()
    }
    products_collection.insert_one(product_doc)

    reviews = []

    tmp_dir = 'backend/tmp_shopee'
    os.makedirs(tmp_dir, exist_ok=True)

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=os.path.abspath(tmp_dir),
            headless=False,
            viewport={'width': 1366, 'height': 768},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = await context.new_page()


#         try:
#             # 1. Go to Shopee
#             print("Step 1: Going to Shopee...")
#             await page.goto('https://shopee.com.my/', timeout=60000, wait_until='domcontentloaded')
#             await page.wait_for_timeout(3000)

#             # 2. Close initial ad popup if present
#             print("Step 2: Closing ad popup...")
#             close_selectors = [
#                 '[data-testid="close-popup"]',
#                 'button[title*="close"], button[aria-label*="close"]',
#                 '.X-btn, .modal-close, [class*="close"]',
#                 '.shopee-popup__close-btn'
#             ]
#             for selector in close_selectors:
#                 try:
#                     close_btn = page.locator(selector).first
#                     if await close_btn.is_visible(timeout=2000):
#                         await close_btn.click()
#                         print(f"Closed ad with selector: {selector}")
#                         await page.wait_for_timeout(1000)
#                         break
#                 except:
#                     continue
#             await page.wait_for_timeout(2000)

#             # 3. Search product
#             print("Step 3: Searching product...")
#             await page.fill('[data-testid="search-input"]', product_query)
#             await page.press('[data-testid="search-input"]', 'Enter')
#             await page.wait_for_timeout(5000)

#             # 4. Open first product
#             print("Step 4: Opening first product...")
#             product_url = None
#             product_elements = await page.locator('a[href*="/product/"]').all()[:5]
#             for link in product_elements:
#                 href = await link.get_attribute('href')
#                 if href and '/product/' in href:
#                     product_url = 'https://shopee.com.my' + href if href.startswith('//') else href
#                     break

#             if not product_url:
#                 return {'success': False, 'reviews_count': 0, 'message': 'No product link found'}

#             print(f"Product URL: {product_url}")
#             products_collection.update_one({'product_id': product_id}, {'$set': {'url': product_url}})
#             await page.goto(product_url, wait_until='networkidle', timeout=60000)
#             await page.wait_for_timeout(5000)

#             # 5. Click Reviews tab
#             print("Step 5: Clicking Reviews tab...")
#             reviews_tab_selectors = [
#                 'a:has-text("Reviews")',
#                 '[data-testid="tab-reviews"]',
#                 'button:Has-text("Reviews"), div:Has-text("Reviews")'
#             ]
#             for selector in reviews_tab_selectors:
#                 try:
#                     tab = page.locator(selector).first
#                     await tab.scroll_into_view_if_needed()
#                     await tab.click()
#                     await page.wait_for_timeout(4000)
#                     break
#                 except:
#                     continue

#             # 6. Paginate and extract reviews
#             page_num = 1
#             while page_num <= max_pages:
#                 print(f"Scraping review page {page_num}...")

#                 # Scroll to reviews
#                 await page.evaluate("""
#                     window.scrollTo(0, document.body.scrollHeight * 0.4);
#                 """)
#                 await page.wait_for_timeout(2000)

#                 # Enhanced review extraction (same as Lazada full-text fix)
#                 js_reviews = await page.evaluate("""
#                     (() => {
#                         const root = document.querySelector('[data-sqe="reviews"]') || document.querySelector('.review-list') || document;
#                         const items = Array.from(root.querySelectorAll('[data-sqe="review-item"], .review-item, article[class*="review"]'));

#                         return items.map(el => {
#                             // Trigger hover for full text reveal
#                             el.dispatchEvent(new MouseEvent('mouseenter', {bubbles: true}));
#                             el.dispatchEvent(new MouseEvent('mouseover', {bubbles: true}));

#                             // Reviewer
#                             const reviewer = el.querySelector('[class*="username"], [class*="author"], [class*="reviewer"]')?.textContent?.trim() || 'Anonymous';

#                             // Rating (Shopee uses aria-label or filled stars)
#                             const ratingEl = el.querySelector('[class*="rating"]');
#                             const ratingAttr = parseFloat(ratingEl?.getAttribute('aria-label')?.match(/(\\d+\\.?\\d*)/)?.[1] || '0');
#                             const ratingCount = el.querySelectorAll('[class*="star-filled"]').length;
#                             const rating = ratingAttr || ratingCount || 0;

#                             // FULL COMMENT - multi-source
#                             let comment = '';
#                             const contentEl = el.querySelector('[class*="content"], [class*="review-text"], [class*="comment"], .review-message');
#                             if (contentEl) {
#                                 comment = contentEl.textContent?.trim() || '';
#                                 // Title attr fallback
#                                 const title = contentEl.getAttribute('title') || '';
#                                 if (title && title.length > comment.length * 1.1) comment = title;
#                                 // Data attrs
#                                 const dataFull = contentEl.getAttribute('data-full-text') || el.getAttribute('data-comment') || '';
#                                 if (dataFull && dataFull.length > comment.length) comment = dataFull;
#                             }
#                             // Fallback full text clean
#                             if (comment.length < 20 || comment.includes('…')) {
#                                 let fullText = el.textContent?.trim() || '';
#                                 fullText = fullText.replace(reviewer, '').replace(/\\d+(?:\\.\\d+)?\\s*(?:star|⭐)/gi, '').trim();
#                                 const sentences = fullText.split(/[.!?]+/).filter(s => s.trim().length > 10);
#                                 comment = sentences.slice(0, 3).join('. ').trim();
#                             }
#                             comment = comment.replace(/\\.{3,}/g, '').replace(/\\s{2,}/g, ' ').trim();
#                             if (!comment || comment.length < 5) comment = 'No comment';

#                             // Date
#                             const date = el.querySelector('[class*="date"], time')?.textContent?.trim() || '';

#                             // Variant
#                             const variant = el.querySelector('[class*="variant"], [class*="sku"]')?.textContent?.trim() || '';

#                             return { reviewer, rating, comment, date, variant };
#                         }).filter(r => r.comment.length > 5);
#                     })();
#                 """)

#                 print(f"  → Found {len(js_reviews)} reviews on page {page_num}")
#                 reviews.extend([{
#                     'review_id': str(uuid.uuid4()),
#                     'platform': 'shopee',
#                     'product_id': product_id,
#                     'product_query': product_query,
#                     'reviewer_name': r['reviewer'],
#                     'rating': r['rating'],
#                     'comment': r['comment'],
#                     'variant': r['variant'],
#                     'date': r['date'],
#                     'user_id': user_id,
#                     'created_at': datetime.utcnow()
#                 } for r in js_reviews])

#                 if len(js_reviews) == 0 or page_num >= max_pages:
#                     break

#                 # Shopee pagination: click 'Next' or page number
#                 next_clicked = await page.locator('[data-testid="pagination-next"], button:Has-text("Next"), a:Has-text(">")', timeout=5000).click()
#                 if not next_clicked:
#                     # Fallback page number click (similar to Lazada)
#                     next_page_num = page_num + 1
#                     await page.evaluate(f'''
#                         const target = Array.from(document.querySelectorAll('button, a')).find(el => 
#                             el.textContent.trim() === '{next_page_num}' && 
#                             el.offsetParent !== null
#                         );
#                         if (target) target.click();
#                     ''')
#                 await page.wait_for_timeout(4000)
#                 page_num += 1

#             # Save to DB
#             if reviews:
#                 reviews_collection.insert_many(reviews)
#             print(f"Done. Saved {len(reviews)} reviews from {page_num-1} pages.")

#             await browser.close()
#             return {
#                 'success': True,
#                 'reviews_count': len(reviews),
#                 'message': f'Scraped {len(reviews)} reviews across {page_num-1} pages'
#             }

#         except Exception as e:
#             print(f"Error: {str(e)}")
#             await browser.close()
#             return {'success': False, 'reviews_count': 0, 'message': str(e)}


# if __name__ == "__main__":
#     asyncio.run(scrape_shopee("iphone 15", "test"))

