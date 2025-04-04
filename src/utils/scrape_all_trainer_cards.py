#!/usr/bin/env python3
import os
import sys
import re
import json
import time
import argparse
from pathlib import Path
from urllib.parse import urlparse

# Import the existing tool scraper for reuse
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from scrape_pokemon_tools import ToolCardScraper

class TrainerCardBatchScraper:
    def __init__(self, input_file, output_dir="trainer_cards_json", db_path=None):
        """Initialize the batch scraper
        
        Args:
            input_file: Path to the text file containing list of trainer card URLs
            output_dir: Directory to save individual JSON files
            db_path: Optional path to SQLite database for direct import
        """
        self.input_file = input_file
        self.output_dir = output_dir
        self.db_path = db_path
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # If db_path is provided, import the necessary module
        if db_path:
            sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "utils"))
            try:
                from import_cards import import_cards_from_json
                self.import_function = import_cards_from_json
            except ImportError:
                print("Warning: Could not import the cards import function. Direct database import disabled.")
                self.import_function = None
    
    def extract_urls(self):
        """Extract and validate URLs from the input file"""
        urls = []
        try:
            with open(self.input_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and line.startswith('http') and 'serebii.net/tcgpocket' in line:
                        urls.append(line)
        except Exception as e:
            print(f"Error reading input file: {e}")
        
        print(f"Found {len(urls)} URLs to process")
        return urls
    
    def process_url(self, url):
        """Process a single URL and save the card data to JSON"""
        # Parse URL to extract set and card number
        parsed_url = urlparse(url)
        path_parts = parsed_url.path.strip('/').split('/')
        
        if len(path_parts) < 3:
            print(f"Invalid URL format: {url}")
            return None
        
        set_name = path_parts[-2]
        card_number = path_parts[-1].replace('.shtml', '')
        
        # Skip if already processed
        output_file = os.path.join(self.output_dir, f"{set_name}_{card_number}.json")
        if os.path.exists(output_file):
            print(f"Card {set_name}/{card_number} already processed, skipping...")
            return output_file
        
        # Create a ToolCardScraper instance to process the URL
        scraper = ToolCardScraper(url)
        print(f"Processing card at {url}")
        
        try:
            card_data = scraper.scrape_card(url)
            
            if card_data and 'name' in card_data and card_data['name'] != f"Card_{card_number}":
                # Save the card data to a JSON file
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump([card_data], f, indent=2, ensure_ascii=False)
                
                print(f"Successfully scraped and saved card: {card_data['name']} to {output_file}")
                return output_file
            else:
                print(f"Failed to extract card data from {url}")
                return None
        except Exception as e:
            print(f"Error processing URL {url}: {e}")
            return None
    
    def import_to_db(self, json_file):
        """Import the card data from JSON to SQLite database"""
        if not self.db_path:
            return False
        
        try:
            # Use the import_cards_from_json function from the import_cards module
            try:
                # First try importing the function directly
                from utils.import_cards import import_cards_from_json
                import_cards_from_json(json_file, self.db_path)
                print(f"Successfully imported card from {json_file} to database")
                return True
            except (ImportError, ModuleNotFoundError):
                # If that fails, try running the import_cards.py script directly
                import subprocess
                cmd = [sys.executable, 
                       os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                    "utils", "import_cards.py"),
                       "--input", json_file,
                       "--db", self.db_path]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    print(f"Successfully imported card from {json_file} to database")
                    return True
                else:
                    print(f"Error running import script: {result.stderr}")
                    return False
        except Exception as e:
            print(f"Error importing card from {json_file} to database: {e}")
            return False
    
    def run(self):
        """Run the batch scraper on all URLs in the input file"""
        urls = self.extract_urls()
        
        successful = 0
        failed = 0
        skipped = 0
        
        for i, url in enumerate(urls):
            print(f"\nProcessing {i+1}/{len(urls)}: {url}")
            
            # Add a small delay to avoid rate limiting
            if i > 0:
                time.sleep(1)
            
            result = self.process_url(url)
            
            if result:
                if self.db_path:
                    if self.import_to_db(result):
                        successful += 1
                    else:
                        failed += 1
                else:
                    successful += 1
            else:
                failed += 1
        
        print(f"\nSummary:")
        print(f"Total URLs: {len(urls)}")
        print(f"Successfully processed: {successful}")
        print(f"Failed: {failed}")
        print(f"Skipped: {skipped}")

def main():
    parser = argparse.ArgumentParser(description='Batch scrape trainer cards from a list of URLs')
    parser.add_argument('--input', type=str, required=True,
                        help='Input file containing list of URLs (e.g., trainer_cards.rtf)')
    parser.add_argument('--output', type=str, default='trainer_cards_json',
                        help='Output directory for JSON files')
    parser.add_argument('--db', type=str, default=None,
                        help='Path to SQLite database for direct import')
    
    args = parser.parse_args()
    
    # If db path is not absolute, make it relative to the src directory
    db_path = args.db
    if db_path:
        if not os.path.isabs(db_path):
            # Try a few common paths to find the database
            potential_paths = [
                db_path,
                os.path.join(os.path.dirname(__file__), db_path),
                os.path.join(os.path.dirname(__file__), '..', db_path),
                os.path.join('src', db_path)
            ]
            
            for path in potential_paths:
                if os.path.exists(path) or os.path.exists(os.path.dirname(path)):
                    db_path = path
                    break
        
        print(f"Using database at path: {db_path}")
    
    # Run the batch scraper
    scraper = TrainerCardBatchScraper(args.input, args.output, db_path)
    scraper.run()

if __name__ == "__main__":
    main() 