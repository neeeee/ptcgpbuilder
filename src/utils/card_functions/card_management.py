import sqlite3
import os
from textual.widgets import Static, ListView, ListItem, Label, Select
from time import time_ns
from views.PokemonCard import *
import json

class CardManagement:
    def __init__(self, db, cursor, app):
        self.db_conn = db
        self.cursor = cursor
        self.app = app
        self.current_filters = {
            "set": "",
            "name": "",
            "category": "all",
            "pokemon_type": "all"
        }

    def add_card_to_deck(self, card_id, deck_id, deck_name, card_name) -> None:
        try:
            # Check total deck size limit
            self.cursor.execute("SELECT SUM(count) FROM deck_cards WHERE deck_id = ?", (deck_id,))
            total_cards = self.cursor.fetchone()[0] or 0
            if total_cards >= 20:
                self.app.notify(f"Deck '{deck_name}' is full (20 cards max). Cannot add {card_name}.", severity="warning")
                return

            # Check specific card count limit
            self.cursor.execute("SELECT count FROM deck_cards WHERE deck_id = ? AND card_id = ?", (deck_id, card_id))
            card_count_row = self.cursor.fetchone()
            card_count = card_count_row[0] if card_count_row else 0
            if card_count >= 2:
                self.app.notify(f"Deck '{deck_name}' already has 2 copies of {card_name}. Cannot add more.", severity="warning")
                return

            # Proceed with adding the card if limits are not exceeded
            self.cursor.execute("""
                INSERT INTO deck_cards (deck_id, card_id, count)
                VALUES (?, ?, 1)
                ON CONFLICT (deck_id, card_id) DO UPDATE SET count = count + 1
            """, (deck_id, card_id))
            self.db_conn.commit()
            self.app.notify(f"Added {card_name} to {deck_name}")

        except sqlite3.Error as e:
            error_msg = f"Error adding card to deck: {str(e)}"
            self.app.query_one("#status-message", Label).update(error_msg)
            self.app.notify(f"Database error: {str(e)}", severity="error")
            self.db_conn.rollback()

    def remove_from_deck(self, deck_id, card_id) -> None:
        self.cursor.execute("BEGIN TRANSACTION;")
        self.cursor.execute(f"UPDATE deck_cards SET count = CASE WHEN count > 1 THEN count - 1 ELSE 0 END WHERE deck_id = {(deck_id)} AND card_id = {(card_id)};")
        self.cursor.execute("DELETE FROM deck_cards WHERE count = 0;")
        self.db_conn.commit()

    def delete_deck(self, deck_id) -> None:
        try:
            self.db_conn.execute("BEGIN TRANSACTION")
            self.cursor.execute("DELETE FROM deck_cards WHERE deck_id = ?", (deck_id,))
            self.cursor.execute("DELETE FROM decks WHERE id = ?", (deck_id,))
            self.db_conn.commit()
            self.app.notify(f"Deleted deck {deck_id}", severity="information")

        except sqlite3.Error as e:
            error_msg = f"Error deleting deck: {str(e)}"
            self.app.notify(f"{error_msg}", severity="error")
            self.db_conn.rollback()

    def rename_deck(self, deck_id, new_name) -> None:
        try:
            self.cursor.execute("""
                UPDATE decks 
                SET name = ?
                WHERE id = ?
            """, (new_name, deck_id))
            self.db_conn.commit()
            self.app.notify(f"Renamed deck to {new_name}", severity="information")
            
        except sqlite3.Error as e:
            error_msg = f"Error renaming deck: {str(e)}"
            self.app.notify(error_msg, severity="error")
            self.db_conn.rollback()

    def create_empty_deck(self, deck_name) -> None:
        try:
            self.cursor.execute("""
                INSERT INTO decks (name)
                VALUES (?)
            """, (deck_name,))
            self.db_conn.commit()
            self.app.notify(f"Created new deck: {deck_name}", severity="information")
            self.populate_decks_list()
            
        except sqlite3.Error as e:
            error_msg = f"Error creating deck: {str(e)}"
            self.app.notify(error_msg, severity="error")
            self.db_conn.rollback()

    def populate_decks_list(self) -> None:
        try:
            decks_list = self.app.query_one("#decks-deck-selector")
            deck_cards = self.app.query_one("#decks-cards-list")
            
            # First clear both lists
            decks_list.clear()
            deck_cards.clear()

            decks_query = "SELECT decks.id, decks.name FROM decks;"
            decks = self.cursor.execute(decks_query).fetchall()

            for deck in decks:
                # Use timestamp to ensure ID uniqueness
                unique_id = f"deck-{deck[0]}-{time_ns()}"
                deck_name = str(deck[1])
                item = ListItem(
                    Static(deck_name),
                    id=unique_id,
                )
                # Make sure deck_id is set as an attribute
                setattr(item, "deck_id", deck[0])
                # Use append for ListView
                decks_list.append(item)
            
            # Reset index after repopulating
            if decks:
                decks_list.index = 0
            else:
                decks_list.index = None

        except Exception as e:
            self.app.notify(f"Error populating decks: {str(e)}", severity="error")
            raise

    def populate_cards_list(self, filters=None) -> None:
        """Populate the cards list, with optional filtering"""
        try:
            cards_list = self.app.query_one("#builder-cards-list")
            # Use clear() instead of remove_children()
            cards_list.clear()

            if filters:
                # Safety check - convert any Select.BLANK to empty string
                for key in filters:
                    if hasattr(filters[key], "__class__") and filters[key].__class__.__name__ == "NoSelection":
                        filters[key] = ""  # Convert BLANK to empty string for safe SQL
                self.current_filters = filters
            
            # Start building the query
            query = """SELECT
                        id, name, set_name, image_path, type, card_type
                    FROM
                        cards
                    WHERE 1=1
                    """
            params = []
            
            # Apply set filter if provided and not empty
            if self.current_filters.get("set") and self.current_filters["set"] != "":
                query += " AND set_name = ?"
                params.append(self.current_filters["set"])
            
            # Apply name filter if provided
            if self.current_filters.get("name"):
                query += " AND name LIKE ?"
                params.append(f"%{self.current_filters['name']}%")
            
            # Apply category filter (using correct card_type values)
            if self.current_filters.get("category") == "pokemon":
                # Pokémon cards seem to have NULL or empty card_type
                query += " AND (card_type IS NULL OR card_type = '')"
                # Apply Pokémon type filter only when category is pokemon
                if self.current_filters.get("pokemon_type") and self.current_filters["pokemon_type"] != "all":
                    query += " AND type LIKE ?"
                    params.append(f"%{self.current_filters['pokemon_type']}%")
            elif self.current_filters.get("category") == "trainer":
                # Trainer cards are labeled 'Trainer' or 'Supporter'
                query += " AND (card_type = 'Trainer' OR card_type = 'Supporter')"
            
            # Apply Pokémon type filter if category is 'all' (implicitly filters for Pokémon)
            elif self.current_filters.get("category") == "all" and \
                 self.current_filters.get("pokemon_type") and \
                 self.current_filters["pokemon_type"] != "all":
                query += " AND type LIKE ?"
                params.append(f"%{self.current_filters['pokemon_type']}%")
            
            # Add sorting
            query += " ORDER BY set_name, name"
            
            # Execute query
            cards = self.cursor.execute(query, params).fetchall()
            
            for card in cards:
                # Use timestamp to ensure ID uniqueness
                unique_id = f"card-{card[0]}-{time_ns()}"
                # Format the display text with set name
                display_text = f"{card[1]} ({card[2]})"
                item = ListItem(
                    Static(display_text),
                    id=unique_id,
                )
                setattr(item, "card_id", card[0])
                # Use append for ListView
                cards_list.append(item)
                
            # Explicitly reset index after repopulating to prevent IndexError
            if cards:
                cards_list.index = 0
            else:
                cards_list.index = None
            
            # Update status message with count of cards found
            self.app.query_one("#status-message", Label).update(
                f"Found {len(cards)} cards matching your filters"
            )

        except Exception as e:
            self.app.notify(f"Error populating card list: {str(e)}", severity="error")
            raise
            
    def populate_set_filter(self) -> None:
        """Populate the set filter dropdown with available sets"""
        try:
            set_filter = self.app.query_one("#set-filter", Select)
            
            # Get all unique set names from the database
            query = "SELECT DISTINCT set_name FROM cards ORDER BY set_name"
            sets = self.cursor.execute(query).fetchall()
            
            # Create the options for the dropdown
            options = [(set_name[0], set_name[0]) for set_name in sets]
            
            # Add an "All Sets" option as the first option - use empty string instead of None
            all_option = ("", "All Sets")
            options.insert(0, all_option)
            
            # Set the options on the Select widget
            set_filter.clear()
            set_filter.set_options(options)
            
            # The first option (All Sets) will be selected automatically
            
        except Exception as e:
            self.app.notify(f"Error populating set filter: {str(e)}", severity="error")
            raise
            
    def apply_filters(self) -> None:
        """Apply the current filters to the card list"""
        try:
            # Get values from filter controls
            set_filter = self.app.query_one("#set-filter", Select)
            name_filter = self.app.query_one("#name-filter")
            type_filter = self.app.query_one("#type-filter", Select)
            
            # Determine which category radio button is selected
            category_value = "all"
            if self.app.query_one("#category-pokemon").value:
                category_value = "pokemon"
            elif self.app.query_one("#category-trainer").value:
                category_value = "trainer"
            
            # Handle set filter value - check for BLANK or empty string
            set_value = ""
            # Check if value is None, BLANK, or empty string (all treated as "All Sets")
            if hasattr(set_filter.value, "__class__") and set_filter.value.__class__.__name__ == "NoSelection":
                set_value = ""  # Handle Select.BLANK case
            elif set_filter.value not in (None, ""):
                set_value = set_filter.value
                
            # Handle type filter value
            type_value = "all"
            if hasattr(type_filter.value, "__class__") and type_filter.value.__class__.__name__ == "NoSelection":
                type_value = "all"  # Handle Select.BLANK case
            elif type_filter.value not in (None, ""):
                type_value = type_filter.value
            
            # Set the filters
            filters = {
                "set": set_value,
                "name": name_filter.value,
                "category": category_value,
                "pokemon_type": type_value
            }
            
            # Apply the filters
            self.populate_cards_list(filters)
            
        except Exception as e:
            self.app.notify(f"Error applying filters: {str(e)}", severity="error")
            raise
            
    def clear_filters(self) -> None:
        """Clear all filters and reset to default view"""
        try:
            # Reset filter controls
            set_filter = self.app.query_one("#set-filter", Select)
            type_filter = self.app.query_one("#type-filter", Select)
            
            # Reset name input and category
            self.app.query_one("#name-filter").value = ""
            self.app.query_one("#category-all").value = True
            
            # Reset Pokemon type filter - use try/except since has_option() doesn't exist
            try:
                type_filter.value = "all"  # Try setting to "all" directly
            except Exception:
                type_filter.clear()  # If that fails, just clear it
            
            # Reset set filter - use try/except since has_option() doesn't exist
            try:
                set_filter.value = ""  # Try setting to empty string directly
            except Exception:
                set_filter.clear()  # If that fails, just clear it
            
            # Reset filters and repopulate
            self.current_filters = {
                "set": "",
                "name": "",
                "category": "all",
                "pokemon_type": "all"
            }
            self.populate_cards_list()
            
        except Exception as e:
            self.app.notify(f"Error clearing filters: {str(e)}", severity="error")
            raise

    def populate_decks_cards_list(self, event) -> None:
        try:
            decks_cards_list = self.app.query_one("#decks-cards-list", ListView)
            # Clear the list view and reset its state
            decks_cards_list.clear()
            
            # Get the deck_id from the highlighted item
            deck_id = getattr(event.item, "deck_id", None)

            if deck_id is None:
                return

            # Store the current deck ID in the app for other operations
            self.app.current_deck_id = deck_id
            
            cursor = self.db_conn.cursor()
            query = """SELECT
                        d.name AS deck_name,
                        c.id AS card_id,
                        c.name AS card_name,
                        c.set_name AS set_name,
                        dc.count
                    FROM
                        deck_cards dc
                    JOIN
                        decks d ON dc.deck_id = d.id
                    JOIN
                        cards c ON dc.card_id = c.id
                    WHERE
                        dc.deck_id = ?;
                    """

            cards = cursor.execute(query, (deck_id,)).fetchall()

            for card in cards:
                # Use timestamp to ensure ID uniqueness
                unique_id = f"decks-card-{card[1]}-{time_ns()}"
                # Include set name in the display
                card_display = f"{card[2]} ({card[3]}) (x{card[4]})"
                item = ListItem(
                    Static(card_display),
                    id=unique_id,
                )
                setattr(item, "card_id", card[1])
                decks_cards_list.append(item)

        except Exception as e:
            self.app.notify(f"Error loading deck cards: {str(e)}", severity="error")
            raise

    def ensure_image_path_exists(self, image_path):
        """Ensure the image path exists and is accessible"""
        if not image_path:
            return None
            
        # Try the path as-is
        if os.path.exists(image_path):
            return image_path
            
        # If the path uses 'src/db' but the file is in 'db', try adjusting the path
        if image_path.startswith('src/db/'):
            alt_path = image_path.replace('src/db/', 'db/', 1)
            if os.path.exists(alt_path):
                return alt_path
                
        # If the path uses 'db' but the file is in 'src/db', try adjusting the path
        if image_path.startswith('db/'):
            alt_path = f"src/{image_path}"
            if os.path.exists(alt_path):
                return alt_path
                
        return image_path  # Return original path even if not found

    def display_card_details(self, event) -> None:
        try:
            card_id = getattr(event.item, "card_id", None)
            if card_id is None:
                return

            query = """SELECT
                        id, name, set_name, hp, type, image_path, moves, weakness, retreat_cost,
                        card_type, description, rule_text
                    FROM
                        cards
                    WHERE
                        id = ?;
                    """
            card = self.cursor.execute(query, (card_id,)).fetchone()

            if card:
                self.app.current_card = PokemonCard(*card)
                self.app.current_card_id = card[0]
                self.app.current_card_name = card[1]
                
                # Ensure the image path exists
                image_path = self.ensure_image_path_exists(card[5])
                
                # Use the correct ID for the Deck view's image widget
                card_image = self.app.query_one("#card-image-decks-view", CardImage)
                card_image.update_image(image_path)

                # Parse JSON data for moves, weakness, and retreat cost
                moves = json.loads(card[6]) if card[6] else []
                weakness = json.loads(card[7]) if card[7] else []
                retreat_cost = json.loads(card[8]) if card[8] else []
                
                # Get card type, description, and rule text
                card_type = card[9] if len(card) > 9 and card[9] else ""
                description = card[10] if len(card) > 10 and card[10] else ""
                rule_text = card[11] if len(card) > 11 and card[11] else ""

                # Format the display differently based on card type
                string = ""
                
                # Basic info for all cards
                string = (
                    f"Name: {card[1]}\n"
                    f"Set: {card[2]}\n"
                )
                
                # Add card type if present
                if card_type:
                    string += f"Card Type: {card_type}\n"
                
                # For Pokémon cards
                if not card_type or ("Pokémon" in card_type and "Tool" not in card_type):
                    # Format moves for display
                    moves_display = ""
                    for move in moves:
                        energy_cost = ", ".join(move.get("energy_cost", []))
                        move_name = move.get("name", "")
                        damage = move.get("damage", "")
                        move_description = move.get("description", "")
                        moves_display += f"{move_name} ({energy_cost}) - {damage} - {move_description}\n"
                    
                    # Add Pokémon-specific info
                    string += (
                        f"HP: {card[3]}\n"
                        f"Type: {card[4]}\n"
                        f"Moves:\n{moves_display}\n"
                        f"Weakness: {', '.join(weakness) if weakness else 'None'}\n"
                        f"Retreat Cost: {', '.join(retreat_cost) if retreat_cost else 'None'}\n"
                    )
                # For Trainer/Tool/Supporter cards
                elif "Trainer" in card_type or "Tool" in card_type or "Supporter" in card_type:
                    # Add Trainer/Tool/Supporter-specific info
                    if description:
                        string += f"\nEffect:\n{description}\n"
                    if rule_text:
                        string += f"\nRule Text:\n{rule_text}\n"

                stats = self.app.query_one("#decks-card-stats", Static)
                stats.update(string)
                self.app.query_one("#status-message", Label).update(f"Selected: {self.app.current_card_name} ({card[2]}) - Press 'o' for actions")
        except Exception as e:
            self.app.notify(f"Error displaying card: {str(e)}", severity="error")
            raise

    def show_builder_cards_list_info(self, event) -> None:
        try:
            card_id = getattr(event.item, "card_id", None)
            if card_id is None:
                return

            query = """SELECT
                        id, name, set_name, hp, type, image_path, moves, weakness, retreat_cost,
                        card_type, description, rule_text
                    FROM
                        cards
                    WHERE
                        id = ?;
                    """
            card = self.cursor.execute(query, (card_id,)).fetchone()

            if card:
                self.app.current_card = PokemonCard(*card)
                self.app.current_card_id = card[0]
                self.app.current_card_name = card[1]
                
                # Ensure the image path exists
                image_path = self.ensure_image_path_exists(card[5])
                
                card_image = self.app.query_one("#card-image-builder-view", CardImage)
                card_image.update_image(image_path)

                # Parse JSON data for moves, weakness, and retreat cost
                moves = json.loads(card[6]) if card[6] else []
                weakness = json.loads(card[7]) if card[7] else []
                retreat_cost = json.loads(card[8]) if card[8] else []
                
                # Get card type, description, and rule text
                card_type = card[9] if len(card) > 9 and card[9] else ""
                description = card[10] if len(card) > 10 and card[10] else ""
                rule_text = card[11] if len(card) > 11 and card[11] else ""

                # Format the display differently based on card type
                string = ""
                
                # Basic info for all cards
                string = (
                    f"Name: {card[1]}\n"
                    f"Set: {card[2]}\n"
                )
                
                # Add card type if present
                if card_type:
                    string += f"Card Type: {card_type}\n"
                
                # For Pokémon cards
                if not card_type or "Pokémon" in card_type and not "Tool" in card_type:
                    # Format moves for display
                    moves_display = ""
                    for move in moves:
                        energy_cost = ", ".join(move.get("energy_cost", []))
                        move_name = move.get("name", "")
                        damage = move.get("damage", "")
                        move_description = move.get("description", "")
                        moves_display += f"{move_name} ({energy_cost}) - {damage} - {move_description}\n"
                    
                    # Add Pokémon-specific info
                    string += (
                        f"HP: {card[3]}\n"
                        f"Type: {card[4]}\n"
                        f"Moves:\n{moves_display}\n"
                        f"Weakness: {', '.join(weakness) if weakness else 'None'}\n"
                        f"Retreat Cost: {', '.join(retreat_cost) if retreat_cost else 'None'}\n"
                    )
                # For Trainer/Tool/Supporter cards
                elif "Trainer" in card_type or "Tool" in card_type or "Supporter" in card_type:
                    # Add Trainer/Tool/Supporter-specific info
                    if description:
                        string += f"\nEffect:\n{description}\n"
                    if rule_text:
                        string += f"\nRule Text:\n{rule_text}\n"

                stats = self.app.query_one("#builder-card-stats", Static)
                stats.update(string)
                self.app.query_one("#status-message", Label).update(f"Selected: {self.app.current_card_name} ({card[2]}) - Press 'o' for actions")

        except Exception as e:
            self.app.notify(f"Error displaying card: {str(e)}", severity="error")
            raise

