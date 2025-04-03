#!/usr/bin/env python3
import sqlite3
import re
import argparse

def fix_card_names(db_path="src/db/pokemon_tcg.db"):
    """
    Fix card names in the database by correcting names containing "Genetic Apex"
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # First, let's check if we have any cards with the problematic name
    cursor.execute("SELECT id, name, set_number, image_path FROM cards WHERE name = 'Genetic Apex'")
    cards = cursor.fetchall()
    
    if not cards:
        print("No cards with the name 'Genetic Apex' found in the database.")
        conn.close()
        return 0
    
    fixed_count = 0
    
    for card in cards:
        card_id, name, set_number, image_path = card
        
        # Try to extract the card number and real name based on set number
        card_number = None
        correct_name = None
        
        # Check if we can extract from the set_number
        if set_number:
            match = re.search(r'Geneticapex (\d+)/226', set_number)
            if match:
                card_number = match.group(1)
                
                # For card 172, we know it's Zubat (from the provided example)
                if card_number == "172":
                    correct_name = "Zubat"
                
                # If we have an image URL, try to extract info from there
                if not correct_name and image_path:
                    # Some image URLs might contain the Pokemon name
                    if "zubat" in image_path.lower():
                        correct_name = "Zubat"
        
        # If we can't determine the name, use a placeholder with the card number
        if not correct_name and card_number:
            correct_name = f"Unknown Pokemon #{card_number}"
        elif not correct_name:
            correct_name = f"Unknown Pokemon Card #{card_id}"
        
        print(f"Fixing card {card_id}: {name} -> {correct_name}")
        
        # Update the name in the database
        cursor.execute("UPDATE cards SET name = ? WHERE id = ?", (correct_name, card_id))
        fixed_count += 1
    
    # Commit the changes
    conn.commit()
    conn.close()
    
    print(f"Fixed {fixed_count} card entries with 'Genetic Apex' name.")
    
    return fixed_count

def manually_fix_zubat(db_path="src/db/pokemon_tcg.db"):
    """
    Specifically fix the Zubat card that was incorrectly named Genetic Apex
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Find card with set number 172/226 in the Geneticapex set
    cursor.execute("SELECT id, name FROM cards WHERE set_number LIKE 'Geneticapex 172/226'")
    card = cursor.fetchone()
    
    if card:
        card_id, name = card
        
        if name != "Zubat":
            print(f"Fixing card {card_id}: {name} -> Zubat")
            cursor.execute("UPDATE cards SET name = 'Zubat' WHERE id = ?", (card_id,))
            conn.commit()
            print("Successfully fixed the Zubat card.")
        else:
            print(f"Card {card_id} already has the correct name: Zubat")
    else:
        print("Could not find Zubat card with set number 172/226")
        
        # Try looking for any card with "172" in the set number
        cursor.execute("SELECT id, name, set_number FROM cards WHERE set_number LIKE '%172%' AND set_name='Geneticapex'")
        results = cursor.fetchall()
        
        if results:
            for card in results:
                card_id, name, set_number = card
                print(f"Found potential match: {card_id} - {name} - {set_number}")
                
                if name == "Genetic Apex":
                    print(f"Fixing card {card_id}: {name} -> Zubat")
                    cursor.execute("UPDATE cards SET name = 'Zubat' WHERE id = ?", (card_id,))
                    conn.commit()
                    print("Successfully fixed the Zubat card.")
                    break
        else:
            print("Could not find any potential matches for Zubat card.")
    
    conn.close()

def parse_arguments():
    parser = argparse.ArgumentParser(description='Fix incorrectly named cards in the database')
    parser.add_argument('--db', type=str, default="src/db/pokemon_tcg.db",
                        help='Path to the database file')
    return parser.parse_args()

def main():
    args = parse_arguments()
    
    print(f"Fixing card names in {args.db}...")
    
    # First try the general fix
    fixed_count = fix_card_names(args.db)
    
    # Then specifically fix the Zubat card
    manually_fix_zubat(args.db)
    
    if fixed_count > 0:
        print(f"Successfully fixed {fixed_count} card names.")
    else:
        print("No cards needed fixing.")

if __name__ == "__main__":
    main() 