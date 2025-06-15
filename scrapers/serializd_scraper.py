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

load_dotenv()
EMAIL = os.getenv("SERIALIZD_EMAIL")
PASSWORD = os.getenv("SERIALIZD_PASSWORD")
USERNAME = os.getenv("SERIALIZD_USERNAME")

if not EMAIL or not PASSWORD or not USERNAME:
    logging.critical("Missing SERIALIZD_EMAIL, SERIALIZD_PASSWORD, or SERIALIZD_USERNAME environment variables. Please set them in your .env file.")
    exit(1)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Set up Chrome options
options = Options()
# options.add_argument("--headless")  # Uncomment for headless mode
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

SCRAPE_WATCHED_PAGE = True

try:
    logging.info("Navigating to login page")
    driver.get("https://serializd.com/login")

    # Wait for login form
    wait = WebDriverWait(driver, 20)
    logging.info("Locating email and password fields")

    # Find email and password fields
    email_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email'].form-input.form-control")))
    password_field = driver.find_element(By.CSS_SELECTOR, "input[type='password'].form-input.form-control")
    email_field.send_keys(EMAIL)
    password_field.send_keys(PASSWORD)

    # Find login button
    logging.info("Clicking login button")
    login_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']")))
    login_button.click()

    # Wait for redirect
    logging.info("Waiting for login redirect")
    time.sleep(5)

    # Navigate to homepage
    homepage_url = f"https://serializd.com/user/{USERNAME}"
    logging.info(f"Navigating to {homepage_url}")
    driver.get(homepage_url)

    # Check for 404
    if "404" in driver.title or "Not Found" in driver.page_source:
        raise Exception(f"Homepage URL {homepage_url} not found. Verify USERNAME.")

    # Save screenshot for debugging
    driver.save_screenshot("debug_output/homepage.png")
    logging.info("Saved screenshot as debug_output/homepage.png")

    # Scroll to load all content
    logging.info("Scrolling to load all homepage content")
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(5)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

    # Save page source for debugging
    with open("debug_output/homepage_source.html", "w", encoding="utf-8") as f:
        f.write(driver.page_source)
    logging.info("Saved page source as debug_output/homepage_source.html")

    # Scrape homepage sections
    logging.info("Scraping homepage data")
    homepage_data = []
    seen_entries = set()

    # Function to scrape a section
    def scrape_section(section_selector, entry_type):
        try:
            section = driver.find_element(By.CSS_SELECTOR, section_selector)
            show_elements = section.find_elements(By.CLASS_NAME, "show-card-v2-container")
            logging.info(f"Found {len(show_elements)} elements in {entry_type} section")
            for show in show_elements:
                try: # Outer try for individual show scraping
                    title = "Unknown" # Initialize title
                    try:
                        h3_element = show.find_element(By.CSS_SELECTOR, "h3")
                        title = h3_element.text.strip()
                    except Exception:
                        pass # h3 not found, try alt text

                    if not title or title == "Unknown":
                        try:
                            alt_text = show.find_element(By.CSS_SELECTOR, "img.card-img").get_attribute("alt")
                            if alt_text:
                                title = alt_text.replace("Poster for ", "").strip()
                        except Exception:
                            pass # Alt text not found, title remains "Unknown"

                    if title == "Unknown":
                        logging.warning("Could not determine title for a show, skipping.")
                        continue

                    season = "N/A"
                    try:
                        season = show.find_element(By.CLASS_NAME, "small-text").text.strip()
                    except Exception:
                        pass

                    entry_key = f"{title}_{entry_type}_{season}"
                    if entry_key in seen_entries:
                        logging.info(f"Skipping duplicate: {title} ({entry_type}, {season})")
                        continue
                    seen_entries.add(entry_key)

                    rating = "N/A"
                    try:
                        rating = show.find_element(By.CSS_SELECTOR, "span[class*='rating'], [class*='rating']").text
                    except Exception:
                        pass

                    homepage_data.append({"Title": title, "Type": entry_type, "Season": season, "Rating": rating})
                    logging.info(f"Scraped: {title} ({entry_type}, {season})")
                except Exception as e: # Catch exceptions for individual show scraping
                    logging.error(f"Error scraping {entry_type} entry: {e}")
                    continue
        except Exception as e: # Catch exceptions for section finding
            logging.error(f"Error finding {entry_type} section: {e}")
            # Do not continue here, as it would break the outer loop
        except: # Catch-all for section scraping (if no specific exception caught above)
            logging.info(f"No {entry_type} section found")


    # Scrape reviews section (update selector after inspection)
    scrape_section("div[class*='profile-reviews'], div[class*='recent-reviews']", "Review")
    scrape_section("div[class*='watching-now'], div[class*='currently-watching']", "Currently Watching")
    scrape_section("div[class*='recent-activity']", "Recent Activity")

    # Fallback: Scrape all show-card-v2-container elements
    if not homepage_data:
        logging.info("No sections found, falling back to scraping all show cards")
        show_elements = driver.find_elements(By.CLASS_NAME, "show-card-v2-container")
        logging.info(f"Found {len(show_elements)} show elements on homepage")
        for show in show_elements:
            try: # Outer try for individual show scraping
                title = "Unknown" # Initialize title
                try:
                    h3_element = show.find_element(By.CSS_SELECTOR, "h3")
                    title = h3_element.text.strip()
                except Exception:
                    pass # h3 not found, try alt text

                if not title or title == "Unknown":
                    try:
                        alt_text = show.find_element(By.CSS_SELECTOR, "img.card-img").get_attribute("alt")
                        if alt_text:
                            title = alt_text.replace("Poster for ", "").strip()
                    except Exception:
                        pass # Alt text not found, title remains "Unknown"

                if title == "Unknown":
                    logging.warning("Could not determine title for a show, skipping.")
                    continue

                season = "N/A"
                try:
                    season = show.find_element(By.CLASS_NAME, "small-text").text.strip()
                except Exception:
                    pass

                entry_type = "Unknown"
                try:
                    if show.find_element(By.CSS_SELECTOR, "a[href*='/review/']"):
                        entry_type = "Review"
                    else:
                        show_class = show.get_attribute("class")
                        if show_class and "watched" in show_class.lower():
                            entry_type = "Watched"
                        elif show_class and "watching" in show_class.lower():
                            entry_type = "Currently Watching"
                except Exception:
                    pass

                entry_key = f"{title}_{entry_type}_{season}"
                if entry_key in seen_entries:
                    logging.info(f"Skipping duplicate: {title} ({entry_type}, {season})")
                    continue
                seen_entries.add(entry_key)

                rating = "N/A"
                try:
                    rating = show.find_element(By.CSS_SELECTOR, "span[class*='rating'], [class*='rating']").text
                except Exception:
                    pass

                homepage_data.append({"Title": title, "Type": entry_type, "Season": season, "Rating": rating})
                logging.info(f"Scraped: {title} ({entry_type}, {season})")
            except Exception as e: # Catch exceptions for individual show scraping
                logging.error(f"Error scraping show: {e}")
                continue

    # Save homepage data to CSV
    logging.info("Saving homepage data to CSV")
    with open("data/serializd_homepage.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Title", "Type", "Season", "Rating"])
        writer.writeheader()
        writer.writerows(homepage_data)

    logging.info(f"Scraped {len(homepage_data)} entries from homepage and saved to data/serializd_homepage.csv")

    # Scrape Watched page
    if SCRAPE_WATCHED_PAGE:
        watched_url = f"https://serializd.com/user/{USERNAME}/watched"
        logging.info(f"Navigating to {watched_url}")
        driver.get(watched_url)

        # Wait for show elements
        logging.info("Waiting for watched show elements")
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "show-card-v2-container")))

        # Scrape watched shows across all pages
        logging.info("Scraping watched shows")
        watched_shows = []
        seen_titles = set()
        total_seasons = 0

        for page in range(1, 22):  # 21 pages
            logging.info(f"Scraping page {page}")
            show_elements = driver.find_elements(By.CLASS_NAME, "show-card-v2-container")
            logging.info(f"Found {len(show_elements)} watched show elements on page {page}")

            for show in show_elements:
                try: # Outer try for individual show scraping
                    title = "Unknown" # Initialize title
                    try:
                        h3_element = show.find_element(By.CSS_SELECTOR, "h3")
                        title = h3_element.text.strip()
                    except Exception:
                        pass # h3 not found, try alt text

                    if not title or title == "Unknown":
                        try:
                            alt_text = show.find_element(By.CSS_SELECTOR, "img.card-img").get_attribute("alt")
                            if alt_text:
                                title = alt_text.replace("Poster for ", "").strip()
                        except Exception:
                            pass # Alt text not found, title remains "Unknown"

                    if title == "Unknown":
                        logging.warning("Could not determine title for a show, skipping.")
                        continue

                    if title in seen_titles:
                        continue
                    seen_titles.add(title)

                    rating = "N/A"
                    try:
                        rating = show.find_element(By.CSS_SELECTOR, "span[class*='rating'], [class*='rating']").text
                    except Exception:
                        pass

                    # Count seasons by clicking into the show
                    seasons = 0
                    try:
                        show_link = show.find_element(By.CSS_SELECTOR, "a[href*='/show/']").get_attribute("href")
                        if show_link: # Ensure show_link is not None
                            driver.execute_script("window.open('');")
                            driver.switch_to.window(driver.window_handles[-1])
                            driver.get(show_link)
                        else:
                            logging.warning(f"Show link not found for {title}, skipping season count.")
                            continue

                        # Wait for season list
                        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[class*='season']")))
                        season_elements = driver.find_elements(By.CSS_SELECTOR, "div[class*='season']")
                        seasons = len(season_elements)
                        total_seasons += seasons

                        driver.close()
                        driver.switch_to.window(driver.window_handles[0])
                    except Exception as e:
                        logging.error(f"Error counting seasons for {title}: {e}")

                    watched_shows.append({"Title": title, "Status": "Watched", "Rating": rating, "Seasons": seasons})
                    logging.info(f"Scraped watched show: {title} (Seasons: {seasons})")
                except Exception as e: # Catch exceptions for individual show scraping
                    logging.error(f"Error scraping watched show: {e}")
                    continue

            # Go to next page
            if page < 21:
                try:
                    next_button = driver.find_element(By.CSS_SELECTOR, "a[class*='next'], button[class*='next'], [aria-label*='Next']")
                    next_button.click()
                    time.sleep(3)
                except Exception:
                    logging.info("No more pages to scrape")
                    break

        # Save watched shows to CSV
        logging.info("Saving watched shows to CSV")
        with open("data/serializd_watched_shows.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["Title", "Status", "Rating", "Seasons"])
            writer.writeheader()
            writer.writerows(watched_shows)

        logging.info(f"Scraped {len(watched_shows)} watched shows with {total_seasons} seasons and saved to data/serializd_watched_shows.csv")

except Exception as e:
    logging.error(f"An error occurred: {e}")
    driver.save_screenshot("debug_output/error_screenshot.png")
    with open("debug_output/error_page_source.html", "w", encoding="utf-8") as f:
        f.write(driver.page_source)

finally:
    logging.info("Closing browser")
    driver.quit()
