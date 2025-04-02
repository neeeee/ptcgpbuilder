import os
import sqlite3
from pathlib import Path
import glob

class DBManagement:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.conn.row_factory = sqlite3.Row

    def update_card_image_paths(self):
        """Updates the image_path column in cards table with paths to card images"""
        try:
            # Find the root pokemon_cards directory
            base_cards_dir = None
            for possible_path in ["src/db/pokemon_cards", "db/pokemon_cards"]:
                if os.path.exists(possible_path):
                    base_cards_dir = possible_path
                    break
            
            if not base_cards_dir:
                raise FileNotFoundError("Could not find the pokemon_cards directory")

            print(f"Updating image paths from base directory: {base_cards_dir}")
            
            # Dictionary to store all found card images {(card_name, set_name): image_path}
            card_images = {}
            
            # First, check for images directly in the root directory (legacy format)
            root_images = self._scan_directory_for_images(base_cards_dir)
            print(f"Found {len(root_images)} image files in the root directory")
            card_images.update(root_images)
            
            # Then, scan each set subdirectory
            set_dirs = [d for d in os.listdir(base_cards_dir) 
                       if os.path.isdir(os.path.join(base_cards_dir, d)) and d != 'types']
            
            print(f"Found {len(set_dirs)} set directories: {', '.join(set_dirs)}")
            
            # Process each set directory
            for set_dir in set_dirs:
                set_path = os.path.join(base_cards_dir, set_dir)
                set_images = self._scan_directory_for_images(set_path, set_name=set_dir)
                print(f"Found {len(set_images)} image files in the {set_dir} directory")
                card_images.update(set_images)
            
            # Update the database with all found images
            print(f"Total card images found: {len(card_images)}")
            updated_count = self._update_image_paths_in_db(card_images)
            
            self.conn.commit()
            print(f"Successfully updated {updated_count} card image paths in the database")
            return True

        except sqlite3.Error as e:
            print(f"Database error: {e}")
            self.conn.rollback()
            return False
        except Exception as e:
            print(f"Error updating image paths: {e}")
            import traceback
            traceback.print_exc()
            self.conn.rollback()
            return False
    
    def _scan_directory_for_images(self, directory, set_name=None):
        """Scan a directory for card images and return a dictionary of card info to paths
        
        Args:
            directory: Directory to scan
            set_name: Optional override for set name (useful for set subdirectories)
            
        Returns:
            Dictionary mapping (card_name, set_name) to image path
        """
        results = {}
        # Get all image files in the directory
        image_files = glob.glob(os.path.join(directory, "*.jpg")) + \
                     glob.glob(os.path.join(directory, "*.png")) + \
                     glob.glob(os.path.join(directory, "*.jpeg"))
        
        for image_path in image_files:
            # Get just the filename without extension
            filename = os.path.basename(image_path)
            file_base = os.path.splitext(filename)[0]
            
            # Handle different filename formats
            if '_' in file_base and not set_name:
                # Filename contains a set identifier: set_name_card_name.jpg
                parts = file_base.split('_', 1)  # Split on first underscore
                if len(parts) >= 2:
                    img_set = parts[0].replace('_', ' ')
                    card_name = parts[1].replace('_', ' ')
                    results[(card_name.lower(), img_set.lower())] = image_path
            else:
                # Either a simple card name or we're in a set directory
                card_name = file_base.replace('_', ' ')
                if set_name:
                    # We're in a set directory, use that as the set name
                    set_display = set_name.replace('_', ' ').replace('-', ' ').title()
                    results[(card_name.lower(), set_display.lower())] = image_path
                else:
                    # No set info, just use the card name (will match any set)
                    results[(card_name.lower(), None)] = image_path
        
        return results
    
    def _update_image_paths_in_db(self, card_images):
        """Update the image_path in the database for all found card images
        
        Args:
            card_images: Dictionary mapping (card_name, set_name) to image path
            
        Returns:
            Number of records updated
        """
        updated_count = 0
        
        # First, get a list of all cards in the database
        self.cursor.execute("SELECT id, name, set_name FROM cards")
        db_cards = self.cursor.fetchall()
        
        for card_id, name, set_name in db_cards:
            # Try to find a matching image with exact set name match
            card_key = (name.lower(), set_name.lower() if set_name else None)
            if card_key in card_images:
                image_path = card_images[card_key]
                self.cursor.execute(
                    "UPDATE cards SET image_path = ? WHERE id = ?", 
                    (image_path, card_id)
                )
                updated_count += 1
            else:
                # Try to find a match with just the card name (no set name)
                name_only_key = (name.lower(), None)
                if name_only_key in card_images:
                    image_path = card_images[name_only_key]
                    self.cursor.execute(
                        "UPDATE cards SET image_path = ? WHERE id = ?", 
                        (image_path, card_id)
                    )
                    updated_count += 1
        
        return updated_count