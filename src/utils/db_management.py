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
        """
        Scan a directory for card images and create a mapping of (card_name, set_name) to image_path
        
        Args:
            directory: The directory to scan
            set_name: Optional set name to associate with all images in this directory
            
        Returns:
            Dictionary mapping (card_name, set_name) to image_path
        """
        image_dict = {}
        
        for image_path in glob.glob(os.path.join(directory, "*.jpg")):
            # Get just the filename without extension
            filename = os.path.basename(image_path)
            file_base = os.path.splitext(filename)[0]
            
            # Handle different filename formats
            try:
                # Filename contains a set identifier: set_name_card_name.jpg
                if '_' in file_base:
                    parts = file_base.split('_', 1)  # Split on first underscore only
                    if len(parts) >= 2:
                        set_id = parts[0]
                        card_name = parts[1].replace('_', ' ')
                        
                        # Handle "ex" or other special suffixes that might have been converted to underscores
                        # Convert underscores back to spaces, but special case for "ex" suffix
                        if card_name.endswith("_ex"):
                            card_name = card_name.replace("_ex", " ex")
                        elif "_ex_" in card_name:
                            card_name = card_name.replace("_ex_", " ex ")
                            
                        card_name = card_name.replace('_', ' ')
                        
                        # Use the set_id as key if we don't have a set_name
                        key_set = set_name or set_id
                        image_dict[(card_name, key_set)] = image_path
                # Simple filename without set: card_name.jpg
                else:
                    card_name = file_base.replace('_', ' ')
                    # Only add if we know what set this is
                    if set_name:
                        image_dict[(card_name, set_name)] = image_path
            except Exception as e:
                print(f"Error processing filename {filename}: {e}")
                continue
                
        return image_dict
    
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
            # Normalize card name and set name for matching
            normalized_name = name.lower()
            normalized_set = set_name.lower() if set_name else None
            
            # Try to find exact match first (case insensitive)
            image_path = None
            
            # First try: exact match with both name and set
            for (img_name, img_set), img_path in card_images.items():
                if (img_name.lower() == normalized_name and 
                    (img_set and img_set.lower() == normalized_set)):
                    image_path = img_path
                    break
            
            # Second try: fuzzy set name match (e.g. "base_set" vs "Base Set 2023")
            if not image_path:
                for (img_name, img_set), img_path in card_images.items():
                    if (img_name.lower() == normalized_name and img_set and normalized_set and
                        (normalized_set in img_set.lower() or img_set.lower() in normalized_set)):
                        image_path = img_path
                        break
            
            # Third try: match just by card name, ignoring set
            if not image_path:
                for (img_name, img_set), img_path in card_images.items():
                    if img_name.lower() == normalized_name:
                        image_path = img_path
                        break
            
            # Update the database if we found an image
            if image_path:
                self.cursor.execute(
                    "UPDATE cards SET image_path = ? WHERE id = ?", 
                    (image_path, card_id)
                )
                updated_count += 1
                print(f"Updated image for {name} ({set_name}): {image_path}")
        
        self.conn.commit()
        return updated_count