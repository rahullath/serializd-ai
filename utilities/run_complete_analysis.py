#!/usr/bin/env python3
"""
Complete TV Taste Analysis Pipeline
Runs the entire analysis from scraping to recommendations
"""

import os
import sys
import logging
import subprocess
import time
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('analysis_pipeline.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

def check_dependencies():
    """Check if all required dependencies are installed"""
    # Map package names to their import names
    package_imports = {
        'pandas': 'pandas',
        'numpy': 'numpy', 
        'scikit-learn': 'sklearn',
        'matplotlib': 'matplotlib',
        'seaborn': 'seaborn',
        'requests': 'requests',
        'python-dotenv': 'dotenv',
        'selenium': 'selenium',
        'webdriver-manager': 'webdriver_manager',
        'textblob': 'textblob'
    }
    
    missing_packages = []
    for package_name, import_name in package_imports.items():
        try:
            __import__(import_name)
        except ImportError:
            missing_packages.append(package_name)
    
    if missing_packages:
        logging.error(f"Missing required packages: {', '.join(missing_packages)}")
        logging.info("Install them with: pip install " + " ".join(missing_packages))
        return False
    
    logging.info("All required dependencies are installed")
    return True

def check_env_file():
    """Check if .env file exists and has required variables"""
    env_path = Path('.env')
    if not env_path.exists():
        logging.error(".env file not found!")
        logging.info("Please create a .env file with your credentials:")
        logging.info("SERIALIZD_EMAIL=your_email@example.com")
        logging.info("SERIALIZD_PASSWORD=your_password")
        logging.info("SERIALIZD_USERNAME=morbius")
        logging.info("TMDB_API_KEY=your_tmdb_api_key")
        return False
    
    # Load and check env variables
    from dotenv import load_dotenv
    load_dotenv()
    
    required_vars = ['SERIALIZD_EMAIL', 'SERIALIZD_PASSWORD', 'SERIALIZD_USERNAME']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logging.error(f"Missing environment variables: {', '.join(missing_vars)}")
        return False
    
    if not os.getenv('TMDB_API_KEY'):
        logging.warning("TMDB_API_KEY not found - TMDB enrichment will be skipped")
    
    logging.info("Environment configuration looks good")
    return True

def run_script(script_name, description, required=True):
    """Run a Python script and handle errors"""
    script_path = Path(script_name)
    
    if not script_path.exists():
        if required:
            logging.error(f"Required script {script_name} not found!")
            return False
        else:
            logging.warning(f"Optional script {script_name} not found, skipping")
            return True
    
    logging.info(f"Starting: {description}")
    logging.info(f"Running: {script_name}")
    
    try:
        # Run the script
        result = subprocess.run([sys.executable, script_name], 
                              capture_output=True, text=True, timeout=3600)  # 1 hour timeout
        
        if result.returncode == 0:
            logging.info(f"✅ Successfully completed: {description}")
            if result.stdout:
                logging.info(f"Output: {result.stdout[-500:]}")  # Last 500 chars
            return True
        else:
            logging.error(f"❌ Failed: {description}")
            logging.error(f"Error: {result.stderr}")
            if not required:
                logging.info("Continuing with pipeline as this step is optional")
                return True
            return False
            
    except subprocess.TimeoutExpired:
        logging.error(f"❌ Timeout: {description} took too long")
        return False
    except Exception as e:
        logging.error(f"❌ Error running {script_name}: {e}")
        return False

def check_existing_data():
    """Check what data files already exist"""
    files_to_check = {
        'final_watched_shows.csv': 'Watched shows data',
        'serializd_reviews.csv': 'Reviews data',
        'enriched_watched_shows.csv': 'TMDB enriched shows',
        'taste_analysis.json': 'Taste analysis',
        'tv_tracking.db': 'Recommendations database'
    }
    
    existing_files = []
    missing_files = []
    
    for filename, description in files_to_check.items():
        if Path(filename).exists():
            existing_files.append(f"✅ {description} ({filename})")
        else:
            missing_files.append(f"❌ {description} ({filename})")
    
    if existing_files:
        logging.info("Existing data files:")
        for file_info in existing_files:
            logging.info(f"  {file_info}")
    
    if missing_files:
        logging.info("Missing data files:")
        for file_info in missing_files:
            logging.info(f"  {file_info}")
    
    return len(existing_files), len(missing_files)

def main():
    """Main pipeline execution"""
    print("🎬 TV Taste Analysis & Recommendation System")
    print("=" * 50)
    
    # Check prerequisites
    logging.info("Checking prerequisites...")
    
    if not check_dependencies():
        logging.error("Please install missing dependencies first")
        return False
    
    if not check_env_file():
        logging.error("Please set up your .env file first")
        return False
    
    # Check existing data
    logging.info("Checking existing data files...")
    existing_count, missing_count = check_existing_data()
    
    # Ask user what to do
    if existing_count > 0:
        print(f"\nFound {existing_count} existing data files.")
        choice = input("Do you want to (r)un full pipeline, (s)kip existing steps, or (q)uit? [r/s/q]: ").lower().strip()
        
        if choice == 'q':
            logging.info("User chose to quit")
            return True
        elif choice == 's':
            skip_existing = True
        else:
            skip_existing = False
    else:
        skip_existing = False
    
    # Pipeline steps
    steps = [
        {
            'script': 'enhanced_reviews_scraper.py',
            'description': 'Scraping reviews and ratings from Serializd',
            'output_file': 'serializd_reviews.csv',
            'required': False  # Optional if user doesn't want reviews
        },
        {
            'script': 'tmdb_enricher.py',
            'description': 'Enriching data with TMDB metadata',
            'output_file': 'enriched_watched_shows.csv',
            'required': False  # Optional if no TMDB API key
        },
        {
            'script': 'taste_analyzer.py',
            'description': 'Analyzing your TV taste using AI/ML',
            'output_file': 'taste_analysis.json',
            'required': True
        },
        {
            'script': 'recommendation_system.py',
            'description': 'Generating personalized recommendations',
            'output_file': 'tv_tracking.db',
            'required': True
        }
    ]
    
    # Execute pipeline
    logging.info("Starting TV taste analysis pipeline...")
    start_time = time.time()
    
    for i, step in enumerate(steps, 1):
        step_start = time.time()
        
        # Skip if file exists and user chose to skip
        if skip_existing and Path(step['output_file']).exists():
            logging.info(f"⏭️  Skipping step {i}: {step['description']} (file exists)")
            continue
        
        logging.info(f"📍 Step {i}/{len(steps)}: {step['description']}")
        
        success = run_script(step['script'], step['description'], step['required'])
        
        step_time = time.time() - step_start
        logging.info(f"Step {i} completed in {step_time:.1f} seconds")
        
        if not success and step['required']:
            logging.error("Pipeline failed on required step")
            return False
        
        # Small delay between steps
        time.sleep(1)
    
    # Pipeline completed
    total_time = time.time() - start_time
    logging.info(f"🎉 Pipeline completed successfully in {total_time:.1f} seconds!")
    
    # Show final results
    print("\n" + "=" * 50)
    print("🎬 ANALYSIS COMPLETE!")
    print("=" * 50)
    
    final_files = {
        'serializd_reviews.csv': 'Your reviews with ratings and sentiment',
        'enriched_watched_shows.csv': 'Shows enriched with TMDB metadata',
        'taste_analysis.json': 'Your comprehensive taste profile',
        'taste_analysis_visualization.png': 'Visual charts of your preferences',
        'tv_tracking.db': 'Recommendations and tracking database'
    }
    
    print("\nGenerated files:")
    for filename, description in final_files.items():
        if Path(filename).exists():
            file_size = Path(filename).stat().st_size
            print(f"✅ {filename} ({file_size:,} bytes) - {description}")
        else:
            print(f"❌ {filename} - {description}")
    
    print("\nNext steps:")
    print("1. Check taste_analysis.json for your taste profile")
    print("2. View taste_analysis_visualization.png for visual charts")
    print("3. Run 'python recommendation_system.py' for interactive recommendations")
    print("4. Use the SQLite database (tv_tracking.db) to track future watches")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        if success:
            sys.exit(0)
        else:
            sys.exit(1)
    except KeyboardInterrupt:
        logging.info("Pipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        sys.exit(1)
