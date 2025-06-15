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

    # Navigate to shows page
    shows_url = f"https://serializd.com/user/{USERNAME}/shows"
    logging.info(f"Navigating to {shows_url}")
    driver.get(shows_url)
    time.sleep(5)

    watched_shows = []
    seen_titles = set()
    page_num = 1
    
    while page_num <= 21:  # Maximum 21 pages as you mentioned
        logging.info(f"Processing page {page_num}")
        
        # Wait for show elements to load
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".show-card-v2-container")))
        except:
            logging.warning(f"No show cards found on page {page_num}")
            break

        # Get all show elements on current page
        show_elements = driver.find_elements(By.CSS_SELECTOR, ".show-card-v2-container")
        logging.info(f"Found {len(show_elements)} show elements on page {page_num}")

        if not show_elements:
            logging.info(f"No shows found on page {page_num}, stopping")
            break

        # Extract show information from current page
        page_shows_added = 0
        for i, show in enumerate(show_elements):
            try:
                title = "Unknown"
                
                # Try multiple ways to get the title
                title_selectors = ["h3", "h2", "h1", ".title", "[class*='title']", "img"]
                for title_sel in title_selectors:
                    try:
                        if title_sel == "img":
                            # Get from alt attribute
                            img_element = show.find_element(By.CSS_SELECTOR, "img")
                            alt_text = img_element.get_attribute("alt")
                            if alt_text and alt_text != "":
                                title = alt_text.replace("Poster for ", "").replace("poster", "").strip()
                                break
                        else:
                            title_element = show.find_element(By.CSS_SELECTOR, title_sel)
                            title_text = title_element.text.strip()
                            if title_text and title_text != "":
                                title = title_text
                                break
                    except:
                        continue

                if title == "Unknown" or title == "" or title == "undefined":
                    continue

                # Skip duplicates
                if title in seen_titles:
                    continue
                seen_titles.add(title)

                # Try to get rating
                rating = "N/A"
                rating_selectors = [
                    "[class*='rating']", 
                    ".rating", 
                    "[class*='score']", 
                    ".score",
                    "[class*='star']",
                    ".star"
                ]
                for rating_sel in rating_selectors:
                    try:
                        rating_element = show.find_element(By.CSS_SELECTOR, rating_sel)
                        rating_text = rating_element.text.strip()
                        if rating_text and rating_text != "":
                            rating = rating_text
                            break
                    except:
                        continue

                watched_shows.append({
                    "Title": title,
                    "Status": "Watched",
                    "Rating": rating,
                    "Seasons": "N/A",
                    "Page": page_num
                })
                page_shows_added += 1

            except Exception as e:
                logging.error(f"Error scraping show {i+1} on page {page_num}: {e}")
                continue

        logging.info(f"Added {page_shows_added} new shows from page {page_num}. Total: {len(watched_shows)}")
        
        # Save progress after each page
        if watched_shows:
            with open("progress_watched_shows.csv", "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["Title", "Status", "Rating", "Seasons", "Page"])
                writer.writeheader()
                writer.writerows(watched_shows)
            logging.info(f"Progress saved: {len(watched_shows)} shows so far")

        # Try to find and click the next page button
        next_found = False
        
        # Look for pagination buttons
        try:
            # Find all pagination items
            pagination_items = driver.find_elements(By.CSS_SELECTOR, ".pagination-item")
            logging.info(f"Found {len(pagination_items)} pagination items")
            
            # Look for the next page number
            next_page_num = page_num + 1
            for item in pagination_items:
                try:
                    if item.text.strip() == str(next_page_num):
                        logging.info(f"Found next page button for page {next_page_num}")
                        driver.execute_script("arguments[0].click();", item)
                        next_found = True
                        time.sleep(3)  # Wait for page to load
                        break
                except Exception as e:
                    continue
            
            # If we didn't find the specific page number, try other next button selectors
            if not next_found:
                next_selectors = [
                    ".pagination-next",
                    ".next",
                    "[aria-label*='Next']",
                    ".pagination-item:last-child"
                ]
                
                for next_sel in next_selectors:
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

    # Final save
    if watched_shows:
        # Save to CSV
        logging.info("Saving final results to CSV")
        with open("final_watched_shows.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["Title", "Status", "Rating", "Seasons", "Page"])
            writer.writeheader()
            writer.writerows(watched_shows)

        # Also save to JSON for easier reading
        with open("final_watched_shows.json", "w", encoding="utf-8") as f:
            json.dump(watched_shows, f, indent=2, ensure_ascii=False)

        logging.info(f"Successfully scraped {len(watched_shows)} watched shows from {page_num-1} pages!")
        logging.info("Results saved to:")
        logging.info("- final_watched_shows.csv")
        logging.info("- final_watched_shows.json")
        
        # Print statistics
        logging.info(f"Total shows scraped: {len(watched_shows)}")
        logging.info(f"Pages processed: {page_num-1}")
        if page_num > 1:
            logging.info(f"Average shows per page: {len(watched_shows) / (page_num-1):.1f}")
        
        # Print first few shows as preview
        logging.info("First 10 shows:")
        for i, show in enumerate(watched_shows[:10]):
            logging.info(f"{i+1}. {show['Title']} (Rating: {show['Rating']}, Page: {show['Page']})")
            
        # Print last few shows as well
        if len(watched_shows) > 10:
            logging.info("Last 5 shows:")
            for i, show in enumerate(watched_shows[-5:], len(watched_shows)-4):
                logging.info(f"{i}. {show['Title']} (Rating: {show['Rating']}, Page: {show['Page']})")
            
    else:
        logging.error("No shows were scraped!")

except Exception as e:
    logging.error(f"An error occurred: {e}")
    driver.save_screenshot("click_pagination_error.png")
    with open("click_pagination_error_source.html", "w", encoding="utf-8") as f:
        f.write(driver.page_source)
    logging.info("Error screenshot and page source saved for debugging")

finally:
    logging.info("Closing browser")
    try:
        driver.quit()
    except:
        pass  # Ignore errors when closing
