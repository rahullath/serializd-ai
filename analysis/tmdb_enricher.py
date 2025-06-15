import pandas as pd
import requests
import time
import logging
from dotenv import load_dotenv
import os
import json

load_dotenv()

# TMDB API setup - You'll need to get a free API key from https://www.themoviedb.org/settings/api
TMDB_API_KEY = os.getenv("TMDB_API_KEY")  # Add this to your .env file
TMDB_BASE_URL = "https://api.themoviedb.org/3"

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def search_show_on_tmdb(title, year=None):
    """Search for a TV show on TMDB"""
    try:
        # Clean the title for better search results
        clean_title = title.strip()
        
        # Search for the show
        search_url = f"{TMDB_BASE_URL}/search/tv"
        params = {
            "api_key": TMDB_API_KEY,
            "query": clean_title
        }
        
        if year:
            params["first_air_date_year"] = year
            
        response = requests.get(search_url, params=params)
        response.raise_for_status()
        
        search_results = response.json()
        
        if not search_results.get("results"):
            return None
            
        # Return the first (most relevant) result
        return search_results["results"][0]
        
    except Exception as e:
        logging.error(f"Error searching for {title}: {e}")
        return None

def get_show_details(tmdb_id):
    """Get detailed information about a TV show"""
    try:
        details_url = f"{TMDB_BASE_URL}/tv/{tmdb_id}"
        params = {
            "api_key": TMDB_API_KEY,
            "append_to_response": "credits,keywords,external_ids"
        }
        
        response = requests.get(details_url, params=params)
        response.raise_for_status()
        
        return response.json()
        
    except Exception as e:
        logging.error(f"Error getting details for TMDB ID {tmdb_id}: {e}")
        return None

def enrich_show_data(title, year=None):
    """Get comprehensive data for a show"""
    try:
        # Search for the show
        search_result = search_show_on_tmdb(title, year)
        if not search_result:
            return None
            
        tmdb_id = search_result["id"]
        
        # Get detailed information
        details = get_show_details(tmdb_id)
        if not details:
            return None
            
        # Extract relevant information
        enriched_data = {
            "TMDB_ID": tmdb_id,
            "TMDB_Title": details.get("name", "N/A"),
            "Original_Title": details.get("original_name", "N/A"),
            "Genres": ", ".join([genre["name"] for genre in details.get("genres", [])]),
            "Overview": details.get("overview", "N/A"),
            "First_Air_Date": details.get("first_air_date", "N/A"),
            "Last_Air_Date": details.get("last_air_date", "N/A"),
            "Status": details.get("status", "N/A"),
            "Number_of_Seasons": details.get("number_of_seasons", 0),
            "Number_of_Episodes": details.get("number_of_episodes", 0),
            "Episode_Runtime": details.get("episode_run_time", []),
            "Average_Runtime": sum(details.get("episode_run_time", [])) / len(details.get("episode_run_time", [])) if details.get("episode_run_time") else 0,
            "Networks": ", ".join([network["name"] for network in details.get("networks", [])]),
            "Production_Countries": ", ".join([country["name"] for country in details.get("production_countries", [])]),
            "Languages": ", ".join(details.get("languages", [])),
            "Original_Language": details.get("original_language", "N/A"),
            "Popularity": details.get("popularity", 0),
            "Vote_Average": details.get("vote_average", 0),
            "Vote_Count": details.get("vote_count", 0),
            "Adult": details.get("adult", False),
            "Homepage": details.get("homepage", "N/A"),
            "IMDB_ID": details.get("external_ids", {}).get("imdb_id", "N/A"),
            "Created_By": ", ".join([creator["name"] for creator in details.get("created_by", [])]),
            "Keywords": ", ".join([keyword["name"] for keyword in details.get("keywords", {}).get("results", [])]),
            "Cast": ", ".join([actor["name"] for actor in details.get("credits", {}).get("cast", [])[:10]]),  # Top 10 cast members
            "Crew": ", ".join([crew["name"] for crew in details.get("credits", {}).get("crew", []) if crew["job"] in ["Director", "Producer", "Executive Producer"]][:5])
        }
        
        return enriched_data
        
    except Exception as e:
        logging.error(f"Error enriching data for {title}: {e}")
        return None

