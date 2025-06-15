# 🎬 Serializd TV Taste Analysis & Recommendation System

A comprehensive system to scrape your Serializd data, analyze your TV taste using AI/ML, enrich data with TMDB, and provide personalized recommendations with future tracking capabilities.

## 🎯 What This System Does

### Current Limitations Addressed
Your original Serializd data was limited:
- ❌ No ratings or reviews (despite having 394 reviews)
- ❌ No episode-level details or watch progress
- ❌ No season counts or metadata
- ❌ Only basic show titles from 480 watched shows

### What We Built
✅ **Enhanced Data Scraping**: Captures reviews, ratings, and detailed watch data  
✅ **TMDB Enrichment**: Adds comprehensive metadata (genres, cast, ratings, etc.)  
✅ **AI Taste Analysis**: Uses ML to understand your preferences and viewing patterns  
✅ **Personalized Recommendations**: Smart recommendations based on your taste profile  
✅ **Future Tracking System**: SQLite database to log future watches and maintain watchlists  

## 📁 System Components

### 1. Data Scraping
- `enhanced_reviews_scraper.py` - Scrapes your 394 reviews with ratings and sentiment
- `click_pagination_scraper.py` - Your existing scraper for watched shows (480 shows)

### 2. Data Enrichment
- `tmdb_enricher.py` - Enriches shows with TMDB metadata (genres, cast, ratings, etc.)

### 3. AI Analysis
- `taste_analyzer.py` - Analyzes your taste using ML clustering and sentiment analysis

### 4. Recommendation & Tracking
- `recommendation_system.py` - Generates personalized recommendations and tracks future watches

## 🚀 Setup Instructions

### Step 1: Install Dependencies

```bash
pip install pandas numpy scikit-learn matplotlib seaborn requests python-dotenv selenium webdriver-manager textblob
```

### Step 2: Get TMDB API Key

