import pandas as pd
import numpy as np
import sqlite3
import json
import logging
from datetime import datetime, timedelta
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler
import requests
import time
from collections import Counter, defaultdict
import os
from dotenv import load_dotenv

load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TVRecommendationSystem:
    def __init__(self, db_path="data/tv_tracking.db"):
        self.db_path = db_path
        self.tmdb_api_key = os.getenv("TMDB_API_KEY")
        self.tmdb_base_url = "https://api.themoviedb.org/3"
        self.taste_profile = None
        self.watched_shows = None
        self.init_database()
        
    def init_database(self):
        """Initialize SQLite database for tracking"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create tables
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS watch_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    season INTEGER,
                    episode INTEGER,
                    watch_date TEXT NOT NULL,
                    rating INTEGER,
                    review_text TEXT,
                    tmdb_id INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS recommendations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    tmdb_id INTEGER,
                    recommendation_score REAL,
                    reason TEXT,
                    genres TEXT,
                    vote_average REAL,
                    popularity REAL,
                    overview TEXT,
                    first_air_date TEXT,
                    status TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    watched BOOLEAN DEFAULT FALSE
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS watchlist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    tmdb_id INTEGER,
                    added_date TEXT DEFAULT CURRENT_TIMESTAMP,
                    priority INTEGER DEFAULT 5,
                    notes TEXT,
                    watched BOOLEAN DEFAULT FALSE
                )
            """)
            
            conn.commit()
            conn.close()
            logging.info("Database initialized successfully")
            
        except Exception as e:
            logging.error(f"Error initializing database: {e}")
    
    def load_taste_profile(self):
        """Load the generated taste profile"""
        try:
            with open("data/taste_analysis.json", "r", encoding="utf-8") as f:
                self.taste_profile = json.load(f)
            logging.info("Taste profile loaded successfully")
            return True
        except FileNotFoundError:
            logging.warning("No taste profile found. Please run taste_analyzer.py first.")
            return False
        except Exception as e:
            logging.error(f"Error loading taste profile: {e}")
            return False
    
    def load_watched_shows(self):
        """Load watched shows data"""
        try:
            # Try enriched data first
            try:
                self.watched_shows = pd.read_csv("data/enriched_watched_shows.csv")
            except FileNotFoundError:
                self.watched_shows = pd.read_csv("data/final_watched_shows.csv")
            
            logging.info(f"Loaded {len(self.watched_shows)} watched shows")
            return True
        except Exception as e:
            logging.error(f"Error loading watched shows: {e}")
            return False
    
    def get_tmdb_recommendations(self, limit=50):
        """Get recommendations from TMDB based on watched shows"""
        if not self.tmdb_api_key:
            logging.warning("No TMDB API key found")
            return []
        
        recommendations = []
        seen_shows = set()
        
        # Get recommendations based on watched shows with TMDB IDs
        if self.watched_shows is not None and 'TMDB_ID' in self.watched_shows.columns:
            tmdb_shows = self.watched_shows[self.watched_shows['TMDB_ID'] != 'N/A']
            
            for _, show in tmdb_shows.head(10).iterrows():  # Use top 10 shows for recommendations
                try:
                    tmdb_id = show['TMDB_ID']
                    url = f"{self.tmdb_base_url}/tv/{tmdb_id}/recommendations"
                    params = {"api_key": self.tmdb_api_key, "page": 1}
                    
                    response = requests.get(url, params=params)
                    response.raise_for_status()
                    
                    data = response.json()
                    for rec_show in data.get('results', []):
                        show_id = rec_show['id']
                        if show_id not in seen_shows:
                            seen_shows.add(show_id)
                            recommendations.append({
                                'tmdb_id': show_id,
                                'title': rec_show['name'],
                                'overview': rec_show.get('overview', ''),
                                'vote_average': rec_show.get('vote_average', 0),
                                'popularity': rec_show.get('popularity', 0),
                                'first_air_date': rec_show.get('first_air_date', ''),
                                'genre_ids': rec_show.get('genre_ids', []),
                                'reason': f"Recommended based on {show['Title']}"
                            })
                    
                    time.sleep(0.25)  # Rate limiting
                    
                except Exception as e:
                    logging.error(f"Error getting recommendations for {show.get('Title', 'Unknown')}: {e}")
                    continue
        
        # Get trending shows
        try:
            url = f"{self.tmdb_base_url}/trending/tv/week"
            params = {"api_key": self.tmdb_api_key}
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            for show in data.get('results', [])[:20]:  # Top 20 trending
                show_id = show['id']
                if show_id not in seen_shows:
                    seen_shows.add(show_id)
                    recommendations.append({
                        'tmdb_id': show_id,
                        'title': show['name'],
                        'overview': show.get('overview', ''),
                        'vote_average': show.get('vote_average', 0),
                        'popularity': show.get('popularity', 0),
                        'first_air_date': show.get('first_air_date', ''),
                        'genre_ids': show.get('genre_ids', []),
                        'reason': "Currently trending"
                    })
        
        except Exception as e:
            logging.error(f"Error getting trending shows: {e}")
        
        return recommendations[:limit]
    
    def score_recommendations(self, recommendations):
        """Score recommendations based on taste profile"""
        if not self.taste_profile:
            logging.warning("No taste profile available for scoring")
            return recommendations
        
        # Get genre preferences
        genre_prefs = self.taste_profile.get('genre_preferences', {})
        preferred_genres = set(genre_prefs.keys())
        
        # Get TMDB genre mapping
        genre_map = self.get_tmdb_genre_map()
        
        scored_recommendations = []
        
        for rec in recommendations:
            score = 0.0
            reasons = []
            
            # Genre matching (40% of score)
            rec_genres = [genre_map.get(gid, '') for gid in rec.get('genre_ids', [])]
            genre_matches = len(set(rec_genres) & preferred_genres)
            if genre_matches > 0:
                genre_score = min(genre_matches / len(preferred_genres), 1.0) * 0.4
                score += genre_score
                reasons.append(f"Matches {genre_matches} of your favorite genres")
            
            # Rating threshold (30% of score)
            vote_avg = rec.get('vote_average', 0)
            if vote_avg >= 7.0:
                rating_score = min(vote_avg / 10.0, 1.0) * 0.3
                score += rating_score
                reasons.append(f"High rating ({vote_avg}/10)")
            
            # Popularity (20% of score)
            popularity = rec.get('popularity', 0)
            if popularity > 50:  # Arbitrary threshold
                pop_score = min(popularity / 1000, 1.0) * 0.2
                score += pop_score
                reasons.append("Popular show")
            
            # Recency (10% of score)
            first_air_date = rec.get('first_air_date', '')
            if first_air_date:
                try:
                    air_date = datetime.strptime(first_air_date, '%Y-%m-%d')
                    years_old = (datetime.now() - air_date).days / 365
                    if years_old <= 5:  # Recent shows get bonus
                        recency_score = max(0, (5 - years_old) / 5) * 0.1
                        score += recency_score
                        reasons.append("Recent show")
                except:
                    pass
            
            rec['recommendation_score'] = score
            rec['score_reasons'] = reasons
            scored_recommendations.append(rec)
        
        # Sort by score
        scored_recommendations.sort(key=lambda x: x['recommendation_score'], reverse=True)
        
        return scored_recommendations
    
    def get_tmdb_genre_map(self):
        """Get TMDB genre ID to name mapping"""
        if not self.tmdb_api_key:
            return {}
        
        try:
            url = f"{self.tmdb_base_url}/genre/tv/list"
            params = {"api_key": self.tmdb_api_key}
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            return {genre['id']: genre['name'] for genre in data.get('genres', [])}
        
        except Exception as e:
            logging.error(f"Error getting genre map: {e}")
            return {}
    
    def save_recommendations(self, recommendations):
        """Save recommendations to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Clear old recommendations
            cursor.execute("DELETE FROM recommendations")
            
            # Insert new recommendations
            for rec in recommendations:
                cursor.execute("""
                    INSERT INTO recommendations 
                    (title, tmdb_id, recommendation_score, reason, genres, vote_average, 
                     popularity, overview, first_air_date, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    rec['title'],
                    rec['tmdb_id'],
                    rec['recommendation_score'],
                    rec['reason'],
                    ', '.join([str(gid) for gid in rec.get('genre_ids', [])]),
                    rec.get('vote_average', 0),
                    rec.get('popularity', 0),
                    rec.get('overview', ''),
                    rec.get('first_air_date', ''),
                    'Recommended'
                ))
            
            conn.commit()
            conn.close()
            logging.info(f"Saved {len(recommendations)} recommendations to database")
            
        except Exception as e:
            logging.error(f"Error saving recommendations: {e}")
    
    def log_watch(self, title, season=None, episode=None, rating=None, review_text=None):
        """Log a watched episode/show"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO watch_logs 
                (title, season, episode, watch_date, rating, review_text)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                title,
                season,
                episode,
                datetime.now().isoformat(),
                rating,
                review_text
            ))
            
            conn.commit()
            conn.close()
            logging.info(f"Logged watch: {title} S{season}E{episode}" if season and episode else f"Logged watch: {title}")
            
        except Exception as e:
            logging.error(f"Error logging watch: {e}")
    
    def add_to_watchlist(self, title, tmdb_id=None, priority=5, notes=None):
        """Add a show to watchlist"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO watchlist (title, tmdb_id, priority, notes)
                VALUES (?, ?, ?, ?)
            """, (title, tmdb_id, priority, notes))
            
            conn.commit()
            conn.close()
            logging.info(f"Added {title} to watchlist")
            
        except Exception as e:
            logging.error(f"Error adding to watchlist: {e}")
    
    def get_recommendations(self, limit=20):
        """Get top recommendations from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT title, recommendation_score, reason, vote_average, overview
                FROM recommendations 
                WHERE watched = FALSE
                ORDER BY recommendation_score DESC
                LIMIT ?
            """, (limit,))
            
            recommendations = cursor.fetchall()
            conn.close()
            
            return [
                {
                    'title': rec[0],
                    'score': rec[1],
                    'reason': rec[2],
                    'rating': rec[3],
                    'overview': rec[4]
                }
                for rec in recommendations
            ]
            
        except Exception as e:
            logging.error(f"Error getting recommendations: {e}")
            return []
    
    def get_watchlist(self):
        """Get current watchlist"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT title, priority, notes, added_date
                FROM watchlist 
                WHERE watched = FALSE
                ORDER BY priority DESC, added_date ASC
            """)
            
            watchlist = cursor.fetchall()
            conn.close()
            
            return [
                {
                    'title': item[0],
                    'priority': item[1],
                    'notes': item[2],
                    'added_date': item[3]
                }
                for item in watchlist
            ]
            
        except Exception as e:
            logging.error(f"Error getting watchlist: {e}")
            return []
    
    def get_watch_stats(self):
        """Get watching statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Total watches
            cursor.execute("SELECT COUNT(*) FROM watch_logs")
            total_watches = cursor.fetchone()[0]
            
            # Watches this week
            week_ago = (datetime.now() - timedelta(days=7)).isoformat()
            cursor.execute("SELECT COUNT(*) FROM watch_logs WHERE watch_date >= ?", (week_ago,))
            week_watches = cursor.fetchone()[0]
            
            # Average rating
            cursor.execute("SELECT AVG(rating) FROM watch_logs WHERE rating IS NOT NULL")
            avg_rating = cursor.fetchone()[0] or 0
            
            # Most watched shows
            cursor.execute("""
                SELECT title, COUNT(*) as watch_count 
                FROM watch_logs 
                GROUP BY title 
                ORDER BY watch_count DESC 
                LIMIT 5
            """)
            top_shows = cursor.fetchall()
            
            conn.close()
            
            return {
                'total_watches': total_watches,
                'week_watches': week_watches,
                'average_rating': round(avg_rating, 2),
                'top_shows': [{'title': show[0], 'count': show[1]} for show in top_shows]
            }
            
        except Exception as e:
            logging.error(f"Error getting watch stats: {e}")
            return {}
    
    def generate_recommendations(self):
        """Generate and save new recommendations"""
        logging.info("Generating new recommendations...")
        
        # Load required data
        if not self.load_taste_profile():
            logging.error("Cannot generate recommendations without taste profile")
            return False
        
        if not self.load_watched_shows():
            logging.error("Cannot generate recommendations without watched shows data")
            return False
        
        # Get TMDB recommendations
        tmdb_recs = self.get_tmdb_recommendations()
        
        if not tmdb_recs:
            logging.warning("No TMDB recommendations found")
            return False
        
        # Score recommendations
        scored_recs = self.score_recommendations(tmdb_recs)
        
        # Save to database
        self.save_recommendations(scored_recs)
        
        logging.info(f"Generated {len(scored_recs)} recommendations")
        return True
    
    def print_recommendations(self, limit=10):
        """Print top recommendations"""
        recommendations = self.get_recommendations(limit)
        
        if not recommendations:
            print("No recommendations available. Run generate_recommendations() first.")
            return
        
        print("\n" + "="*60)
        print("🎬 YOUR PERSONALIZED TV RECOMMENDATIONS")
        print("="*60)
        
        for i, rec in enumerate(recommendations, 1):
            print(f"\n{i}. {rec['title']}")
            print(f"   Score: {rec['score']:.2f}/1.0")
            print(f"   Rating: {rec['rating']}/10")
            print(f"   Reason: {rec['reason']}")
            if rec['overview']:
                overview = rec['overview'][:100] + "..." if len(rec['overview']) > 100 else rec['overview']
                print(f"   Overview: {overview}")
        
        print("\n" + "="*60)
    
    def print_watchlist(self):
        """Print current watchlist"""
        watchlist = self.get_watchlist()
        
        if not watchlist:
            print("Your watchlist is empty.")
            return
        
        print("\n" + "="*40)
        print("📺 YOUR WATCHLIST")
        print("="*40)
        
        for i, item in enumerate(watchlist, 1):
            print(f"\n{i}. {item['title']}")
            print(f"   Priority: {item['priority']}/10")
            if item['notes']:
                print(f"   Notes: {item['notes']}")
            print(f"   Added: {item['added_date'][:10]}")
        
        print("\n" + "="*40)
    
    def print_stats(self):
        """Print watching statistics"""
        stats = self.get_watch_stats()
        
        if not stats:
            print("No watching statistics available.")
            return
        
        print("\n" + "="*40)
        print("📊 YOUR WATCHING STATISTICS")
        print("="*40)
        
        print(f"Total Episodes/Shows Watched: {stats['total_watches']}")
        print(f"Watched This Week: {stats['week_watches']}")
        print(f"Average Rating: {stats['average_rating']}/10")
        
        if stats['top_shows']:
            print("\nMost Watched Shows:")
            for i, show in enumerate(stats['top_shows'], 1):
                print(f"  {i}. {show['title']}: {show['count']} episodes")
        
        print("\n" + "="*40)

