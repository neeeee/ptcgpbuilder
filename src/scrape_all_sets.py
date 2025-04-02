#!/usr/bin/env python3
import subprocess
import os
import sys
import argparse
from pathlib import Path

# List of known TCG Pocket sets on Serebii
KNOWN_SETS = {
    "shiningrevelry": "Shining Revelry",
    "geneticapex": "Genetic Apex",
    "triumphantlight": "Triumphant Light",
    "spacetimesmackdown": "Space-time Smackdown",
    "mythicalisland": "Mythical Island"
}

def scrape_set(set_name, should_import=False, force_recreate=False):
    """Scrape a single set and optionally import it to the database
    
    Args:
        set_name: The set identifier used in the URL (e.g., "shiningrevelry")
        should_import: Whether to import to the database
        force_recreate: Whether to force recreate the table (only use if schema changed)
    """
    if set_name not in KNOWN_SETS:
        print(f"Unknown set: {set_name}")
        print(f"Known sets: {', '.join(KNOWN_SETS.keys())}")
        return False
    
    display_name = KNOWN_SETS[set_name]
    url = f"https://www.serebii.net/tcgpocket/{set_name}/"
    
    print(f"\n{'='*80}")
    print(f"Scraping {display_name} from {url}")
    print(f"{'='*80}\n")
    
    # Run the scraping script
    cmd = [sys.executable, "src/scrape_pokemon_cards.py", "--url", url]
    result = subprocess.run(cmd, check=False)
    
    if result.returncode != 0:
        print(f"Error scraping {display_name}")
        return False
    
    # Import to database if requested
    if should_import:
        import_cmd = [sys.executable, "src/utils/import_cards.py", "--input", f"pokemon_cards_{set_name}.json"]
        
        # Add --force flag if requested
        if force_recreate:
            import_cmd.append("--force")
            
        print(f"\nImporting {display_name} cards to database...")
        import_result = subprocess.run(import_cmd, check=False)
        
        if import_result.returncode != 0:
            print(f"Error importing {display_name} to database")
            return False
    
    return True

def parse_arguments():
    parser = argparse.ArgumentParser(description='Scrape multiple Pokemon TCG Pocket sets from Serebii')
    parser.add_argument('--sets', nargs='+', choices=list(KNOWN_SETS.keys()) + ['all'], default=['all'],
                        help='Sets to scrape (default: all)')
    parser.add_argument('--import', dest='import_db', action='store_true',
                        help='Import scraped cards to database')
    parser.add_argument('--force', action='store_true',
                        help='Force recreate database table (use only if schema changed)')
    return parser.parse_args()

def main():
    args = parse_arguments()
    
    # Determine which sets to scrape
    sets_to_scrape = list(KNOWN_SETS.keys()) if 'all' in args.sets else args.sets
    
    success_count = 0
    for set_name in sets_to_scrape:
        if scrape_set(set_name, args.import_db, args.force):
            success_count += 1
    
    print(f"\nSuccessfully scraped {success_count} out of {len(sets_to_scrape)} sets")

if __name__ == "__main__":
    main() 