1. Go to [TMDB API](https://www.themoviedb.org/settings/api)
2. Create a free account and get an API key
3. Add to your `.env` file:

```env
SERIALIZD_EMAIL=your_email@example.com
SERIALIZD_PASSWORD=your_password
SERIALIZD_USERNAME=morbius
TMDB_API_KEY=your_tmdb_api_key_here
```

### Step 3: Run the Complete Pipeline

#### Option A: Run Everything Automatically
```bash
python run_complete_analysis.py
```

#### Option B: Run Step by Step

1. **Scrape Reviews** (to get your 394 reviews with ratings):
```bash
python enhanced_reviews_scraper.py
```

2. **Enrich Data with TMDB**:
```bash
python tmdb_enricher.py
```

3. **Analyze Your Taste**:
```bash
python taste_analyzer.py
```

4. **Generate Recommendations**:
```bash
python recommendation_system.py
```

## 📊 What You'll Get

### 1. Enhanced Data Files
- `serializd_reviews.csv` - Your 394 reviews with ratings and sentiment
- `enriched_watched_shows.csv` - 480 shows with TMDB metadata
- `enriched_reviews.csv` - Reviews enriched with show metadata

### 2. Taste Analysis
- `taste_analysis.json` - Comprehensive taste profile
- `taste_analysis_visualization.png` - Visual charts of your preferences

### 3. Recommendations Database
- `tv_tracking.db` - SQLite database with:
  - Personalized recommendations based on your taste
  - Watchlist management
  - Future watch logging
  - Statistics tracking

## 🎭 Taste Analysis Features

### Genre Preferences
- Identifies your top genres from 480 watched shows
- Calculates genre percentages and preferences
- Uses this for future recommendations

### Rating Patterns
- Analyzes your 394 reviews for rating patterns
- Converts various rating formats (numeric, letter grades, fractions)
- Identifies if you're a tough critic or generous rater

### Show Characteristics
- Analyzes preference for long vs short series
- Identifies if you prefer highly-rated shows
- Analyzes network/platform preferences
- Language diversity analysis

### Sentiment Analysis
- Uses TextBlob to analyze sentiment in your review texts
- Identifies positive vs negative keywords
- Determines your review writing style

### ML Clustering
- Groups your shows into viewing patterns
- Uses K-means clustering on genres and metadata
- Identifies your distinct taste clusters

## 🎯 Recommendation System Features

### Smart Scoring Algorithm
Recommendations are scored based on:
- **Genre Matching (40%)**: How well genres match your preferences
- **Rating Threshold (30%)**: Preference for highly-rated shows
- **Popularity (20%)**: Balance of popular vs niche content
- **Recency (10%)**: Preference for newer shows

### Data Sources
- **TMDB Recommendations**: Based on shows you've watched
- **Trending Shows**: Current popular content
- **Genre-based**: Shows matching your preferred genres

### Tracking Features
- **Watch Logging**: Log episodes/seasons with ratings and reviews
- **Watchlist Management**: Prioritized list of shows to watch
- **Statistics**: Track your viewing habits over time

## 📈 Usage Examples

### View Your Taste Analysis
```python
from taste_analyzer import TVTasteAnalyzer

analyzer = TVTasteAnalyzer()
analyzer.load_data()
profile = analyzer.generate_taste_profile()
analyzer.print_summary()
```

### Get Personalized Recommendations
```python
from recommendation_system import TVRecommendationSystem

system = TVRecommendationSystem()
system.generate_recommendations()
system.print_recommendations(limit=10)
```

### Log a Watch
```python
system.log_watch("Breaking Bad", season=1, episode=1, rating=9, review_text="Amazing pilot episode!")
```

### Manage Watchlist
```python
system.add_to_watchlist("The Bear", priority=8, notes="Heard great things about this")
system.print_watchlist()
```

## 🔍 Sample Analysis Output

```
🎬 YOUR TV TASTE ANALYSIS SUMMARY
============================================================
📊 Total Shows Watched: 480
📝 Total Reviews Written: 394

🎭 TOP GENRES:
  1. Drama: 156 shows (32.5%)
  2. Comedy: 98 shows (20.4%)
  3. Crime: 67 shows (14.0%)
  4. Thriller: 45 shows (9.4%)
  5. Sci-Fi: 34 shows (7.1%)

⭐ RATING PATTERNS:
  Average Rating: 7.8/10
  Total Rated Shows: 394

💡 KEY INSIGHTS:
  1. Your top 3 favorite genres are: Drama, Comedy, Crime
  2. Drama makes up 32.5% of your watched shows
  3. You tend to rate shows highly, suggesting you're selective about what you watch
  4. You prefer longer series with multiple seasons
  5. You tend to watch critically acclaimed shows
  6. Your reviews are generally positive and enthusiastic
  7. Your largest viewing pattern centers around Drama shows
```

## 🎯 Addressing Original Limitations

### ✅ Ratings & Reviews
- **Before**: No ratings despite 394 reviews
- **After**: Full sentiment analysis and rating extraction from all reviews

### ✅ Episode-Level Details
- **Before**: No episode counts or watch progress
- **After**: TMDB provides episode counts, seasons, and runtime data

### ✅ Rich Metadata
- **Before**: Only show titles
- **After**: Genres, cast, crew, networks, languages, popularity, ratings, keywords

### ✅ Historical Context
- **Before**: Limited to Jan 1, 2022+ data
- **After**: TMDB provides full show history and context

### ✅ Future Tracking
- **Before**: No way to track future watches
- **After**: Complete SQLite system for ongoing tracking

## 🔮 Future Enhancements

### Potential Additions
1. **Integration with Other Platforms**: Import from Trakt, IMDb, etc.
2. **Social Features**: Compare taste with friends
3. **Advanced ML**: Deep learning for better recommendations
4. **Web Interface**: Flask/Django web app
5. **Mobile App**: React Native or Flutter app
6. **Export Features**: Generate reports, share taste profiles

### API Integrations
- **Trakt.tv**: For historical data pre-2022
- **IMDb**: For additional ratings and reviews
- **JustWatch**: For streaming availability
- **Rotten Tomatoes**: For critic vs audience scores

## 🛠️ Technical Architecture

### Data Flow
```
Serializd Scraping → TMDB Enrichment → AI Analysis → Recommendations → Future Tracking
```

### Technologies Used
- **Scraping**: Selenium WebDriver
- **Data Processing**: Pandas, NumPy
- **Machine Learning**: Scikit-learn (K-means, TF-IDF, Cosine Similarity)
- **Sentiment Analysis**: TextBlob
- **Visualization**: Matplotlib, Seaborn
- **Database**: SQLite
- **API**: TMDB REST API

### File Structure
```
serializd-py/
├── enhanced_reviews_scraper.py    # Scrape reviews & ratings
├── tmdb_enricher.py              # Enrich with TMDB data
├── taste_analyzer.py             # AI taste analysis
├── recommendation_system.py      # Recommendations & tracking
├── click_pagination_scraper.py   # Original watched shows scraper
├── final_watched_shows.csv       # Your 480 watched shows
├── serializd_reviews.csv         # Your 394 reviews (generated)
├── enriched_watched_shows.csv    # Shows + TMDB data (generated)
├── taste_analysis.json           # Your taste profile (generated)
├── tv_tracking.db                # Future tracking database (generated)
└── .env                          # Your credentials
```

## 🎉 Getting Started

1. **Clone/Download** all the Python files
2. **Set up** your `.env` file with credentials and TMDB API key
3. **Install** dependencies: `pip install -r requirements.txt`
4. **Run** the enhanced reviews scraper: `python enhanced_reviews_scraper.py`
5. **Enrich** with TMDB: `python tmdb_enricher.py`
6. **Analyze** your taste: `python taste_analyzer.py`
7. **Generate** recommendations: `python recommendation_system.py`

Your goal of analyzing your TV taste and building a personalized recommendation system is now fully achievable with this comprehensive solution! 🎬✨
