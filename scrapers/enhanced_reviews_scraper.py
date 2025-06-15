from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import csv
import time
import logging
from dotenv import load_dotenv
import os
import json
import re

load_dotenv()
EMAIL = os.getenv("SERIALIZD_EMAIL")
PASSWORD = os.getenv("SERIALIZD_PASSWORD")
USERNAME = os.getenv("SERIALIZD_USERNAME")

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Set up Chrome options
options = Options()
# options.add_argument("--headless")  # Uncomment for headless mode
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

try:
    logging.info("Navigating to login page")
    driver.get("https://serializd.com/login")

    # Wait for login form
    wait = WebDriverWait(driver, 20)
    logging.info("Locating email and password fields")

    # Find email and password fields
    email_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email']")))
    password_field = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
    email_field.send_keys(EMAIL)
    password_field.send_keys(PASSWORD)

    # Find login button
    logging.info("Clicking login button")
    login_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']")))
    login_button.click()

    # Wait for redirect
    logging.info("Waiting for login redirect")
    time.sleep(5)

    # Navigate to reviews page
    reviews_url = f"https://serializd.com/user/{USERNAME}/reviews"
    logging.info(f"Navigating to {reviews_url}")
    driver.get(reviews_url)
    time.sleep(5)

    # Take screenshot for debugging
    driver.save_screenshot("debug_output/reviews_page_debug.png")
    logging.info("Saved reviews page screenshot")

    reviews_data = []
    seen_reviews = set()
    page_num = 1
    
    while True:  # Continue until no more reviews
        logging.info(f"Processing reviews page {page_num}")
        
        # Wait for review elements to load
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div, article, section")))
            time.sleep(3)  # Additional wait for dynamic content
        except:
            logging.warning(f"No review elements found on page {page_num}")
            break

        # Try multiple selectors for review containers
        review_selectors = [
            ".review-card",
            ".review-item", 
            ".review",
            "[class*='review']",
            ".card",
            "[class*='card']",
            "article",
            ".post",
            "[class*='post']"
        ]
        
        review_elements = []
        working_selector = None
        
        for selector in review_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    # Filter elements that likely contain reviews
                    potential_reviews = []
                    for elem in elements:
                        elem_text = elem.text.lower()
                        # Look for review indicators
                        if any(indicator in elem_text for indicator in ['season', 'episode', 'rating', 'review', 'watched']):
                            potential_reviews.append(elem)
                    
                    if potential_reviews:
                        review_elements = potential_reviews
                        working_selector = selector
                        logging.info(f"Found {len(review_elements)} potential review elements with selector: {selector}")
                        break
            except:
                continue

        if not review_elements:
            logging.warning(f"No review elements found on page {page_num}")
            # Try to find any links that might contain reviews
            review_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/review/']")
            if review_links:
                logging.info(f"Found {len(review_links)} review links instead")
                review_elements = review_links
                working_selector = "a[href*='/review/']"
            else:
                break

        # Extract review information from current page
        page_reviews_added = 0
        for i, review_elem in enumerate(review_elements):
            try:
                # Get review ID to avoid duplicates
                review_id = None
                try:
                    if working_selector == "a[href*='/review/']":
                        review_url = review_elem.get_attribute("href")
                        review_id = review_url.split("/review/")[-1] if review_url and "/review/" in review_url else None
                    else:
                        # Look for review links within the element
                        review_link = review_elem.find_element(By.CSS_SELECTOR, "a[href*='/review/']")
                        review_url = review_link.get_attribute("href")
                        review_id = review_url.split("/review/")[-1] if review_url and "/review/" in review_url else None
                except:
                    review_id = f"page_{page_num}_item_{i}"  # Fallback ID

                if review_id in seen_reviews:
                    continue
                seen_reviews.add(review_id)

                # Extract show title
                title = "Unknown"
                title_selectors = [
                    "h1", "h2", "h3", "h4",
                    ".title", "[class*='title']",
                    ".show-title", "[class*='show']",
                    "img[alt]"
                ]
                
                for title_sel in title_selectors:
                    try:
                        if "img" in title_sel:
                            img_elem = review_elem.find_element(By.CSS_SELECTOR, title_sel)
                            alt_text = img_elem.get_attribute("alt")
                            if alt_text and "poster" in alt_text.lower():
                                title = alt_text.replace("Poster for ", "").replace("poster", "").strip()
                                break
                        else:
                            title_elem = review_elem.find_element(By.CSS_SELECTOR, title_sel)
                            title_text = title_elem.text.strip()
                            if title_text and len(title_text) > 2:
                                title = title_text
                                break
                    except:
                        continue

                # Extract season/episode info
                season_episode = "N/A"
                season_selectors = [
                    ".season", "[class*='season']",
                    ".episode", "[class*='episode']",
                    ".small-text", ".meta", "[class*='meta']"
                ]
                
                for season_sel in season_selectors:
                    try:
                        season_elem = review_elem.find_element(By.CSS_SELECTOR, season_sel)
                        season_text = season_elem.text.strip()
                        if season_text and ("season" in season_text.lower() or "episode" in season_text.lower()):
                            season_episode = season_text
                            break
                    except:
                        continue

                # Extract rating
                rating = "N/A"
                rating_selectors = [
                    "[class*='rating']", ".rating",
                    "[class*='score']", ".score", 
                    "[class*='star']", ".star",
                    "[class*='grade']", ".grade"
                ]
                
                for rating_sel in rating_selectors:
                    try:
                        rating_elem = review_elem.find_element(By.CSS_SELECTOR, rating_sel)
                        rating_text = rating_elem.text.strip()
                        # Look for numeric ratings or letter grades
                        if rating_text and (rating_text.replace(".", "").replace("/", "").replace("10", "").isdigit() or 
                                          rating_text in ["A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "F"]):
                            rating = rating_text
                            break
                    except:
                        continue

                # Extract review text
                review_text = "N/A"
                review_selectors = [
                    ".review-text", "[class*='review-text']",
                    ".review-content", "[class*='review-content']",
                    ".content", "[class*='content']",
                    ".text", "[class*='text']",
                    "p"
                ]
                
                for review_sel in review_selectors:
                    try:
                        review_elem_text = review_elem.find_element(By.CSS_SELECTOR, review_sel)
                        review_content = review_elem_text.text.strip()
                        if review_content and len(review_content) > 10:  # Ensure it's substantial text
                            review_text = review_content
                            break
                    except:
                        continue

                # Extract watch date if available
                watch_date = "N/A"
                date_selectors = [
                    ".date", "[class*='date']",
                    ".time", "[class*='time']",
                    ".timestamp", "[class*='timestamp']",
                    "time"
                ]
                
                for date_sel in date_selectors:
                    try:
                        date_elem = review_elem.find_element(By.CSS_SELECTOR, date_sel)
                        date_text = date_elem.text.strip()
                        # Look for date patterns
                        if date_text and (re.search(r'\d{4}', date_text) or re.search(r'\d{1,2}/\d{1,2}', date_text)):
                            watch_date = date_text
                            break
                    except:
                        continue

                if title != "Unknown":
                    reviews_data.append({
                        "Title": title,
                        "Season_Episode": season_episode,
                        "Rating": rating,
                        "Review_Text": review_text,
                        "Watch_Date": watch_date,
                        "Review_ID": review_id,
                        "Page": page_num
                    })
                    page_reviews_added += 1

            except Exception as e:
                logging.error(f"Error scraping review {i+1} on page {page_num}: {e}")
                continue

        logging.info(f"Added {page_reviews_added} new reviews from page {page_num}. Total: {len(reviews_data)}")
        
        # Save progress after each page
        if reviews_data:
            with open("data/progress_reviews.csv", "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["Title", "Season_Episode", "Rating", "Review_Text", "Watch_Date", "Review_ID", "Page"])
                writer.writeheader()
                writer.writerows(reviews_data)
            logging.info(f"Progress saved: {len(reviews_data)} reviews so far")

        # Try to find and click the next page button
        next_found = False
        
        try:
            # Look for pagination
            pagination_selectors = [
                ".pagination-next", ".next",
                "[aria-label*='Next']", "[aria-label*='next']",
                ".pagination-item:last-child",
                "a[href*='page=']"
            ]
            
            for next_sel in pagination_selectors:
                try:
                    next_button = driver.find_element(By.CSS_SELECTOR, next_sel)
                    if next_button.is_enabled() and next_button.is_displayed():
                        logging.info(f"Found next button with selector: {next_sel}")
                        driver.execute_script("arguments[0].click();", next_button)
                        next_found = True
                        time.sleep(3)
                        break
                except:
                    continue
                    
        except Exception as e:
            logging.error(f"Error finding pagination: {e}")

        if not next_found:
            logging.info(f"No next page button found after page {page_num}, stopping")
            break
            
        page_num += 1
        
        # Safety limit
        if page_num > 50:  # Reasonable limit for reviews
            logging.info("Reached page limit of 50, stopping")
            break

    # Final save
    if reviews_data:
        # Save to CSV
        logging.info("Saving final reviews to CSV")
        with open("data/serializd_reviews.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["Title", "Season_Episode", "Rating", "Review_Text", "Watch_Date", "Review_ID", "Page"])
            writer.writeheader()
            writer.writerows(reviews_data)

        # Also save to JSON
        with open("data/serializd_reviews.json", "w", encoding="utf-8") as f:
            json.dump(reviews_data, f, indent=2, ensure_ascii=False)

        logging.info(f"Successfully scraped {len(reviews_data)} reviews from {page_num-1} pages!")
        logging.info("Results saved to:")
        logging.info("- data/serializd_reviews.csv")
        logging.info("- data/serializd_reviews.json")
        
        # Print statistics
        rated_reviews = [r for r in reviews_data if r["Rating"] != "N/A"]
        logging.info(f"Total reviews scraped: {len(reviews_data)}")
        logging.info(f"Reviews with ratings: {len(rated_reviews)}")
        logging.info(f"Reviews with text: {len([r for r in reviews_data if r['Review_Text'] != 'N/A'])}")
        
        # Print first few reviews as preview
        logging.info("First 5 reviews:")
        for i, review in enumerate(reviews_data[:5]):
            logging.info(f"{i+1}. {review['Title']} - Rating: {review['Rating']}")
            if review['Review_Text'] != 'N/A':
                preview_text = review['Review_Text'][:100] + "..." if len(review['Review_Text']) > 100 else review['Review_Text']
                logging.info(f"   Review: {preview_text}")
            
    else:
        logging.error("No reviews were scraped!")
        # Save page source for debugging
        with open("debug_output/reviews_page_source.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        logging.info("Saved page source for debugging")

except Exception as e:
    logging.error(f"An error occurred: {e}")
    driver.save_screenshot("debug_output/reviews_error.png")
    with open("debug_output/reviews_error_source.html", "w", encoding="utf-8") as f:
        f.write(driver.page_source)
    logging.info("Error screenshot and page source saved for debugging")

finally:
    logging.info("Closing browser")
    try:
        driver.quit()
    except:
        pass
