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

class PokemonCardScraper:
    def __init__(self, url: str):
        """Initialize the scraper with a URL to a Serebii TCG Pocket set page
        
        Args:
            url: URL to the Serebii TCG Pocket set page, should be in the format
                https://www.serebii.net/tcgpocket/setname/
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
        self.type_image_dir = Path("src/db/pokemon_cards/types")
        self.image_dir.mkdir(parents=True, exist_ok=True)
        self.type_image_dir.mkdir(parents=True, exist_ok=True)

    def fetch_page(self, url: str) -> Optional[str]:
        """Fetch HTML content from the given URL"""
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"Error fetching page {url}: {e}")
            return None

    def download_image(self, image_url: str, card_name: str, set_name: str = None) -> Optional[str]:
        """Download card image and return the local path
        
        Args:
            image_url: URL of the image to download
            card_name: Name of the card
            set_name: Name of the set (defaults to class's set_name)
        
        Returns:
            Path to the downloaded image or None if download failed
        """
        try:
            # Use provided set_name or default to class's set_name
            set_name = set_name or self.set_name
            
            # Create a safe filename from the card name and set name
            # Use a more precise regex to preserve "ex" and other special identifiers
            # Replace only characters that are invalid in filenames
            safe_name = re.sub(r'[^a-zA-Z0-9_\-\s.]', '_', card_name)
            # Then replace spaces with underscores
            safe_name = re.sub(r'\s+', '_', safe_name)
            
            safe_set = re.sub(r'[^a-zA-Z0-9_\-\s.]', '_', set_name)
            safe_set = re.sub(r'\s+', '_', safe_set)
            
            filename = f"{safe_set}_{safe_name}.jpg"
            filepath = self.image_dir / filename

            # If image already exists, skip download
            if filepath.exists():
                return str(filepath)
                
            # Print our progress
            print(f"Downloading image for {card_name} from {set_name}...")

            # Construct full URL
            full_url = urljoin(self.base_url, image_url)
            
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

    def download_type_image(self, image_url: str, type_name: str) -> Optional[str]:
        """Download type image and return the local path"""
        try:
            # Create a safe filename from the type name
            safe_name = re.sub(r'[^\w\-_.]', '_', type_name)
            filename = f"{safe_name}.png"
            filepath = self.type_image_dir / filename

            # If image already exists, skip download
            if filepath.exists():
                return str(filepath)

            # Construct full URL
            full_url = urljoin(self.base_url, image_url)
            
            # Download image
            response = requests.get(full_url, headers=self.headers)
            response.raise_for_status()

            # Save image
            with open(filepath, 'wb') as f:
                f.write(response.content)

            return str(filepath)
        except Exception as e:
            print(f"Error downloading type image for {type_name}: {e}")
            return None

    def get_type_from_image_url(self, image_url: str) -> str:
        """Extract type name from image URL"""
        # Example URL: /tcgpocket/image/colorless.png
        match = re.search(r'/image/([^.]+)\.png$', image_url)
        if match:
            return match.group(1)
        return ""

    def extract_card_links(self, html_content: str) -> List[Tuple[str, str]]:
        """Extract links to individual card pages from the main page"""
        soup = BeautifulSoup(html_content, 'html.parser')
        card_links = []
        
        # Find all card links in the main table
        for link in soup.find_all('a', href=re.compile(rf'/tcgpocket/{self.set_name}/\d+\.shtml')):
            # Get the card URL
            card_url = link['href']
            
            # Get the card image URL (from the image in the same cell)
            img_tag = None
            if link.find('img'):
                img_tag = link.find('img')
            else:
                # If the link doesn't contain an image, look for an image in a nearby cell
                parent_td = link.find_parent('td')
                if parent_td:
                    parent_tr = parent_td.find_parent('tr')
                    if parent_tr:
                        img_td = parent_tr.find('td', class_='cen', width='142')
                        if img_td and img_td.find('a') and img_td.find('a').find('img'):
                            img_tag = img_td.find('a').find('img')
            
            # If we found an image, store both the card URL and image URL
            if img_tag and 'src' in img_tag.attrs:
                image_url = img_tag['src']
                card_links.append((card_url, image_url))
        
        return card_links

    def parse_card_details_page(self, html_content: str, image_url: str) -> Dict:
        """Parse the individual card details page"""
        soup = BeautifulSoup(html_content, 'html.parser')
        card_data = {}
        
        # Set information (from the class's set name)
        card_data['set_name'] = self.set_name
        
        # Find the card info table
        card_info_td = soup.find('td', class_='cardinfo')
        if not card_info_td:
            print("Card info table not found")
            return card_data
        
        # Extract card name - look for the main title which includes both name and potential "ex" suffix
        try:
            # Find the card name from the page URL or card number
            # Serebii cards follow a pattern where the URL is pokemon name, not set name
            current_url = soup.find('link', rel='canonical')['href'] if soup.find('link', rel='canonical') else ""
            card_number_match = re.search(r'/(\d+)\.shtml$', current_url)
            
            # Extract Pokémon name from the main heading
            card_title = None
            
            # Try to get the Pokémon name from the title section - this is reliable for most cards
            h1_title = soup.find('h1')
            if h1_title:
                h1_text = h1_title.get_text(strip=True)
                # Extract pattern like "#172 Zubat" from the heading
                card_name_match = re.search(r'#\d+\s+([A-Za-z\s\-\']+)', h1_text)
                if card_name_match:
                    card_title = card_name_match.group(1).strip()
            
            # If we didn't get a name from H1, try the first table row
            if not card_title:
                first_row = card_info_td.find('tr')
                if first_row:
                    card_name_cell = first_row.find('td', class_='main')
                    if card_name_cell:
                        # Check if the text contains the set name - that would be wrong
                        cell_text = card_name_cell.get_text(strip=True)
                        if cell_text != self.display_set_name:
                            card_title = cell_text
            
            # If we found a card title, use it
            if card_title:
                card_data['name'] = card_title
            else:
                # Default to using the text in the card_name_cell, but double-check it's not the set name
                name_td = card_info_td.find('td', class_='main')
                if name_td:
                    potential_name = name_td.get_text(strip=True)
                    # Only use if it's not the set name
                    if potential_name != self.display_set_name:
                        card_data['name'] = potential_name
                    # If it is the set name, we need to extract the real name from somewhere else
                    else:
                        # Try to get the real Pokémon name from the title tag or other parts of the page
                        title_tag = soup.find('title')
                        if title_tag:
                            title_text = title_tag.get_text(strip=True)
                            # Title format: "Genetic Apex - #172 Zubat | Serebii.net TCG Cards"
                            name_match = re.search(r'#\d+\s+([A-Za-z\s\-\']+)', title_text)
                            if name_match:
                                card_data['name'] = name_match.group(1).strip()
                
            # Check if name is missing or is the same as set name (common error)
            if 'name' not in card_data or card_data['name'] == self.display_set_name:
                # Look at the URL path to get the card number
                if card_number_match:
                    card_number = card_number_match.group(1)
                    # Try to extract from title or other parts of the page
                    title_tag = soup.find('title')
                    if title_tag:
                        title_text = title_tag.get_text(strip=True)
                        # Title format: "Genetic Apex - #172 Zubat | Serebii.net TCG Cards"
                        name_match = re.search(r'#\d+\s+([A-Za-z\s\-\']+)', title_text)
                        if name_match:
                            card_data['name'] = name_match.group(1).strip()
                        else:
                            # If we can't find it, just mark it as "Unknown Pokémon #X"
                            card_data['name'] = f"Unknown Pokemon {card_number}"
            
            # Check for "ex" suffix which might be found separately
            if 'name' in card_data and 'ex' not in card_data['name'].lower():
                ex_text = soup.find(string=lambda text: text and text.strip().lower() == 'ex')
                if ex_text:
                    card_data['name'] += " ex"
                    
        except Exception as e:
            print(f"Error extracting card name: {e}")
            # In case of error, set a fallback name
            if 'name' not in card_data:
                card_data['name'] = "Unknown Card"
        
        # Extract HP and type
        hp_td = card_info_td.find('td', align='right')
        if hp_td:
            hp_match = re.search(r'(\d+)\s*HP', hp_td.get_text(strip=True))
            if hp_match:
                card_data['hp'] = int(hp_match.group(1))
        
        # Find Pokemon type (image after HP)
        type_td = card_info_td.find('td', align='center', width='20')
        if type_td and type_td.find('img'):
            type_img = type_td.find('img')
            if type_img and 'src' in type_img.attrs and type_img['src'].endswith('.png'):
                type_name = self.get_type_from_image_url(type_img['src'])
                if type_name:
                    card_data['type'] = type_name
                    self.download_type_image(type_img['src'], type_name)
        
        # Find moves
        moves = []
        move_rows = card_info_td.find_all('tr')
        for row in move_rows:
            # Look for rows that have a move name (bold text in a span with class 'main')
            move_span = row.find('span', class_='main')
            if move_span and move_span.find('b'):
                move_name = move_span.find('b').get_text(strip=True)
                
                # Find move cost (energy type images)
                energy_td = row.find('td', align='center', width='15%')
                energy_cost = []
                if energy_td:
                    energy_imgs = energy_td.find_all('img')
                    for img in energy_imgs:
                        if 'src' in img.attrs and 'alt' in img.attrs:
                            energy_type = img['alt'].lower()
                            energy_cost.append(energy_type)
                
                # Find move description (text after the move name)
                move_description = ""
                if move_span.parent:
                    # Get text content after the name
                    description_text = move_span.parent.get_text()
                    # Remove the move name
                    description_text = description_text.replace(move_name, '', 1)
                    move_description = description_text.strip()
                
                # Find damage
                damage = ""
                damage_td = row.find('td', colspan='2', align='center', class_='main')
                if damage_td and damage_td.find('b'):
                    damage = damage_td.find('b').get_text(strip=True)
                
                moves.append({
                    'name': move_name,
                    'energy_cost': energy_cost,
                    'description': move_description,
                    'damage': damage
                })
        
        card_data['moves'] = moves
        
        # Find weakness and retreat cost
        weakness_td = card_info_td.find('td', string=re.compile('Weakness'))
        if weakness_td:
            weakness_cell = weakness_td.find_next_sibling('td')
            if weakness_cell:
                weakness_img = weakness_cell.find('img')
                if weakness_img and 'src' in weakness_img.attrs:
                    type_name = self.get_type_from_image_url(weakness_img['src'])
                    if type_name:
                        card_data['weakness'] = [type_name]
                        self.download_type_image(weakness_img['src'], type_name)
                
                # Extract damage modifier
                damage_text = weakness_cell.get_text(strip=True)
                damage_match = re.search(r'(\+\d+)', damage_text)
                if damage_match:
                    card_data['weakness_damage'] = damage_match.group(1)
        
        retreat_td = card_info_td.find('td', string=re.compile('Retreat Cost'))
        if retreat_td:
            retreat_cell = retreat_td.find_next_sibling('td')
            if retreat_cell:
                retreat_cost = []
                retreat_imgs = retreat_cell.find_all('img')
                for img in retreat_imgs:
                    if 'src' in img.attrs:
                        type_name = self.get_type_from_image_url(img['src'])
                        if type_name:
                            retreat_cost.append(type_name)
                            self.download_type_image(img['src'], type_name)
                card_data['retreat_cost'] = retreat_cost
        
        # Find set number - fix the NoneType error by checking for the presence of next sibling
        # and using more robust selectors to find the set information
        set_number = ""
        # Look for any table that contains the set number info (usually follows the card info table)
        tables = soup.find_all('table')
        for table in tables:
            # Check for tables with a cell containing "of" which indicates set number (e.g., "1 of 72")
            set_cell = table.find('td', string=re.compile(r'\d+\s+of\s+\d+'))
            if set_cell:
                set_text = set_cell.get_text(strip=True)
                match = re.search(r'(\d+)\s*of\s*(\d+)', set_text)
                if match:
                    set_number = f"{self.display_set_name} {match.group(1)}/{match.group(2)}"
                    break
        
        if set_number:
            card_data['set_number'] = set_number
        else:
            # Fallback to a default set number pattern if we couldn't find it
            card_data['set_number'] = self.display_set_name
        
        # Find artist - also using a more robust approach
        artist = ""
        for table in tables:
            artist_cell = table.find('td', string=re.compile('Illustration'))
            if artist_cell:
                artist_link = artist_cell.find('a')
                if artist_link:
                    artist = artist_link.get_text(strip=True)
                    break
        
        if artist:
            card_data['artist'] = artist
        
        # Add image URL and booster pack info
        card_data['image_url'] = image_url
        card_data['available_booster_packs'] = self.display_set_name
        
        return card_data

    def scrape_cards(self) -> List[Dict]:
        """Scrape Pokemon cards by following links from the main page to individual card pages"""
        html_content = self.fetch_page(self.base_url)
        if not html_content:
            return []
        
        # Extract links to individual card pages
        card_links = self.extract_card_links(html_content)
        print(f"Found {len(card_links)} card links for set: {self.display_set_name}")
        
        cards = []
        # Process each card page
        for card_url, image_url in card_links:
            full_url = urljoin(self.base_url, card_url)
            print(f"Processing card page: {full_url}")
            
            # Fetch the card details page
            card_html = self.fetch_page(full_url)
            if not card_html:
                continue
            
            # Parse the card details
            card_data = self.parse_card_details_page(card_html, image_url)
            if card_data and 'name' in card_data:
                # Download the card image with set name included in filename
                local_image_path = self.download_image(image_url, card_data['name'])
                card_data['local_image_path'] = local_image_path
                
                cards.append(card_data)
                print(f"Successfully scraped card: {card_data['name']} ({card_data.get('set_name', 'Unknown Set')})")
            
        return cards

    def save_to_json(self, cards: List[Dict], filename: str = None) -> None:
        """Save the scraped cards to a JSON file"""
        if filename is None:
            filename = f"pokemon_cards_{self.set_name}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(cards, f, indent=2, ensure_ascii=False)
        
        print(f"Saved {len(cards)} cards to {filename}")

def parse_arguments():
    parser = argparse.ArgumentParser(description='Scrape Pokemon cards from Serebii TCG Pocket')
    parser.add_argument('--url', type=str,
                        help='URL to scrape (example: https://www.serebii.net/tcgpocket/shiningrevelry/)')
    parser.add_argument('--output', type=str, default=None,
                        help='Output JSON filename (default: pokemon_cards_<set_name>.json)')
    return parser.parse_args()

def main():
    args = parse_arguments()
    scraper = PokemonCardScraper(args.url)
    cards = scraper.scrape_cards()
    
    if cards:
        print(f"Successfully scraped {len(cards)} cards from {scraper.display_set_name}")
        scraper.save_to_json(cards, args.output)
    else:
        print(f"No cards were scraped from {args.url}")

if __name__ == "__main__":
    main()
