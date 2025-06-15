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

    # Navigate to shows page (where all watched shows are)
    watched_url = f"https://serializd.com/user/{USERNAME}/shows"
    logging.info(f"Navigating to {watched_url}")
    driver.get(watched_url)

    # Wait for page to load
    time.sleep(3)

    # Take a screenshot for debugging
    driver.save_screenshot("debug_output/watched_page.png")
    logging.info("Saved screenshot as debug_output/watched_page.png")

    # Try different approaches to find shows
    watched_shows = []
    seen_titles = set()

    # Method 1: Look for show cards with different selectors
    selectors_to_try = [
        ".show-card-v2-container",
        ".show-card",
        "[class*='show-card']",
        ".card",
        "[class*='card']",
        ".poster",
        "[class*='poster']"
    ]

    shows_found = False
    working_selector = None
    for selector in selectors_to_try:
        try:
            show_elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if show_elements:
                logging.info(f"Found {len(show_elements)} elements with selector: {selector}")
                shows_found = True
                working_selector = selector
                break
        except Exception as e:
            logging.error(f"Error with selector {selector}: {e}")
            continue

    if not shows_found:
        logging.error("No show elements found with any selector")
        # Save page source for debugging
        with open("debug_output/watched_page_source.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        logging.info("Saved page source as debug_output/watched_page_source.html")
    else:
        # Method 2: Infinite scroll to load all shows
        logging.info("Scrolling to load all shows")
        last_height = driver.execute_script("return document.body.scrollHeight")
        scroll_attempts = 0
        max_scroll_attempts = 50  # Prevent infinite scrolling

        while scroll_attempts < max_scroll_attempts:
            # Scroll down to bottom
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            
            # Wait for new content to load
            time.sleep(2)
            
            # Calculate new scroll height and compare with last scroll height
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                logging.info(f"No more content to load after {scroll_attempts} scroll attempts")
                break
            last_height = new_height
            scroll_attempts += 1
            
            # Check how many shows we have now
            current_shows = driver.find_elements(By.CSS_SELECTOR, working_selector)
            logging.info(f"After scroll {scroll_attempts}: Found {len(current_shows)} shows")

        # Now extract all the shows
        show_elements = driver.find_elements(By.CSS_SELECTOR, working_selector)
        logging.info(f"Final count: Found {len(show_elements)} show elements")

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

                if title == "Unknown" or title == "":
                    logging.warning(f"Could not extract title for show {i+1}")
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
                    "Seasons": "N/A"
                })
                
                if len(watched_shows) % 50 == 0:
                    logging.info(f"Scraped {len(watched_shows)} shows so far...")

            except Exception as e:
                logging.error(f"Error scraping show {i+1}: {e}")
                continue

    # Save results
    if watched_shows:
        # Save to CSV
        logging.info("Saving watched shows to CSV")
        with open("data/improved_watched_shows.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["Title", "Status", "Rating", "Seasons"])
            writer.writeheader()
            writer.writerows(watched_shows)

        # Also save to JSON for easier reading
        with open("data/improved_watched_shows.json", "w", encoding="utf-8") as f:
            json.dump(watched_shows, f, indent=2, ensure_ascii=False)

        logging.info(f"Successfully scraped {len(watched_shows)} watched shows!")
        logging.info("Results saved to:")
        logging.info("- data/improved_watched_shows.csv")
        logging.info("- data/improved_watched_shows.json")
        
        # Print first few shows as preview
        logging.info("First 10 shows:")
        for i, show in enumerate(watched_shows[:10]):
            logging.info(f"{i+1}. {show['Title']} (Rating: {show['Rating']})")
            
    else:
        logging.error("No shows were scraped!")

except Exception as e:
    logging.error(f"An error occurred: {e}")
    driver.save_screenshot("debug_output/error_screenshot.png")
    with open("debug_output/error_page_source.html", "w", encoding="utf-8") as f:
        f.write(driver.page_source)
    logging.info("Error screenshot and page source saved for debugging")

finally:
    logging.info("Closing browser")
    driver.quit()
