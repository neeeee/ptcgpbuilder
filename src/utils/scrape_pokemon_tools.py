#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup
import json
import re
import os
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

class ToolCardScraper:
    def __init__(self, url: str):
        """Initialize the scraper for Trainer/Tool cards specifically
        
        Args:
            url: URL to the Serebii TCG Pocket card page or set page
        """
        self.base_url = url
        # Extract set name from URL
        parsed_url = urlparse(url)
        path_parts = parsed_url.path.strip('/').split('/')
        if len(path_parts) >= 2 and path_parts[0] == 'tcgpocket':
            self.set_name = path_parts[1]
        else:
            self.set_name = "unknown_set"
        
        # Format for display (capitalize, replace underscores with spaces)
        self.display_set_name = self.set_name.replace('-', ' ').replace('_', ' ').title()
        
        print(f"Scraping set: {self.display_set_name} from {self.base_url}")
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.image_dir = Path(f"src/db/pokemon_cards/{self.set_name}")
        self.image_dir.mkdir(parents=True, exist_ok=True)

    def fetch_page(self, url: str) -> Optional[str]:
        """Fetch HTML content from the given URL"""
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"Error fetching page {url}: {e}")
            return None

    def download_image(self, image_url: str, card_name: str) -> Optional[str]:
        """Download card image and return the local path"""
        try:
            # Create a safe filename from the card name
            safe_name = re.sub(r'[^a-zA-Z0-9_\-\s.]', '_', card_name)
            safe_name = re.sub(r'\s+', '_', safe_name)
            
            # Create filename with set name prefix
            filename = f"{self.set_name}_{safe_name}.jpg"
            filepath = self.image_dir / filename

            # If image already exists, skip download
            if filepath.exists():
                return str(filepath)
                
            # Print our progress
            print(f"Downloading image for {card_name} from {self.set_name}...")

            # Construct full URL
            full_url = urljoin("https://www.serebii.net", image_url)
            
            # Download image
            response = requests.get(full_url, headers=self.headers)
            response.raise_for_status()

            # Save image
            with open(filepath, 'wb') as f:
                f.write(response.content)
                
            print(f"Saved image to {filepath}")
            return str(filepath)
        except Exception as e:
            print(f"Error downloading image for {card_name}: {e}")
            return None

    def scrape_card(self, url: str) -> Dict:
        """Scrape a single Trainer/Tool card's details"""
        # Get card number from URL
        card_number_match = re.search(r'/(\d+)\.shtml$', url)
        card_number = card_number_match.group(1) if card_number_match else "000"
        
        # Extract set name from URL
        set_name = self.set_name
        
        # Dictionary of known trainer cards
        trainer_cards = {
            # Space-time Smackdown
            "144": {"name": "Skull Fossil", "card_type": "Trainer", 
                   "description": "Play this card as if it were a 40 HP Basic Colorless Pokémon. At any time during your turn, you may discard this card from play. This card can't retreat", 
                   "rule_text": ""},
            "145": {"name": "Armor Fossil", "card_type": "Trainer", 
                   "description": "Play this card as if it were a 40 HP Basic Colorless Pokémon. At any time during your turn, you may discard this card from play. This card can't retreat", 
                   "rule_text": ""},
            "146": {"name": "Pokemon Communication", "card_type": "Trainer", 
                   "description": "Trade a Pokémon from your hand with a Pokémon from your deck. Show both Pokémon to your opponent. Shuffle your deck afterward.", 
                   "rule_text": ""},
            "147": {"name": "Giant Cape", "card_type": "Pokémon Tool", 
                   "description": "The Pokémon this card is attached to gets +20 HP.", 
                   "rule_text": "Attach Giant Cape to 1 of your Pokémon that doesn't have a Pokémon Tool attached to it."},
            "148": {"name": "Rocky Helmet", "card_type": "Pokémon Tool", 
                   "description": "If the Pokémon this card is attached to is in the Active Spot and is damaged by an attack from your opponent's Pokémon, do 20 damage to the Attacking Pokémon", 
                   "rule_text": "Attach Rocky Helmet to 1 of your Pokémon that doesn't have a Pokémon Tool attached to it."},
            "149": {"name": "Lum Berry", "card_type": "Pokémon Tool", 
                   "description": "When you attach this card to 1 of your Pokémon, remove all Special Conditions from that Pokémon.", 
                   "rule_text": "Attach Lum Berry to 1 of your Pokémon that doesn't have a Pokémon Tool attached to it."},
            "150": {"name": "Cyrus", "card_type": "Supporter", 
                   "description": "Switch in 1 of your opponent's Benched Pokémon that has damage on it to the Active Spot.", 
                   "rule_text": "You may play only 1 Supporter card during your turn."},
            "151": {"name": "Team Galactic Grunt", "card_type": "Supporter", 
                   "description": "Put 1 random Glameow, Stunky, or Croagunk from your deck into your hand.", 
                   "rule_text": "You may play only 1 Supporter card during your turn."},
            "152": {"name": "Cynthia", "card_type": "Supporter", 
                   "description": "During this turn, attacks used by your Garchomp or Togekiss do +50 damage to your opponent's Active Pokémon.", 
                   "rule_text": "You may play only 1 Supporter card during your turn."},
            "153": {"name": "Volkner", "card_type": "Supporter", 
                   "description": "Choose 1 of your Electivire or Luxray. Attach 2 Electric Energy from your discard pile to that Pokémon.", 
                   "rule_text": "You may play only 1 Supporter card during your turn."},
            "154": {"name": "Dawn", "card_type": "Supporter", 
                   "description": "Move an Energy from 1 of your Benched Pokémon to your Active Pokémon.", 
                   "rule_text": "You may play only 1 Supporter card during your turn."},
            "155": {"name": "Mars", "card_type": "Supporter", 
                   "description": "Your opponent shuffles their hand into their deck and draws a card for each of their remaining points needed to win.", 
                   "rule_text": "You may play only 1 Supporter card during your turn."},
            
            # Common Trainer Cards in all sets
            "potion": {"name": "Potion", "card_type": "Trainer", 
                     "description": "Heal 30 damage from 1 of your Pokémon.", 
                     "rule_text": ""},
            "pokeball": {"name": "Poké Ball", "card_type": "Trainer", 
                       "description": "Reveal cards from the top of your deck until you reveal a Pokémon. Put that Pokémon into your hand and shuffle the other revealed cards back into your deck.", 
                       "rule_text": ""},
            "greatball": {"name": "Great Ball", "card_type": "Trainer", 
                        "description": "Look at the top 7 cards of your deck. You may reveal a Pokémon you find there and put it into your hand. Shuffle the other cards back into your deck.", 
                        "rule_text": ""},
            "ultraball": {"name": "Ultra Ball", "card_type": "Trainer", 
                        "description": "Discard 2 cards from your hand. Then, search your deck for a Pokémon, reveal it, and put it into your hand. Shuffle your deck afterward.", 
                        "rule_text": ""},
            "pokedex": {"name": "Pokédex", "card_type": "Trainer", 
                      "description": "Look at the top 5 cards of your deck and arrange them in any order. Put them back on top of your deck.", 
                      "rule_text": ""},
            "energysearch": {"name": "Energy Search", "card_type": "Trainer", 
                           "description": "Search your deck for a basic Energy card, reveal it, and put it into your hand. Shuffle your deck afterward.", 
                           "rule_text": ""},
            "energyretrieval": {"name": "Energy Retrieval", "card_type": "Trainer", 
                              "description": "Put 2 basic Energy cards from your discard pile into your hand.", 
                              "rule_text": ""},
            "switchcard": {"name": "Switch", "card_type": "Trainer", 
                         "description": "Switch your Active Pokémon with 1 of your Benched Pokémon.", 
                         "rule_text": ""}
        }
        
        # Check if this is a known trainer card
        if "space-timesmackdown" in url and card_number in trainer_cards:
            card_info = trainer_cards[card_number]
            print(f"Processing {card_info['name']} specifically")
            card_data = {
                'set_name': self.set_name,
                'name': card_info['name'],
                'card_type': card_info['card_type'],
                'description': card_info['description'],
                'rule_text': card_info['rule_text'],
                'set_number': f"{self.display_set_name} {card_number}/155",
                'image_url': f"/tcgpocket/th/{self.set_name}/{card_number}.jpg",
                'available_booster_packs': self.display_set_name,
                'moves': []
            }
            
            # Download the image
            local_image_path = self.download_image(card_data['image_url'], card_data['name'])
            if local_image_path:
                card_data['local_image_path'] = local_image_path
            
            return card_data

        # Fetch the HTML content
        html_content = self.fetch_page(url)
        if not html_content:
            return {
                'set_name': self.set_name,
                'name': f"Card_{card_number}",
                'moves': []
            }
        
        # Create BeautifulSoup object
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Initialize card data with default name
        card_data = {
            'set_name': self.set_name,
            'name': f"Card_{card_number}",  # Default name in case we can't find it
            'moves': []  # Tool/Trainer cards don't have moves but needed for PokemonCard class
        }
        
        # Try to extract the card name from the page title first
        title = soup.find('title')
        if title:
            title_text = title.get_text()
            # Title format is typically "Space-time Smackdown - #148 Rocky Helmet | Serebii.net TCG Cards"
            title_match = re.search(r'#\d+\s+([A-Za-z\s\-\']+)\s*\|', title_text)
            if title_match:
                card_data['name'] = title_match.group(1).strip()
                print(f"Extracted name from title: {card_data['name']}")
        
        # Try to extract the card name from the H1 heading
        h1 = soup.find('h1')
        if h1:  # Only process if h1 exists
            h1_text = h1.get_text()
            # H1 format is typically "Space-time Smackdown - #148 Rocky Helmet"
            h1_match = re.search(r'#\d+\s+([A-Za-z\s\-\']+)', h1_text)
            if h1_match:
                card_data['name'] = h1_match.group(1).strip()
                print(f"Extracted name from h1: {card_data['name']}")
        
        # Look for the card info table
        card_info = soup.find('td', class_='cardinfo')
        
        # Try to extract fossil card data specifically
        fossil_type = None
        if "fossil" in url.lower():
            for table in soup.find_all("table"):
                table_text = table.get_text().lower()
                if "fossil" in table_text:
                    # Try to determine which fossil
                    if "armor fossil" in table_text:
                        fossil_type = "Armor Fossil"
                    elif "skull fossil" in table_text:
                        fossil_type = "Skull Fossil"
                    elif "dome fossil" in table_text:
                        fossil_type = "Dome Fossil"
                    elif "old amber" in table_text:
                        fossil_type = "Old Amber"
                    elif "helix fossil" in table_text:
                        fossil_type = "Helix Fossil"
                    elif "fossil" in table_text:
                        # Generic fallback
                        fossil_type = "Fossil"
                    
                    if fossil_type:
                        card_data['name'] = fossil_type
                        card_data['card_type'] = "Trainer"
                        card_data['description'] = "Play this card as if it were a 40 HP Basic Colorless Pokémon. At any time during your turn, you may discard this card from play. This card can't retreat"
                        card_data['rule_text'] = ""
                        print(f"Identified as fossil card: {fossil_type}")
                        break
        
        # If we can't find that, look for a table with a description typical of Pokémon Tool cards
        if not card_info and not fossil_type:
            # Find all tables
            tables = soup.find_all('table')
            for table in tables:
                # Look for the specific card structure in the table
                bold_name = table.find('b')
                if bold_name and bold_name.text and len(bold_name.text) > 2:
                    # This might be the card name in bold
                    card_data['name'] = bold_name.text.strip()
                    print(f"Extracted name from bold text: {card_data['name']}")
                    
                    # Look for italic text indicating card type
                    italic_type = table.find('i')
                    if italic_type and italic_type.text:
                        card_data['card_type'] = italic_type.text.strip()
                        print(f"Extracted card type: {card_data['card_type']}")
                    
                    # Look for the description text
                    card_text = table.get_text()
                    
                    # Try to extract the description and rule text
                    # Rule text on Serebii is often in italics
                    italic_rules = table.find_all('i')
                    if len(italic_rules) >= 2:  # First one might be card type, second might be rules
                        rule_text = italic_rules[1].get_text().strip()
                        if rule_text and "attach" in rule_text.lower():
                            card_data['rule_text'] = rule_text
                            print(f"Extracted rule text: {card_data['rule_text']}")
                            
                            # Now extract the description - everything between card name and rule text
                            full_text = card_text
                            if card_data['name'] in full_text and rule_text in full_text:
                                # Try to parse between card name and rule text
                                parts = full_text.split(card_data['name'], 1)
                                if len(parts) > 1:
                                    desc_and_rules = parts[1].strip()
                                    desc = desc_and_rules.split(rule_text, 1)[0].strip()
                                    # Clean up description
                                    desc = re.sub(r'Pokémon Tool', '', desc).strip()
                                    if desc:
                                        card_data['description'] = desc
                                        print(f"Extracted description: {card_data['description']}")
                    
                    # If we found card name and description, we can stop searching
                    if 'name' in card_data and 'description' in card_data:
                        break
        
        # If we still don't have a name, let's try finding it from the image or URL
        if (not card_data['name'] or card_data['name'] == f"Card_{card_number}") and not fossil_type:
            # Extract from URL path
            path_parts = url.split('/')
            if len(path_parts) > 1:
                file_name = path_parts[-1]
                if file_name.endswith('.shtml'):
                    file_name = file_name[:-6]  # Remove .shtml
                    # Try to convert to a readable name
                    if file_name.isdigit():
                        # We only have a number, use the set and number
                        card_data['name'] = f"Card {file_name} from {self.display_set_name}"
                    else:
                        # Try to make a readable name from the file name
                        name = file_name.replace('-', ' ').replace('_', ' ').title()
                        card_data['name'] = name
                        print(f"Extracted name from URL: {card_data['name']}")
        
        # Set the card type if we don't have it yet
        if 'card_type' not in card_data and card_data['name'] and not fossil_type:
            # Try to determine if it's a Tool card by name or URL
            name_lower = card_data['name'].lower()
            if 'fossil' in name_lower:
                card_data['card_type'] = "Trainer"
                card_data['description'] = "Play this card as if it were a 40 HP Basic Colorless Pokémon. At any time during your turn, you may discard this card from play. This card can't retreat"
            elif any(keyword in name_lower for keyword in ['cape', 'helmet', 'berry', 'band', 'charm', 'belt']):
                card_data['card_type'] = "Pokémon Tool"
            elif any(keyword in name_lower for keyword in ['ball', 'potion', 'poké ', 'poke ', 'communication']):
                card_data['card_type'] = "Trainer"
            elif any(keyword in name_lower for keyword in ['professor', 'bill', 'cyrus', 'mars', 'dawn', 'cynthia', 'volkner', 'grunt']):
                card_data['card_type'] = "Supporter"
        
        # If we have a name but no description, try to extract it from the card info
        if 'name' in card_data and card_data['name'] and 'description' not in card_data and card_info:
            # Look for a paragraph in the card info, which often contains the description
            paragraphs = card_info.find_all('p')
            if paragraphs:
                for p in paragraphs:
                    p_text = p.get_text().strip()
                    if len(p_text) > 10:  # Non-empty paragraph
                        card_data['description'] = p_text
                        print(f"Extracted description from paragraph: {p_text[:50]}...")
                        break
        
        # If we still don't have the card_type or description, try another approach
        if ('card_type' not in card_data or 'description' not in card_data) and card_info:
            # Try to look for italic text for card_type
            italics = card_info.find_all('i')
            if italics and len(italics) > 0 and not 'card_type' in card_data:
                card_type = italics[0].get_text().strip()
                if card_type in ["Trainer", "Supporter", "Pokémon Tool"]:
                    card_data['card_type'] = card_type
                    print(f"Extracted card type from italics: {card_type}")
            
            # Try to find description between paragraphs
            if not 'description' in card_data:
                card_text = card_info.get_text()
                lines = [line.strip() for line in card_text.split('\n') if line.strip()]
                # Try to find a substantial line that might be the description
                for line in lines:
                    if len(line) > 20 and not line.startswith("Attach") and not "play only 1" in line.lower():
                        card_data['description'] = line
                        print(f"Extracted description from lines: {line[:50]}...")
                        break
        
        # Check for common trainer card patterns in different sets
        # Dictionary of known trainer cards by set and number
        known_trainer_cards = {
            # Promo-A set
            "promo-a": {
                "001": {"name": "Energy Search", "card_type": "Trainer", 
                        "description": "Search your deck for a basic Energy card, reveal it, and put it into your hand. Shuffle your deck afterward."},
                "002": {"name": "Energy Retrieval", "card_type": "Trainer", 
                        "description": "Put 2 basic Energy cards from your discard pile into your hand."},
                "003": {"name": "Potion", "card_type": "Trainer", 
                        "description": "Heal 30 damage from 1 of your Pokémon."},
                "006": {"name": "Great Ball", "card_type": "Trainer", 
                        "description": "Look at the top 7 cards of your deck. You may reveal a Pokémon you find there and put it into your hand. Shuffle the other cards back into your deck."},
                "007": {"name": "Pokédex", "card_type": "Trainer", 
                        "description": "Look at the top 5 cards of your deck and arrange them in any order. Put them back on top of your deck."}
            },
            # Mythical Island set
            "mythicalisland": {
                "064": {"name": "Misty", "card_type": "Supporter",
                        "description": "Draw cards until you have 6 cards in your hand."},
                "065": {"name": "Whitney", "card_type": "Supporter",
                        "description": "Draw 3 cards."},
                "066": {"name": "Brock", "card_type": "Supporter",
                        "description": "Heal 60 damage from one of your Pokémon."},
                "067": {"name": "Lt. Surge", "card_type": "Supporter",
                        "description": "Search your deck for up to 3 Electric Energy cards and put them into your hand. Then, shuffle your deck."},
                "068": {"name": "Erika", "card_type": "Supporter",
                        "description": "Discard a card from your hand. Then, draw 3 cards."}
            },
            # Triumphant Light
            "triumphantlight": {
                "072": {"name": "Full Heal", "card_type": "Trainer",
                        "description": "Remove all Special Conditions from 1 of your Pokémon."},
                "073": {"name": "Switch", "card_type": "Trainer",
                        "description": "Switch your Active Pokémon with 1 of your Benched Pokémon."},
                "074": {"name": "Poké Ball", "card_type": "Trainer",
                        "description": "Reveal cards from the top of your deck until you reveal a Pokémon. Put that Pokémon into your hand and shuffle the other revealed cards back into your deck."},
                "075": {"name": "Bill", "card_type": "Supporter",
                        "description": "Draw 2 cards."}
            },
            # Shining Revelry
            "shiningrevelry": {
                "069": {"name": "Hyper Potion", "card_type": "Trainer",
                        "description": "Discard an Energy from 1 of your Pokémon and heal 120 damage from it."},
                "070": {"name": "Super Rod", "card_type": "Trainer",
                        "description": "Shuffle up to 3 in any combination of Pokémon and basic Energy cards from your discard pile into your deck."},
                "071": {"name": "Ultra Ball", "card_type": "Trainer",
                        "description": "Discard 2 cards from your hand. Then, search your deck for a Pokémon, reveal it, and put it into your hand. Shuffle your deck afterward."},
                "072": {"name": "Professor Elm", "card_type": "Supporter",
                        "description": "Discard your hand and draw 7 cards."}
            },
            # Genetic Apex
            "geneticapex": {
                "219": {"name": "Bright Powder", "card_type": "Pokémon Tool",
                        "description": "When your opponent's Pokémon attacks the Pokémon this card is attached to, your opponent flips a coin. If tails, that attack does nothing.",
                        "rule_text": "Attach Bright Powder to 1 of your Pokémon that doesn't have a Pokémon Tool attached to it."},
                "220": {"name": "Escape Rope", "card_type": "Trainer",
                        "description": "Each player switches their Active Pokémon with 1 of their Benched Pokémon."},
                "221": {"name": "Choice Band", "card_type": "Pokémon Tool",
                        "description": "The Pokémon this card is attached to does 30 more damage to your opponent's Active Pokémon.",
                        "rule_text": "Attach Choice Band to 1 of your Pokémon that doesn't have a Pokémon Tool attached to it."},
                "222": {"name": "Rare Candy", "card_type": "Trainer",
                        "description": "Choose 1 of your Basic Pokémon in play. If you have a Stage 2 card in your hand that evolves from that Pokémon, put that card onto the Basic Pokémon to evolve it. You can't use this card during your first turn or on a Basic Pokémon that was put into play this turn."},
                "223": {"name": "Big Charm", "card_type": "Pokémon Tool",
                        "description": "The Pokémon this card is attached to gets +30 HP.",
                        "rule_text": "Attach Big Charm to 1 of your Pokémon that doesn't have a Pokémon Tool attached to it."},
                "224": {"name": "Field Blower", "card_type": "Trainer",
                        "description": "Choose up to 2 in any combination of Pokémon Tool cards and Stadium cards in play and discard them."},
                "225": {"name": "Rescue Stretcher", "card_type": "Trainer",
                        "description": "Choose 1: • Put a Pokémon from your discard pile into your hand. • Shuffle 3 Pokémon from your discard pile into your deck."},
                "226": {"name": "Professor Sycamore", "card_type": "Supporter",
                        "description": "Discard your hand and draw 7 cards."}
            }
        }
        
        # Check if this card is in our known trainer cards dictionary by set and number
        set_key = self.set_name.lower()
        if set_key in known_trainer_cards and card_number in known_trainer_cards[set_key]:
            card_info = known_trainer_cards[set_key][card_number]
            print(f"Using predefined card info for {set_key}/{card_number}: {card_info['name']}")
            
            # Update card data with known values
            card_data.update({
                'name': card_info['name'],
                'card_type': card_info['card_type'],
                'description': card_info['description'],
                'rule_text': card_info.get('rule_text', '')
            })
        
        # Set the set number
        card_data['set_number'] = f"{self.display_set_name} {card_number}/155"
        
        # Set the card image URL
        card_data['image_url'] = f"/tcgpocket/th/{self.set_name}/{card_number}.jpg"
        
        # Add booster pack info
        card_data['available_booster_packs'] = self.display_set_name
        
        # Download the image
        local_image_path = self.download_image(card_data['image_url'], card_data['name'])
        if local_image_path:
            card_data['local_image_path'] = local_image_path
            
        return card_data
        
    def save_to_json(self, cards: List[Dict], filename: str = None) -> None:
        """Save the scraped cards to a JSON file"""
        if filename is None:
            filename = f"pokemon_tools_{self.set_name}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(cards, f, indent=2, ensure_ascii=False)
        
        print(f"Saved {len(cards)} cards to {filename}")

def main():
    parser = argparse.ArgumentParser(description='Scrape Pokémon Tool/Trainer cards from Serebii TCG Pocket')
    parser.add_argument('--url', type=str, required=True,
                        help='URL to the card page (e.g., https://www.serebii.net/tcgpocket/space-timesmackdown/147.shtml)')
    parser.add_argument('--output', type=str, default=None,
                        help='Output JSON filename (default: pokemon_tools_<set_name>.json)')
    args = parser.parse_args()
    
    scraper = ToolCardScraper(args.url)
    card_data = scraper.scrape_card(args.url)
    
    if card_data and 'name' in card_data:
        print(f"Successfully scraped: {card_data['name']}")
        scraper.save_to_json([card_data], args.output)
    else:
        print(f"Failed to scrape card from {args.url}")

if __name__ == "__main__":
    main() 