def enrich_watched_shows():
    """Enrich the watched shows data with TMDB information"""
    
    if not TMDB_API_KEY:
        logging.error("TMDB_API_KEY not found in environment variables!")
        logging.info("Please get a free API key from https://www.themoviedb.org/settings/api")
        logging.info("Then add TMDB_API_KEY=your_key_here to your .env file")
        return
    
    # Load watched shows data
    try:
        watched_df = pd.read_csv("data/final_watched_shows.csv")
        logging.info(f"Loaded {len(watched_df)} watched shows")
    except FileNotFoundError:
        logging.error("data/final_watched_shows.csv not found! Please run the scraper first.")
        return
    
    enriched_data = []
    failed_shows = []
    
    for index, row in watched_df.iterrows():
        title = row["Title"]
        logging.info(f"Processing {int(index) + 1}/{len(watched_df)}: {title}")
        
        # Try to extract year from title if present
        year = None
        if "(" in title and ")" in title:
            try:
                year_match = title.split("(")[-1].split(")")[0]
                if year_match.isdigit() and len(year_match) == 4:
                    year = int(year_match)
                    title = title.split("(")[0].strip()  # Remove year from title for search
            except:
                pass
        
        # Get TMDB data
        tmdb_data = enrich_show_data(title, year)
        
        if tmdb_data:
            # Combine original data with TMDB data
            enriched_row = row.to_dict()
            enriched_row.update(tmdb_data)
            enriched_data.append(enriched_row)
            logging.info(f"✓ Successfully enriched: {title}")
        else:
            # Keep original data even if TMDB lookup failed
            enriched_row = row.to_dict()
            # Add empty TMDB fields
            tmdb_fields = {
                "TMDB_ID": "N/A", "TMDB_Title": "N/A", "Original_Title": "N/A",
                "Genres": "N/A", "Overview": "N/A", "First_Air_Date": "N/A",
                "Last_Air_Date": "N/A", "Status": "N/A", "Number_of_Seasons": 0,
                "Number_of_Episodes": 0, "Episode_Runtime": "N/A", "Average_Runtime": 0,
                "Networks": "N/A", "Production_Countries": "N/A", "Languages": "N/A",
                "Original_Language": "N/A", "Popularity": 0, "Vote_Average": 0,
                "Vote_Count": 0, "Adult": False, "Homepage": "N/A", "IMDB_ID": "N/A",
                "Created_By": "N/A", "Keywords": "N/A", "Cast": "N/A", "Crew": "N/A"
            }
            enriched_row.update(tmdb_fields)
            enriched_data.append(enriched_row)
            failed_shows.append(title)
            logging.warning(f"✗ Failed to enrich: {title}")
        
        # Rate limiting - TMDB allows 40 requests per 10 seconds
        time.sleep(0.25)  # 4 requests per second to be safe
        
        # Save progress every 50 shows
        if (int(index) + 1) % 50 == 0:
            temp_df = pd.DataFrame(enriched_data)
            temp_df.to_csv("data/enriched_shows_progress.csv", index=False)
            logging.info(f"Progress saved: {len(enriched_data)} shows processed")
    
    # Save final results
    if enriched_data:
        enriched_df = pd.DataFrame(enriched_data)
        
        # Convert relevant columns to numeric, coercing errors to NaN
        for col in ["Vote_Average", "Number_of_Seasons", "Number_of_Episodes"]:
            enriched_df[col] = pd.to_numeric(enriched_df[col], errors='coerce')

        # Save to CSV
        enriched_df.to_csv("data/enriched_watched_shows.csv", index=False)
        
        # Save to JSON for easier reading
        enriched_df.to_json("data/enriched_watched_shows.json", orient="records", indent=2)
        
        logging.info(f"Successfully enriched {len(enriched_data)} shows!")
        logging.info(f"Successfully matched with TMDB: {len(enriched_data) - len(failed_shows)}")
        logging.info(f"Failed to match: {len(failed_shows)}")
        
        if failed_shows:
            logging.info("Shows that couldn't be matched:")
            for show in failed_shows[:10]:  # Show first 10
                logging.info(f"  - {show}")
            if len(failed_shows) > 10:
                logging.info(f"  ... and {len(failed_shows) - 10} more")
        
        # Print some statistics
        matched_shows = enriched_df[enriched_df["TMDB_ID"] != "N/A"]
        if len(matched_shows) > 0:
            logging.info("\nEnrichment Statistics:")
            # Ensure these columns are numeric before calculating mean
            logging.info(f"Average TMDB rating: {matched_shows['Vote_Average'].mean():.2f}")
            logging.info(f"Average number of seasons: {matched_shows['Number_of_Seasons'].mean():.1f}")
            logging.info(f"Average number of episodes: {matched_shows['Number_of_Episodes'].mean():.1f}")
            
            # Top genres
            all_genres = []
            for genres_str in matched_shows["Genres"]:
                if genres_str != "N/A":
                    all_genres.extend([g.strip() for g in genres_str.split(",")])
            
            if all_genres:
                from collections import Counter
                top_genres = Counter(all_genres).most_common(10)
                logging.info("Top genres in your watched shows:")
                for genre, count in top_genres:
                    logging.info(f"  {genre}: {count} shows")
        
        logging.info("Results saved to:")
        logging.info("- data/enriched_watched_shows.csv")
        logging.info("- data/enriched_watched_shows.json")
    
    else:
        logging.error("No shows were enriched!")