def main():
    """Main function for CLI interface"""
    system = TVRecommendationSystem()
    
    print("🎬 TV Recommendation & Tracking System")
    print("=====================================")
    
    while True:
        print("\nOptions:")
        print("1. Generate new recommendations")
        print("2. View recommendations")
        print("3. View watchlist")
        print("4. Add to watchlist")
        print("5. Log a watch")
        print("6. View statistics")
        print("7. Exit")
        
        choice = input("\nEnter your choice (1-7): ").strip()
        
        if choice == '1':
            system.generate_recommendations()
        
        elif choice == '2':
            limit = input("How many recommendations to show? (default 10): ").strip()
            limit = int(limit) if limit.isdigit() else 10
            system.print_recommendations(limit)
        
        elif choice == '3':
            system.print_watchlist()
        
        elif choice == '4':
            title = input("Enter show title: ").strip()
            priority = input("Enter priority (1-10, default 5): ").strip()
            priority = int(priority) if priority.isdigit() and 1 <= int(priority) <= 10 else 5
            notes = input("Enter notes (optional): ").strip() or None
            system.add_to_watchlist(title, priority=priority, notes=notes)
        
        elif choice == '5':
            title = input("Enter show title: ").strip()
            season = input("Enter season (optional): ").strip()
            episode = input("Enter episode (optional): ").strip()
            rating = input("Enter rating 1-10 (optional): ").strip()
            review = input("Enter review (optional): ").strip()
            
            season = int(season) if season.isdigit() else None
            episode = int(episode) if episode.isdigit() else None
            rating = int(rating) if rating.isdigit() and 1 <= int(rating) <= 10 else None
            review = review if review else None
            
            system.log_watch(title, season, episode, rating, review)
        
        elif choice == '6':
            system.print_stats()
        
        elif choice == '7':
            print("Goodbye!")
            break
        
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()
