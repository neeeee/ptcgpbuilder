import json
import sqlite3
import os
import argparse
from pathlib import Path
import sys

def import_cards_from_json(json_file: str, db_path: str, force_recreate: bool = False) -> None:
    """Import Pokemon cards from a JSON file to a SQLite database"""
    try:
        # Load the cards from the JSON file
        with open(json_file, 'r', encoding='utf-8') as f:
            cards = json.load(f)
        
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create the table if it doesn't exist
        if force_recreate:
            print("Dropping existing cards table...")
            cursor.execute("DROP TABLE IF EXISTS cards")
            
        # Create the table with updated schema for Trainer and Tool cards
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS cards (
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
            moves TEXT,
            card_type TEXT,
            description TEXT,
            rule_text TEXT
        )
        """)
        
        # Create a unique index on name + set_name to prevent duplicates
        cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_cards_name_set ON cards(name, set_name)
        """)

        # Prepare the insert statement with OR IGNORE to skip duplicates
        insert_stmt = """
        INSERT OR IGNORE INTO cards (
            name, set_name, set_number, hp, type, image_path, 
            weakness, retreat_cost, weakness_damage, 
            available_booster_packs, moves, card_type, description, rule_text
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            set_name = card.get('set_name', 'unknown')
            
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
                    moves_json,
                    card.get('card_type', ''),
                    card.get('description', ''),
                    card.get('rule_text', '')
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
    json_file = args.input
    db_path = args.db if args.db else project_root / 'db' / 'pokemon_tcg.db'
    if not json_file:
        print("No input file provided")
        return
    
    # Make sure the db directory exists
    db_dir = os.path.dirname(db_path)
    os.makedirs(db_dir, exist_ok=True)
    
    # Import cards
    import_cards_from_json(str(json_file), str(db_path), args.force)

if __name__ == "__main__":
    main() 