def enrich_reviews():
    """Enrich the reviews data with TMDB information"""
    
    if not TMDB_API_KEY:
        logging.error("TMDB_API_KEY not found in environment variables!")
        return
    
    # Check if reviews file exists
    try:
        reviews_df = pd.read_csv("data/serializd_reviews.csv")
        logging.info(f"Loaded {len(reviews_df)} reviews")
    except FileNotFoundError:
        logging.warning("data/serializd_reviews.csv not found! Skipping reviews enrichment.")
        return
    
    enriched_reviews = []
    failed_reviews = []
    
    # Get unique shows from reviews to avoid duplicate API calls
    unique_shows = reviews_df["Title"].unique()
    show_tmdb_cache = {}
    
    for i, title in enumerate(unique_shows):
        logging.info(f"Processing show {i + 1}/{len(unique_shows)}: {title}")
        
        tmdb_data = enrich_show_data(title)
        if tmdb_data:
            show_tmdb_cache[title] = tmdb_data
            logging.info(f"✓ Cached TMDB data for: {title}")
        else:
            show_tmdb_cache[title] = None
            failed_reviews.append(title)
            logging.warning(f"✗ Failed to get TMDB data for: {title}")
        
        time.sleep(0.25)  # Rate limiting
    
    # Now enrich all reviews using the cache
    for index, row in reviews_df.iterrows():
        title = row["Title"]
        enriched_row = row.to_dict()
        
        if show_tmdb_cache.get(title):
            enriched_row.update(show_tmdb_cache[title])
        else:
            # Add empty TMDB fields
            tmdb_fields = {
                "TMDB_ID": "N/A", "TMDB_Title": "N/A", "Genres": "N/A",
                "Vote_Average": 0, "Popularity": 0, "Number_of_Seasons": 0,
                "Number_of_Episodes": 0, "Status": "N/A", "Networks": "N/A"
            }
            enriched_row.update(tmdb_fields)
        
        enriched_reviews.append(enriched_row)
    
    # Save enriched reviews
    if enriched_reviews:
        enriched_reviews_df = pd.DataFrame(enriched_reviews)
        enriched_reviews_df.to_csv("data/enriched_reviews.csv", index=False)
        enriched_reviews_df.to_json("data/enriched_reviews.json", orient="records", indent=2)
        
        logging.info(f"Successfully enriched {len(enriched_reviews)} reviews!")
        logging.info("Results saved to:")
        logging.info("- data/enriched_reviews.csv")
        logging.info("- data/enriched_reviews.json")

if __name__ == "__main__":
    logging.info("Starting TMDB enrichment process...")
    
    # Enrich watched shows
    logging.info("=== Enriching Watched Shows ===")
    enrich_watched_shows()
    
    # Enrich reviews if available
    logging.info("\n=== Enriching Reviews ===")
    enrich_reviews()
    
    logging.info("TMDB enrichment complete!")
