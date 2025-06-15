import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.metrics.pairwise import cosine_similarity
import logging
from collections import Counter
import re
import json
from textblob import TextBlob
import warnings
warnings.filterwarnings('ignore')

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TVTasteAnalyzer:
    def __init__(self):
        self.watched_shows = None
        self.reviews = None
        self.enriched_data = None
        self.taste_profile = {}
        
    def load_data(self):
        """Load all available data files"""
        try:
            # Load enriched watched shows if available, otherwise use basic data
            try:
                self.watched_shows = pd.read_csv("data/enriched_watched_shows.csv")
                logging.info(f"Loaded {len(self.watched_shows)} enriched watched shows")
            except FileNotFoundError:
                self.watched_shows = pd.read_csv("data/final_watched_shows.csv")
                logging.info(f"Loaded {len(self.watched_shows)} basic watched shows")
            
            # Load reviews if available
            try:
                self.reviews = pd.read_csv("data/serializd_reviews.csv")
                logging.info(f"Loaded {len(self.reviews)} reviews")
            except FileNotFoundError:
                logging.warning("No reviews data found")
                self.reviews = None
                
        except Exception as e:
            logging.error(f"Error loading data: {e}")
            return False
        
        return True
    
    def analyze_genre_preferences(self):
        """Analyze genre preferences from watched shows"""
        if self.watched_shows is None or 'Genres' not in self.watched_shows.columns:
            logging.warning("No genre data available for analysis")
            return {}
        
        # Extract all genres
        all_genres = []
        for genres_str in self.watched_shows['Genres'].dropna():
            if genres_str != 'N/A':
                genres = [g.strip() for g in str(genres_str).split(',')]
                all_genres.extend(genres)
        
        if not all_genres:
            logging.warning("No valid genre data found")
            return {}
        
        # Count genre frequencies
        genre_counts = Counter(all_genres)
        total_shows = len(self.watched_shows)
        
        # Calculate genre preferences as percentages
        genre_preferences = {
            genre: {
                'count': count,
                'percentage': (count / total_shows) * 100
            }
            for genre, count in genre_counts.most_common()
        }
        
        logging.info(f"Analyzed {len(genre_preferences)} genres from {total_shows} shows")
        return genre_preferences
    
    def analyze_rating_patterns(self):
        """Analyze rating patterns from reviews"""
        if self.reviews is None or 'Rating' not in self.reviews.columns:
            logging.warning("No rating data available for analysis")
            return {}
        
        # Clean and convert ratings
        ratings = []
        for rating in self.reviews['Rating'].dropna():
            if rating != 'N/A':
                # Try to extract numeric rating
                rating_str = str(rating)
                # Look for patterns like "8.5", "4/5", "A", etc.
                if '/' in rating_str:
                    try:
                        num, denom = rating_str.split('/')
                        numeric_rating = (float(num) / float(denom)) * 10
                        ratings.append(numeric_rating)
                    except:
                        pass
                elif rating_str.replace('.', '').isdigit():
                    try:
                        numeric_rating = float(rating_str)
                        # Normalize to 0-10 scale
                        if numeric_rating <= 5:
                            numeric_rating *= 2  # Assume 0-5 scale
                        ratings.append(numeric_rating)
                    except:
                        pass
                elif rating_str in ['A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'F']:
                    # Convert letter grades to numeric
                    grade_map = {
                        'A+': 10, 'A': 9, 'A-': 8.5,
                        'B+': 8, 'B': 7, 'B-': 6.5,
                        'C+': 6, 'C': 5, 'C-': 4.5,
                        'D+': 4, 'D': 3, 'F': 1
                    }
                    ratings.append(grade_map.get(rating_str, 5))
        
        if not ratings:
            logging.warning("No valid rating data found")
            return {}
        
        rating_stats = {
            'average_rating': np.mean(ratings),
            'median_rating': np.median(ratings),
            'std_rating': np.std(ratings),
            'min_rating': min(ratings),
            'max_rating': max(ratings),
            'total_rated_shows': len(ratings),
            'rating_distribution': Counter([round(r) for r in ratings])
        }
        
        logging.info(f"Analyzed {len(ratings)} ratings with average of {rating_stats['average_rating']:.2f}")
        return rating_stats
    
    def analyze_show_characteristics(self):
        """Analyze characteristics of watched shows"""
        characteristics = {}
        
        if self.watched_shows is None:
            logging.warning("No watched shows data available for characteristic analysis")
            return characteristics

        # Analyze show lengths (seasons/episodes)
        if 'Number_of_Seasons' in self.watched_shows.columns:
            seasons = self.watched_shows['Number_of_Seasons'].replace('N/A', 0)
            seasons = pd.to_numeric(seasons, errors='coerce').fillna(0)
            valid_seasons = seasons[seasons > 0]
            
            if len(valid_seasons) > 0:
                characteristics['seasons'] = {
                    'average_seasons': valid_seasons.mean(),
                    'median_seasons': valid_seasons.median(),
                    'prefers_long_series': valid_seasons.mean() > 3,
                    'season_distribution': valid_seasons.value_counts().to_dict()
                }
        
        # Analyze show popularity and ratings
        if 'Vote_Average' in self.watched_shows.columns:
            ratings = pd.to_numeric(self.watched_shows['Vote_Average'], errors='coerce')
            valid_ratings = ratings[ratings > 0]
            
            if len(valid_ratings) > 0:
                characteristics['tmdb_ratings'] = {
                    'average_show_rating': valid_ratings.mean(),
                    'prefers_highly_rated': valid_ratings.mean() > 7.0,
                    'rating_threshold': valid_ratings.quantile(0.25)  # Bottom 25% threshold
                }
        
        # Analyze networks/platforms
        if 'Networks' in self.watched_shows.columns:
            networks = []
            for network_str in self.watched_shows['Networks'].dropna():
                if network_str != 'N/A':
                    networks.extend([n.strip() for n in str(network_str).split(',')])
            
            if networks:
                network_counts = Counter(networks)
                characteristics['networks'] = {
                    'top_networks': dict(network_counts.most_common(10)),
                    'total_networks': len(set(networks))
                }
        
        # Analyze languages
        if 'Original_Language' in self.watched_shows.columns:
            languages = self.watched_shows['Original_Language'].value_counts()
            characteristics['languages'] = {
                'primary_language': languages.index[0] if len(languages) > 0 else 'en',
                'language_diversity': len(languages),
                'language_distribution': languages.to_dict()
            }
        
        return characteristics
    
    def analyze_review_sentiment(self):
        """Analyze sentiment from review texts"""
        if self.reviews is None or 'Review_Text' not in self.reviews.columns:
            logging.warning("No review text available for sentiment analysis")
            return {}
        
        sentiments = []
        review_texts = []
        
        for review_text in self.reviews['Review_Text'].dropna():
            if review_text != 'N/A' and len(str(review_text)) > 10:
                try:
                    blob = TextBlob(str(review_text))
                    sentiment = blob.sentiment
                    sentiments.append({
                        'polarity': sentiment.polarity,  # -1 to 1
                        'subjectivity': sentiment.subjectivity  # 0 to 1
                    })
                    review_texts.append(review_text)
                except:
                    pass
        
        if not sentiments:
            logging.warning("No valid review text for sentiment analysis")
            return {}
        
        polarities = [s['polarity'] for s in sentiments]
        subjectivities = [s['subjectivity'] for s in sentiments]
        
        sentiment_analysis = {
            'average_sentiment': np.mean(polarities),
            'sentiment_std': np.std(polarities),
            'average_subjectivity': np.mean(subjectivities),
            'positive_reviews': len([p for p in polarities if p > 0.1]),
            'negative_reviews': len([p for p in polarities if p < -0.1]),
            'neutral_reviews': len([p for p in polarities if -0.1 <= p <= 0.1]),
            'total_analyzed_reviews': len(sentiments)
        }
        
        # Extract common words from positive vs negative reviews
        positive_reviews = [review_texts[i] for i, p in enumerate(polarities) if p > 0.1]
        negative_reviews = [review_texts[i] for i, p in enumerate(polarities) if p < -0.1]
        
        if positive_reviews and negative_reviews:
            # Simple word frequency analysis
            def get_common_words(texts, n=10):
                all_words = []
                for text in texts:
                    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
                    all_words.extend(words)
                return Counter(all_words).most_common(n)
            
            sentiment_analysis['positive_keywords'] = dict(get_common_words(positive_reviews))
            sentiment_analysis['negative_keywords'] = dict(get_common_words(negative_reviews))
        
        logging.info(f"Analyzed sentiment for {len(sentiments)} reviews")
        return sentiment_analysis
    
    def cluster_shows(self):
        """Cluster shows based on available features"""
        if self.watched_shows is None or 'Genres' not in self.watched_shows.columns:
            logging.warning("Cannot cluster shows without genre data")
            return {}
        
        # Prepare features for clustering
        features_df = pd.DataFrame()
        
        # Genre features (one-hot encoding)
        all_genres = set()
        for genres_str in self.watched_shows['Genres'].dropna():
            if genres_str != 'N/A':
                genres = [g.strip() for g in str(genres_str).split(',')]
                all_genres.update(genres)
        
        # Create genre columns
        for genre in all_genres:
            features_df[f'genre_{genre}'] = self.watched_shows['Genres'].apply(
                lambda x: 1 if isinstance(x, str) and genre in x else 0
            )
        
        # Add numeric features if available
        numeric_features = ['Vote_Average', 'Popularity', 'Number_of_Seasons', 'Number_of_Episodes']
        for feature in numeric_features:
            if feature in self.watched_shows.columns:
                values = pd.to_numeric(self.watched_shows[feature], errors='coerce').fillna(0)
                features_df[feature] = values
        
        if features_df.empty:
            logging.warning("No features available for clustering")
            return {}
        
        # Standardize features
        scaler = StandardScaler()
        features_scaled = scaler.fit_transform(features_df)
        
        # Perform clustering
        n_clusters = min(5, len(self.watched_shows) // 10)  # Reasonable number of clusters
        if n_clusters < 2:
            n_clusters = 2
        
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        clusters = kmeans.fit_predict(features_scaled)
        
        # Analyze clusters
        cluster_analysis = {}
        for i in range(n_clusters):
            cluster_shows = self.watched_shows[clusters == i]
            cluster_genres = []
            
            for genres_str in cluster_shows['Genres'].dropna():
                if genres_str != 'N/A':
                    cluster_genres.extend([g.strip() for g in str(genres_str).split(',')])
            
            cluster_analysis[f'cluster_{i}'] = {
                'size': len(cluster_shows),
                'shows': cluster_shows['Title'].tolist()[:10],  # First 10 shows
                'top_genres': dict(Counter(cluster_genres).most_common(5)),
                'avg_rating': cluster_shows.get('Vote_Average', pd.Series([0])).mean() if 'Vote_Average' in cluster_shows.columns else 0
            }
        
        logging.info(f"Created {n_clusters} clusters from {len(self.watched_shows)} shows")
        return cluster_analysis
    
    def generate_taste_profile(self):
        """Generate comprehensive taste profile"""
        logging.info("Generating comprehensive taste profile...")
        
        self.taste_profile = {
            'summary': {
                'total_shows_watched': len(self.watched_shows) if self.watched_shows is not None else 0,
                'total_reviews_written': len(self.reviews) if self.reviews is not None else 0,
                'analysis_date': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        }
        
        # Analyze different aspects
        self.taste_profile['genre_preferences'] = self.analyze_genre_preferences()
        self.taste_profile['rating_patterns'] = self.analyze_rating_patterns()
        self.taste_profile['show_characteristics'] = self.analyze_show_characteristics()
        self.taste_profile['sentiment_analysis'] = self.analyze_review_sentiment()
        self.taste_profile['show_clusters'] = self.cluster_shows()
        
        # Generate insights
        self.taste_profile['insights'] = self.generate_insights()
        
        return self.taste_profile
    
    def generate_insights(self):
        """Generate human-readable insights from the analysis"""
        insights = []
        
        # Genre insights
        if 'genre_preferences' in self.taste_profile and self.taste_profile['genre_preferences']:
            top_genres = list(self.taste_profile['genre_preferences'].keys())[:3]
            insights.append(f"Your top 3 favorite genres are: {', '.join(top_genres)}")
            
            top_genre_pct = self.taste_profile['genre_preferences'][top_genres[0]]['percentage']
            insights.append(f"{top_genres[0]} makes up {top_genre_pct:.1f}% of your watched shows")
        
        # Rating insights
        if 'rating_patterns' in self.taste_profile and self.taste_profile['rating_patterns']:
            avg_rating = self.taste_profile['rating_patterns'].get('average_rating', 0)
            if avg_rating > 7:
                insights.append("You tend to rate shows highly, suggesting you're selective about what you watch")
            elif avg_rating < 5:
                insights.append("You're a tough critic with generally lower ratings")
            else:
                insights.append("You have balanced rating patterns across different shows")
        
        # Show characteristics insights
        if 'show_characteristics' in self.taste_profile:
            chars = self.taste_profile['show_characteristics']
            if 'seasons' in chars and chars['seasons'].get('prefers_long_series', False):
                insights.append("You prefer longer series with multiple seasons")
            
            if 'tmdb_ratings' in chars and chars['tmdb_ratings'].get('prefers_highly_rated', False):
                insights.append("You tend to watch critically acclaimed shows")
        
        # Sentiment insights
        if 'sentiment_analysis' in self.taste_profile and self.taste_profile['sentiment_analysis']:
            sentiment = self.taste_profile['sentiment_analysis']
            avg_sentiment = sentiment.get('average_sentiment', 0)
            if avg_sentiment > 0.2:
                insights.append("Your reviews are generally positive and enthusiastic")
            elif avg_sentiment < -0.2:
                insights.append("You tend to be critical in your reviews")
            else:
                insights.append("You write balanced, objective reviews")
        
        # Cluster insights
        if 'show_clusters' in self.taste_profile and self.taste_profile['show_clusters']:
            clusters = self.taste_profile['show_clusters']
            largest_cluster = max(clusters.keys(), key=lambda k: clusters[k]['size'])
            cluster_info = clusters[largest_cluster]
            top_genre = list(cluster_info['top_genres'].keys())[0] if cluster_info['top_genres'] else 'Unknown'
            insights.append(f"Your largest viewing pattern centers around {top_genre} shows")
        
        return insights
    
    def save_analysis(self, filename="data/taste_analysis.json"):
        """Save the complete analysis to a JSON file"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.taste_profile, f, indent=2, ensure_ascii=False, default=str)
            logging.info(f"Taste analysis saved to {filename}")
        except Exception as e:
            logging.error(f"Error saving analysis: {e}")
    
    def create_visualizations(self):
        """Create visualizations of the taste analysis"""
        try:
            plt.style.use('default')
            fig, axes = plt.subplots(2, 2, figsize=(15, 12))
            fig.suptitle('Your TV Taste Analysis', fontsize=16, fontweight='bold')
            
            # Genre preferences
            if 'genre_preferences' in self.taste_profile and self.taste_profile['genre_preferences']:
                genres = list(self.taste_profile['genre_preferences'].keys())[:10]
                counts = [self.taste_profile['genre_preferences'][g]['count'] for g in genres]
                
                axes[0, 0].bar(range(len(genres)), counts)
                axes[0, 0].set_title('Top 10 Genres')
                axes[0, 0].set_xticks(range(len(genres)))
                axes[0, 0].set_xticklabels(genres, rotation=45, ha='right')
                axes[0, 0].set_ylabel('Number of Shows')
            
            # Rating distribution
            if 'rating_patterns' in self.taste_profile and self.taste_profile['rating_patterns']:
                rating_dist = self.taste_profile['rating_patterns'].get('rating_distribution', {})
                if rating_dist:
                    ratings = list(rating_dist.keys())
                    counts = list(rating_dist.values())
                    
                    axes[0, 1].bar(ratings, counts)
                    axes[0, 1].set_title('Rating Distribution')
                    axes[0, 1].set_xlabel('Rating')
                    axes[0, 1].set_ylabel('Number of Reviews')
            
            # Show clusters
            if 'show_clusters' in self.taste_profile and self.taste_profile['show_clusters']:
                cluster_sizes = [info['size'] for info in self.taste_profile['show_clusters'].values()]
                cluster_labels = list(self.taste_profile['show_clusters'].keys())
                
                axes[1, 0].pie(cluster_sizes, labels=cluster_labels, autopct='%1.1f%%')
                axes[1, 0].set_title('Show Clusters')
            
            # Sentiment analysis
            if 'sentiment_analysis' in self.taste_profile and self.taste_profile['sentiment_analysis']:
                sentiment = self.taste_profile['sentiment_analysis']
                categories = ['Positive', 'Neutral', 'Negative']
                values = [
                    sentiment.get('positive_reviews', 0),
                    sentiment.get('neutral_reviews', 0),
                    sentiment.get('negative_reviews', 0)
                ]
                
                colors = ['green', 'gray', 'red']
                axes[1, 1].bar(categories, values, color=colors, alpha=0.7)
                axes[1, 1].set_title('Review Sentiment Distribution')
                axes[1, 1].set_ylabel('Number of Reviews')
            
            plt.tight_layout()
            plt.savefig('debug_output/taste_analysis_visualization.png', dpi=300, bbox_inches='tight')
            plt.close()
            
            logging.info("Visualizations saved to debug_output/taste_analysis_visualization.png")
            
        except Exception as e:
            logging.error(f"Error creating visualizations: {e}")
    
    def print_summary(self):
        """Print a summary of the taste analysis"""
        if not self.taste_profile:
            logging.error("No taste profile generated yet!")
            return
        
        print("\n" + "="*60)
        print("🎬 YOUR TV TASTE ANALYSIS SUMMARY")
        print("="*60)
        
        # Basic stats
        summary = self.taste_profile.get('summary', {})
        print(f"📊 Total Shows Watched: {summary.get('total_shows_watched', 0)}")
        print(f"📝 Total Reviews Written: {summary.get('total_reviews_written', 0)}")
        
        # Top genres
        if 'genre_preferences' in self.taste_profile and self.taste_profile['genre_preferences']:
            print(f"\n🎭 TOP GENRES:")
            for i, (genre, data) in enumerate(list(self.taste_profile['genre_preferences'].items())[:5], 1):
                print(f"  {i}. {genre}: {data['count']} shows ({data['percentage']:.1f}%)")
        
        # Rating patterns
        if 'rating_patterns' in self.taste_profile and self.taste_profile['rating_patterns']:
            rating_data = self.taste_profile['rating_patterns']
            print(f"\n⭐ RATING PATTERNS:")
            print(f"  Average Rating: {rating_data.get('average_rating', 0):.2f}/10")
            print(f"  Total Rated Shows: {rating_data.get('total_rated_shows', 0)}")
        
        # Key insights
        if 'insights' in self.taste_profile and self.taste_profile['insights']:
            print(f"\n💡 KEY INSIGHTS:")
            for i, insight in enumerate(self.taste_profile['insights'], 1):
                print(f"  {i}. {insight}")
        
        print("\n" + "="*60)

def main():
    """Main function to run the taste analysis"""
    analyzer = TVTasteAnalyzer()
    
    # Load data
    if not analyzer.load_data():
        logging.error("Failed to load data. Please ensure you have run the scrapers first.")
        return
    
    # Generate taste profile
    taste_profile = analyzer.generate_taste_profile()
    
    # Save analysis
    analyzer.save_analysis()
    
    # Create visualizations
    analyzer.create_visualizations()
    
    # Print summary
    analyzer.print_summary()
    
    logging.info("Taste analysis complete! Check data/taste_analysis.json and debug_output/taste_analysis_visualization.png")

if __name__ == "__main__":
    main()
