import sqlite3
import os
from textual.widgets import Static, ListView, ListItem, Label
from time import time_ns
from views.PokemonCard import *
import json

class CardManagement:
    def __init__(self, db, cursor, app):
        self.db_conn = db
        self.cursor = cursor
        self.app = app

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

    def populate_cards_list(self) -> None:
        try:
            cards_list = self.app.query_one("#builder-cards-list")
            cards_list.remove_children()

            query = """SELECT
                        id, name, set_name, image_path
                    FROM
                        cards
                    ORDER BY
                        set_name, name;
                    """
            cards = self.cursor.execute(query).fetchall()

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

        except Exception as e:
            self.app.notify(f"Error populating card list: {str(e)}", severity="error")
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

