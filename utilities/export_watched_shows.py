import json
import logging
# from serializd import SerializdClient # Commented out as 'serializd' package was deleted
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

def export_watched_shows(email: str, password: str, username: str, output_file: str = "data/watched_shows.json"):
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    # The SerializdClient was part of the deleted 'serializd' package.
    # Login functionality is currently disabled.
    # client = SerializdClient()
    # try:
    #     client.login(email=email, password=password)
    #     logging.info("Login successful")
    # except Exception as e:
    #     logging.error(f"Login failed: {e})
    #     return
    logging.warning("SerializdClient login functionality is disabled as the 'serializd' package was deleted.")
    logging.warning("Please implement an alternative login method or remove this functionality if not needed.")

    # Set up Chrome options
    options = Options()
    # options.add_argument("--headless")  # Uncomment for headless mode
    driver = webdriver.Chrome(options=options)

    try:
        watched_url = f"https://serializd.com/user/{username}/watched"
        logging.info(f"Navigating to {watched_url}")
        driver.get(watched_url)

        # Wait for show elements
        logging.info("Waiting for watched show elements")
        wait = WebDriverWait(driver, 20)
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "show-card-v2-container")))

        # Scrape watched shows
        logging.info("Scraping watched shows")
        watched_shows = []
        show_elements = driver.find_elements(By.CLASS_NAME, "show-card-v2-container")
        logging.info(f"Found {len(show_elements)} watched show elements")

        for show in show_elements:
            try:
                title = "Unknown"
                try:
                    h3_element = show.find_element(By.CSS_SELECTOR, "h3")
                    title = h3_element.text.strip()
                except Exception as e:
                    logging.error(f"Error getting title: {e}")
                    pass

                rating = "N/A"
                try:
                    rating = show.find_element(By.CSS_SELECTOR, "span[class*='rating'], [class*='rating']").text
                except:
                    pass

                watched_shows.append({"Title": title, "Status": "Watched", "Rating": rating})
                logging.info(f"Scraped watched show: {title}")
            except Exception as e:
                logging.error(f"Error scraping watched show: {e}")
                continue

        # Save watched shows to JSON
        logging.info("Saving watched shows to JSON")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(watched_shows, f, indent=4)

        logging.info(f"Scraped {len(watched_shows)} watched shows and saved to {output_file}")

    except Exception as e:
        logging.error(f"An error occurred: {e}")
    finally:
        logging.info("Closing browser")
        driver.quit()


if __name__ == "__main__":
    email = input("Enter your Serializd email: ")
    password = input("Enter your Serializd password: ")
    username = input("Enter your Serializd username: ")
    export_watched_shows(email, password, username)
