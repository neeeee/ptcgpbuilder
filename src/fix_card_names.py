#!/usr/bin/env python3
import sqlite3
import requests
from bs4 import BeautifulSoup
import re
import os
import sys
import argparse

def get_correct_card_name(set_name, card_number):
    """
    Fetch the correct card name from Serebii for a given set and card number
    """
    url = f"https://www.serebii.net/tcgpocket/{set_name}/{card_number}.shtml"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Try to get the card name from the title (most reliable)
        title = soup.find('title')
        if title:
            title_text = title.get_text(strip=True)
            # Format: "Genetic Apex - #172 Zubat | Serebii.net TCG Cards"
            match = re.search(r'#\d+\s+([A-Za-z\s\-\']+)', title_text)
            if match:
                return match.group(1).strip()
        
        # Fallback to H1 if available
        h1 = soup.find('h1')
        if h1:
            h1_text = h1.get_text(strip=True)
            match = re.search(r'#\d+\s+([A-Za-z\s\-\']+)', h1_text)
            if match:
                return match.group(1).strip()
                
        # If we can't find the name, return None
        return None
        
    except Exception as e:
        print(f"Error fetching card name for {set_name}/{card_number}: {e}")
        return None

def extract_card_number_from_path(image_path):
    """
    Extract the card number from a file path like 'src/db/pokemon_cards/geneticapex/geneticapex_172.jpg'
    or other formats like 'src/db/pokemon_cards/geneticapex/geneticapex_Genetic_Apex.jpg'
    """
    # Try to extract a number from the file name
    match = re.search(r'/(\d+)\.jpg$', image_path)
    if match:
        return match.group(1)
    
    # If not found, extract from the URL in the database
    match = re.search(r'geneticapex/(\d+)\.jpg', image_path)
    if match:
        return match.group(1)
    
    # If we still can't find it, look for the set code
    match = re.search(r'Geneticapex (\d+)/226', image_path)
    if match:
        return match.group(1)
    
    return None

def fix_card_names(db_path="src/db/pokemon_tcg.db"):
    """
    Fix card names in the database
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all cards with the set name 'Geneticapex' where the name might be incorrect
    cursor.execute("SELECT id, name, set_name, set_number, image_path FROM cards WHERE set_name='Geneticapex'")
    cards = cursor.fetchall()
    
    fixed_count = 0
    checked_count = 0
    
    for card in cards:
        card_id, name, set_name, set_number, image_path = card
        
        checked_count += 1
        
        # Skip cards that already have a correct name (not the set name)
        if name != "Genetic Apex" and "Genetic" not in name and "Apex" not in name:
            print(f"Skipping card {card_id}: {name} - already has a valid name")
            continue
        
        # Extract the card number
        card_number = None
        
        # Try from set_number
        if set_number:
            match = re.search(r'Geneticapex (\d+)/226', set_number)
            if match:
                card_number = match.group(1)
        
        # Try from image_path if needed
        if not card_number and image_path:
            card_number = extract_card_number_from_path(image_path)
        
        if not card_number:
            print(f"Could not extract card number for card {card_id}: {name}")
            continue
        
        # Get the correct card name
        correct_name = get_correct_card_name("geneticapex", card_number)
        
        if correct_name:
            # Check if the name has 'ex' suffix in the original
            if "ex" in name.lower() and "ex" not in correct_name.lower():
                correct_name += " ex"
            
            print(f"Fixing card {card_id}: {name} -> {correct_name}")
            
            # Update the name in the database
            cursor.execute("UPDATE cards SET name = ? WHERE id = ?", (correct_name, card_id))
            fixed_count += 1
        else:
            print(f"Could not find correct name for card {card_id}: {name}")
    
    # Commit the changes
    conn.commit()
    
    print(f"\nFixed {fixed_count} out of {checked_count} cards checked.")
    
    # Close the connection
    conn.close()
    
    return fixed_count

def parse_arguments():
    parser = argparse.ArgumentParser(description='Fix card names in the database')
    parser.add_argument('--db', type=str, default="src/db/pokemon_tcg.db",
                        help='Path to the database file')
    return parser.parse_args()

def main():
    args = parse_arguments()
    
    print(f"Fixing card names in {args.db}...")
    fixed_count = fix_card_names(args.db)
    
    if fixed_count > 0:
        print(f"Successfully fixed {fixed_count} card names.")
    else:
        print("No card names needed fixing.")

if __name__ == "__main__":
    main() 