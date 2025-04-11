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

    def add_card_to_deck(self, card_id, deck_id, deck_name, card_name, quantity=1) -> None:
        try:
            self.cursor.execute("SELECT SUM(count) FROM deck_cards WHERE deck_id = ?", (deck_id,))
            total_cards = self.cursor.fetchone()[0] or 0
            if total_cards + quantity > 20:
                self.app.notify(f"Deck '{deck_name}' would exceed 20 cards. Cannot add {quantity} copies of {card_name}.", severity="warning")
                return

            self.cursor.execute("SELECT count FROM deck_cards WHERE deck_id = ? AND card_id = ?", (deck_id, card_id))
            card_count_row = self.cursor.fetchone()
            card_count = card_count_row[0] if card_count_row else 0
            if card_count + quantity > 2:
                self.app.notify(f"Deck '{deck_name}' would exceed 2 copies of {card_name}. Cannot add {quantity} more.", severity="warning")
                return

            self.cursor.execute("""
                INSERT INTO deck_cards (deck_id, card_id, count)
                VALUES (?, ?, ?)
                ON CONFLICT (deck_id, card_id) DO UPDATE SET count = count + ?
            """, (deck_id, card_id, quantity, quantity))
            self.db_conn.commit()
            self.app.notify(f"Added {quantity} copies of {card_name} to {deck_name}")

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
            
            decks_list.clear()
            deck_cards.clear()

            decks_query = "SELECT decks.id, decks.name FROM decks;"
            decks = self.cursor.execute(decks_query).fetchall()

            for deck in decks:
                unique_id = f"deck-{deck[0]}-{time_ns()}"
                deck_name = str(deck[1])
                item = ListItem(
                    Static(deck_name),
                    id=unique_id,
                )
                setattr(item, "deck_id", deck[0])
                decks_list.append(item)
            
            if decks:
                decks_list.index = 0
            else:
                decks_list.index = None

        except Exception as e:
            self.app.notify(f"Error populating decks: {str(e)}", severity="error")
            raise

    def populate_cards_list(self, filters=None) -> None:
        try:
            cards_list = self.app.query_one("#builder-cards-list")
            cards_list.clear()

            if filters:
                for key in filters:
                    if hasattr(filters[key], "__class__") and filters[key].__class__.__name__ == "NoSelection":
                        filters[key] = "" 
                self.current_filters = filters
            
            query = """SELECT
                        id, name, set_name, image_path, type, card_type
                    FROM
                        cards
                    WHERE 1=1
                    """
            params = []
            
            if self.current_filters.get("set") and self.current_filters["set"] != "":
                query += " AND set_name = ?"
                params.append(self.current_filters["set"])
            
            if self.current_filters.get("name"):
                query += " AND name LIKE ?"
                params.append(f"%{self.current_filters['name']}%")
            
            if self.current_filters.get("category") == "pokemon":
                query += " AND (card_type IS NULL OR card_type = '')"
                if self.current_filters.get("pokemon_type") and self.current_filters["pokemon_type"] != "all":
                    query += " AND type LIKE ?"
                    params.append(f"%{self.current_filters['pokemon_type']}%")
            elif self.current_filters.get("category") == "trainer":
                query += " AND (card_type = 'Trainer' OR card_type = 'Supporter')"
            
            elif self.current_filters.get("category") == "all" and \
                 self.current_filters.get("pokemon_type") and \
                 self.current_filters["pokemon_type"] != "all":
                query += " AND type LIKE ?"
                params.append(f"%{self.current_filters['pokemon_type']}%")
            
            query += " ORDER BY set_name, name"
            
            cards = self.cursor.execute(query, params).fetchall()
            
            for card in cards:
                unique_id = f"card-{card[0]}-{time_ns()}"
                display_text = f"{card[1]} ({card[2]})"
                item = ListItem(
                    Static(display_text),
                    id=unique_id,
                )
                setattr(item, "card_id", card[0])
                cards_list.append(item)
                
            if cards:
                cards_list.index = 0
            else:
                cards_list.index = None
            
            self.app.query_one("#status-message", Label).update(
                f"Found {len(cards)} cards matching your filters"
            )

        except Exception as e:
            self.app.notify(f"Error populating card list: {str(e)}", severity="error")
            raise
            
    def populate_set_filter(self) -> None:
        try:
            set_filter = self.app.query_one("#set-filter", Select)
            
            query = "SELECT DISTINCT set_name FROM cards ORDER BY set_name"
            sets = self.cursor.execute(query).fetchall()
            
            options = [(set_name[0], set_name[0]) for set_name in sets]
            
            all_option = ("", "All Sets")
            options.insert(0, all_option)
            
            set_filter.clear()
            set_filter.set_options(options)
            
            
        except Exception as e:
            self.app.notify(f"Error populating set filter: {str(e)}", severity="error")
            raise
            
    def apply_filters(self) -> None:
        try:
            set_filter = self.app.query_one("#set-filter", Select)
            name_filter = self.app.query_one("#name-filter")
            type_filter = self.app.query_one("#type-filter", Select)
            
            category_value = "all"
            if self.app.query_one("#category-pokemon").value:
                category_value = "pokemon"
            elif self.app.query_one("#category-trainer").value:
                category_value = "trainer"
            
            set_value = ""
            if hasattr(set_filter.value, "__class__") and set_filter.value.__class__.__name__ == "NoSelection":
                set_value = "" 
            elif set_filter.value not in (None, ""):
                set_value = set_filter.value
                
            type_value = "all"
            if hasattr(type_filter.value, "__class__") and type_filter.value.__class__.__name__ == "NoSelection":
                type_value = "all"  
            elif type_filter.value not in (None, ""):
                type_value = type_filter.value
            
            filters = {
                "set": set_value,
                "name": name_filter.value,
                "category": category_value,
                "pokemon_type": type_value
            }
            
            self.populate_cards_list(filters)
            
        except Exception as e:
            self.app.notify(f"Error applying filters: {str(e)}", severity="error")
            raise
            
    def clear_filters(self) -> None:
        try:
            set_filter = self.app.query_one("#set-filter", Select)
            type_filter = self.app.query_one("#type-filter", Select)
            
            self.app.query_one("#name-filter").value = ""
            self.app.query_one("#category-all").value = True
            
            try:
                type_filter.value = "all" 
            except Exception:
                type_filter.clear()
            try:
                set_filter.value = "" 
            except Exception:
                set_filter.clear() 
            
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
            decks_cards_list.clear()
            
            deck_id = getattr(event.item, "deck_id", None)

            if deck_id is None:
                return

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
                unique_id = f"decks-card-{card[1]}-{time_ns()}"
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
        if not image_path:
            return None
            
        if os.path.exists(image_path):
            return image_path
            
        if image_path.startswith('src/db/'):
            alt_path = image_path.replace('src/db/', 'db/', 1)
            if os.path.exists(alt_path):
                return alt_path
                
        if image_path.startswith('db/'):
            alt_path = f"src/{image_path}"
            if os.path.exists(alt_path):
                return alt_path
                
        return image_path
        
    @staticmethod
    def get_type_image_path(type_name: str) -> str:
        type_map = {
            "Colorless": "colorless.png",
            "Darkness": "dark.png", 
            "Dragon": "dragon.png",
            "Fairy": "fairy.png",
            "Fighting": "fighting.png",
            "Fire": "fire.png",
            "Grass": "grass.png",
            "Lightning": "lightning.png",
            "Metal": "metal.png",
            "Psychic": "psychic.png",
            "Water": "water.png"
        }
        if type_name in type_map:
            base_path = "db/pokemon_cards/types"
            if not os.path.exists(base_path):
                base_path = "src/db/pokemon_cards/types"
            return f"{base_path}/{type_map[type_name]}"
        return ""

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
                
                image_path = self.ensure_image_path_exists(card[5])
                
                card_image = self.app.query_one("#card-image-decks-view", CardImage)
                card_image.update_image(image_path)

                moves = json.loads(card[6]) if card[6] else []
                weakness = json.loads(card[7]) if card[7] else []
                retreat_cost = json.loads(card[8]) if card[8] else []
                
                # Convert retreat_cost array to image paths
                retreat_cost_images = []
                for cost_type in retreat_cost:
                    image_path = CardManagement.get_type_image_path(cost_type)
                    if image_path:
                        retreat_cost_images.append(image_path)
                
                card_type = card[9] if len(card) > 9 and card[9] else ""
                description = card[10] if len(card) > 10 and card[10] else ""
                rule_text = card[11] if len(card) > 11 and card[11] else ""

                string = ""
                
                string = (
                    f"Name: {card[1]}\n"
                    f"Set: {card[2]}\n"
                )
                
                if card_type:
                    string += f"Card Type: {card_type}\n"
                
                if not card_type or ("Pokémon" in card_type and "Tool" not in card_type):
                    moves_display = ""
                    for move in moves:
                        energy_cost = ", ".join(move.get("energy_cost", []))
                        move_name = move.get("name", "")
                        damage = move.get("damage", "")
                        move_description = move.get("description", "")
                        moves_display += f"{move_name} ({energy_cost}) - {damage} - {move_description}\n"
                    
                    # Create retreat cost display using actual values instead of image paths
                    retreat_cost_display = "None"
                    if retreat_cost:
                        # Display retreat cost as number and type
                        retreat_count = len(retreat_cost)
                        retreat_type = retreat_cost[0] if retreat_cost else "Colorless"
                        retreat_cost_display = f"{retreat_count} {retreat_type}"
                    
                    string += (
                        f"HP: {card[3]}\n"
                        f"Type: {card[4]}\n"
                        f"Moves:\n{moves_display}\n"
                        f"Weakness: {', '.join(weakness) if weakness else 'None'}\n"
                        f"Retreat Cost: {retreat_cost_display}\n"
                    )
                elif "Trainer" in card_type or "Tool" in card_type or "Supporter" in card_type:
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
                
                image_path = self.ensure_image_path_exists(card[5])
                
                card_image = self.app.query_one("#card-image-builder-view", CardImage)
                card_image.update_image(image_path)

                moves = json.loads(card[6]) if card[6] else []
                weakness = json.loads(card[7]) if card[7] else []
                retreat_cost = json.loads(card[8]) if card[8] else []
                
                card_type = card[9] if len(card) > 9 and card[9] else ""
                description = card[10] if len(card) > 10 and card[10] else ""
                rule_text = card[11] if len(card) > 11 and card[11] else ""

                string = ""
                
                string = (
                    f"Name: {card[1]}\n"
                    f"Set: {card[2]}\n"
                )
                
                if card_type:
                    string += f"Card Type: {card_type}\n"
                
                if not card_type or "Pokémon" in card_type and not "Tool" in card_type:
                    moves_display = ""
                    for move in moves:
                        energy_cost = ", ".join(move.get("energy_cost", []))
                        move_name = move.get("name", "")
                        damage = move.get("damage", "")
                        move_description = move.get("description", "")
                        moves_display += f"{move_name} ({energy_cost}) - {damage} - {move_description}\n"
                    
                    # Convert retreat_cost array to image paths
                    retreat_cost_images = []
                    for cost_type in retreat_cost:
                        image_path = CardManagement.get_type_image_path(cost_type)
                        if image_path:
                            retreat_cost_images.append(image_path)
                    
                    # Create retreat cost display using actual values instead of image paths
                    retreat_cost_display = "None"
                    if retreat_cost:
                        # Display retreat cost as number and type
                        retreat_count = len(retreat_cost)
                        retreat_type = retreat_cost[0] if retreat_cost else "Colorless"
                        retreat_cost_display = f"{retreat_count} {retreat_type}"
                    
                    string += (
                        f"HP: {card[3]}\n"
                        f"Type: {card[4]}\n"
                        f"Moves:\n{moves_display}\n"
                        f"Weakness: {', '.join(weakness) if weakness else 'None'}\n"
                        f"Retreat Cost: {retreat_cost_display}\n"
                    )
                elif "Trainer" in card_type or "Tool" in card_type or "Supporter" in card_type:
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

    def export_deck_cards(self, deck_id) -> None:
        try:
            # Get deck name
            self.cursor.execute("SELECT name FROM decks WHERE id = ?", (deck_id,))
            deck_name = self.cursor.fetchone()[0]
            
            # Get all cards in the deck
            self.cursor.execute("""
                SELECT c.name, c.set_name, dc.count
                FROM deck_cards dc
                JOIN cards c ON dc.card_id = c.id
                WHERE dc.deck_id = ?
                ORDER BY c.name
            """, (deck_id,))
            cards = self.cursor.fetchall()
            
            if not cards:
                self.app.notify("No cards in deck to export", severity="warning")
                return
                
            # Create export directory if it doesn't exist
            export_dir = "exports"
            if not os.path.exists(export_dir):
                os.makedirs(export_dir)
                
            # Create filename with timestamp
            timestamp = time_ns()
            filename = f"{export_dir}/{deck_name}_{timestamp}.txt"
            
            # Write cards to file
            with open(filename, "w") as f:
                f.write(f"Deck: {deck_name}\n")
                f.write("=" * 50 + "\n\n")
                for card in cards:
                    f.write(f"{card[2]}x {card[0]} ({card[1]})\n")
                    
            self.app.notify(f"Deck exported to {filename}", severity="information")
            
        except Exception as e:
            self.app.notify(f"Error exporting deck: {str(e)}", severity="error")
            raise

