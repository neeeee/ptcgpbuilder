import json
import sqlite3
import os
import argparse
from pathlib import Path
import sys

def import_cards_from_json(json_file: str, db_path: str, force_recreate: bool = False) -> None:
    """Import cards from JSON file into the database
    
    Args:
        json_file: Path to the JSON file with card data
        db_path: Path to the SQLite database
        force_recreate: If True, recreate the table (only use if necessary)
    """
    try:
        # Read JSON file
        with open(json_file, 'r', encoding='utf-8') as f:
            cards = json.load(f)

        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if the table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cards'")
        table_exists = cursor.fetchone() is not None

        if force_recreate:
            if table_exists:
                print("Warning: Dropping existing cards table due to --force flag")
                cursor.execute("DROP TABLE IF EXISTS cards")
                table_exists = False
        
        # Create the table if it doesn't exist
        if not table_exists:
            print("Creating cards table with the required schema")
            cursor.execute("""
            CREATE TABLE cards (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                set_name TEXT NOT NULL,
                set_number TEXT,
                hp INTEGER,
                type TEXT,
                image_path TEXT,
                weakness TEXT,
                retreat_cost TEXT,
                weakness_damage TEXT,
                available_booster_packs TEXT,
                moves TEXT
            )
            """)
            
            # Create a unique index on name + set_name to prevent duplicates
            cursor.execute("""
            CREATE UNIQUE INDEX idx_cards_name_set ON cards(name, set_name)
            """)
        else:
            print(f"Using existing cards table")

        # Prepare the insert statement with OR IGNORE to skip duplicates
        insert_stmt = """
        INSERT OR IGNORE INTO cards (
            name, set_name, set_number, hp, type, image_path, 
            weakness, retreat_cost, weakness_damage, 
            available_booster_packs, moves
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        # Insert each card
        card_count = 0
        duplicate_count = 0
        for card in cards:
            # Convert moves, weakness and retreat cost to JSON strings
            moves_json = json.dumps(card.get('moves', []))
            weakness_json = json.dumps(card.get('weakness', []))
            retreat_cost_json = json.dumps(card.get('retreat_cost', []))
            
            # Get or set default set name
            set_name = card.get('set_name', 'Shining Revelry')
            
            try:
                cursor.execute(insert_stmt, (
                    card.get('name', ''),
                    set_name,
                    card.get('set_number', ''),
                    card.get('hp'),
                    card.get('type'),
                    card.get('local_image_path'),
                    weakness_json,
                    retreat_cost_json,
                    card.get('weakness_damage'),
                    card.get('available_booster_packs', ''),
                    moves_json
                ))
                if cursor.rowcount > 0:
                    card_count += 1
                else:
                    duplicate_count += 1
            except sqlite3.IntegrityError:
                # This happens if there's a duplicate card (same name, same set)
                duplicate_count += 1
                print(f"Duplicate card skipped: {card.get('name')} in set {set_name}")

        # Commit changes and close connection
        conn.commit()
        conn.close()
        print(f"Successfully imported {card_count} cards into the database")
        if duplicate_count > 0:
            print(f"Skipped {duplicate_count} duplicate cards")

    except Exception as e:
        print(f"Error importing cards: {e}")
        import traceback
        traceback.print_exc()
        if 'conn' in locals():
            conn.close()

def parse_arguments():
    parser = argparse.ArgumentParser(description='Import Pokemon cards from JSON file to database')
    parser.add_argument('--input', type=str, default=None,
                       help='Input JSON file (default: pokemon_cards.json in the project root)')
    parser.add_argument('--db', type=str, default=None,
                       help='Database file path (default: db/pokemon_tcg.db in the project root)')
    parser.add_argument('--force', action='store_true',
                       help='Force recreate table (use only if schema changed)')
    return parser.parse_args()

def main():
    args = parse_arguments()
    
    # Get the project root directory
    project_root = Path(__file__).parent.parent
    
    # Define paths
    json_file = args.input if args.input else project_root / 'pokemon_cards.json'
    db_path = args.db if args.db else project_root / 'db' / 'pokemon_tcg.db'
    
    # Make sure the db directory exists
    db_dir = os.path.dirname(db_path)
    os.makedirs(db_dir, exist_ok=True)
    
    # Import cards
    import_cards_from_json(str(json_file), str(db_path), args.force)

if __name__ == "__main__":
    main() 