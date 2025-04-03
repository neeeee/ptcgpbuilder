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
            self.cursor.execute("""
                INSERT INTO deck_cards (deck_id, card_id, count)
                VALUES (?, ?, 1)
                ON CONFLICT (deck_id, card_id) DO UPDATE SET count = count + 1
            """, (deck_id, card_id))
            self.db_conn.commit()
            self.app.notify(f"Added {card_name} to {deck_name}")

        except sqlite3.Error as e:
            error_msg = f"Error: {str(e)}"
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

            decks_list.remove_children()
            deck_cards.remove_children()

            decks_query = "SELECT decks.id, decks.name FROM decks;"
            decks = self.cursor.execute(decks_query).fetchall()

            for deck in decks:
                unique_id = f"decks-list-{deck[0]}--{time_ns()}"
                item = ListItem(
                    Static(str(deck[1])),
                    id=unique_id,
                )
                setattr(item, "deck_id", deck[0])
                decks_list.mount(item)

        except Exception:
            raise

    def populate_cards_list(self, filters=None) -> None:
        """Populate the cards list, with optional filtering"""
        try:
            cards_list = self.app.query_one("#builder-cards-list")
            cards_list.remove_children()

            if filters:
                self.current_filters = filters
            
            # Start building the query
            query = """SELECT
                        id, name, set_name, image_path, type
                    FROM
                        cards
                    WHERE 1=1
                    """
            params = []
            
            # Apply set filter if provided and not empty
            # Make sure we're not passing a Select.BLANK object
            if (self.current_filters.get("set") and 
                self.current_filters["set"] != "" and 
                str(self.current_filters["set"]) != "Select.BLANK"):
                query += " AND set_name = ?"
                params.append(self.current_filters["set"])
            
            # Apply name filter if provided
            if self.current_filters.get("name"):
                query += " AND name LIKE ?"
                params.append(f"%{self.current_filters['name']}%")
            
            # Apply category filter (formerly type filter)
            if self.current_filters.get("category") == "pokemon":
                query += " AND type NOT LIKE 'Trainer%'"
            elif self.current_filters.get("category") == "trainer":
                query += " AND type LIKE 'Trainer%'"
            
            # Apply Pokémon type filter (new)
            # Make sure we're not passing a Select.BLANK object
            if (self.current_filters.get("pokemon_type") and 
                self.current_filters["pokemon_type"] != "all" and
                str(self.current_filters["pokemon_type"]) != "Select.BLANK"):
                query += " AND type LIKE ?"
                params.append(f"%{self.current_filters['pokemon_type']}%")
            
            # Add sorting
            query += " ORDER BY set_name, name"
            
            # Execute query
            cards = self.cursor.execute(query, params).fetchall()
            
            for card in cards:
                unique_id = f"card-list-{card[0]}-{time_ns()}"
                # Format the display text with set name
                display_text = f"{card[1]} ({card[2]})"
                item = ListItem(
                    Static(display_text),
                    id=unique_id,
                )
                setattr(item, "card_id", card[0])
                cards_list.mount(item)
                
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
            
            # Add a blank option for "All sets"
            all_option = ("", "All Sets")
            options.insert(0, all_option)
            
            # Set the options on the Select widget
            set_filter.set_options(options)
            
            # Try to set the value to the first option after a short delay
            # In this version, we'll just let the default empty value work
            
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
            
            # Handle possible NoSelection cases and Select.BLANK
            # Convert the actual Select.BLANK object to an empty string
            set_value = ""
            if set_filter.value is not None and str(set_filter.value) != "Select.BLANK":
                set_value = set_filter.value
                
            type_value = "all"
            if type_filter.value is not None and str(type_filter.value) != "Select.BLANK":
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
            
            set_filter.value = ""
            self.app.query_one("#name-filter").value = ""
            self.app.query_one("#category-all").value = True
            type_filter.value = "all"
            
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
            deck_id = getattr(event.item, "deck_id", None)

            if deck_id is None:
                return

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
                unique_id = f"decks-card-list-{card[1]}-{str(card[0]).replace(' ', '-')}"
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

    def show_decks_cards_list_info(self, event) -> None:
        try:
            card_id = getattr(event.item, "card_id", None)
            if card_id is None:
                return

            query = """SELECT
                        id, name, set_name, hp, type, image_path, moves, weakness, retreat_cost
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
                
                card_image = self.app.query_one("#card-image-decks-view", CardImage)
                card_image.update_image(image_path)

                # Parse JSON data for moves, weakness, and retreat cost
                moves = json.loads(card[6]) if card[6] else []
                weakness = json.loads(card[7]) if card[7] else []
                retreat_cost = json.loads(card[8]) if card[8] else []

                # Format moves for display
                moves_display = ""
                for move in moves:
                    energy_cost = ", ".join(move.get("energy_cost", []))
                    move_name = move.get("name", "")
                    damage = move.get("damage", "")
                    description = move.get("description", "")
                    moves_display += f"{move_name} ({energy_cost}) - {damage} - {description}\n"

                # Format weakness and retreat cost
                weakness_display = ", ".join(weakness) if weakness else "None"
                retreat_display = ", ".join(retreat_cost) if retreat_cost else "None"

                stats = self.app.query_one("#decks-card-stats", Static)
                string = (
                    f"Name: {card[1]}\n"
                    f"Set: {card[2]}\n"
                    f"HP: {card[3]}\n"
                    f"Type: {card[4]}\n"
                    f"Moves:\n{moves_display}\n"
                    f"Weakness: {weakness_display}\n"
                    f"Retreat Cost: {retreat_display}\n"
                )
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
                        id, name, set_name, hp, type, image_path, moves, weakness, retreat_cost
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

                # Format moves for display
                moves_display = ""
                for move in moves:
                    energy_cost = ", ".join(move.get("energy_cost", []))
                    move_name = move.get("name", "")
                    damage = move.get("damage", "")
                    description = move.get("description", "")
                    moves_display += f"{move_name} ({energy_cost}) - {damage} - {description}\n"

                # Format weakness and retreat cost
                weakness_display = ", ".join(weakness) if weakness else "None"
                retreat_display = ", ".join(retreat_cost) if retreat_cost else "None"

                stats = self.app.query_one("#builder-card-stats", Static)
                string = (
                    f"Name: {card[1]}\n"
                    f"Set: {card[2]}\n"
                    f"HP: {card[3]}\n"
                    f"Type: {card[4]}\n"
                    f"Moves:\n{moves_display}\n"
                    f"Weakness: {weakness_display}\n"
                    f"Retreat Cost: {retreat_display}\n"
                )
                stats.update(string)
                self.app.query_one("#status-message", Label).update(f"Selected: {self.app.current_card_name} ({card[2]}) - Press 'o' for actions")

        except Exception as e:
            self.app.notify(f"Error displaying card: {str(e)}", severity="error")
            raise

