import sqlite3
from textual.widgets import Static, ListView, ListItem, Label
from time import time_ns
from views.PokemonCard import *

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
                        id, name, image_path
                    FROM
                        cards
                    ORDER BY
                        name;
                    """
            cards = self.cursor.execute(query).fetchall()

            for card in cards:
                unique_id = f"card-list-{card[0]}-{time_ns()}"
                item = ListItem(
                    Static(card[1]),
                    id=unique_id,
                )
                setattr(item, "card_id", card[0])
                cards_list.mount(item)

        except Exception:
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
                item = ListItem(
                    Static(f"{card[2]} (x{card[3]})"),
                    id=unique_id,
                )
                setattr(item, "card_id", card[1])
                decks_cards_list.append(item)

        except Exception:
            raise

    def show_decks_cards_list_info(self, event) -> None:
        try:
            card_id = getattr(event.item, "card_id", None)
            if card_id is None:
                return

            query = """SELECT
                        id, name, hp, attacks, abilities, image_path
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
                card_image = self.app.query_one("#card-image-decks-view", CardImage)
                card_image.update_image(card[5])

                stats = self.app.query_one("#decks-card-stats", Static)
                string =  (
                    f"HP: {card[2]}\n"
                    f"Attacks: {card[3]}\n"
                    f"Abilities: {card[4]}\n"
                    f"Name: {card[1]}\n"
                )
                stats.update(string)
                self.app.query_one("#status-message", Label).update(f"Selected: {self.app.current_card_name} - Press 'o' for actions")
        except Exception:
            raise

    def show_builder_cards_list_info(self, event) -> None:
        try:
            card_id = getattr(event.item, "card_id", None)
            if card_id is None:
                return

            query = """SELECT
                        id, name, hp, attacks, abilities, image_path
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
                card_image = self.app.query_one("#card-image-builder-view", CardImage)
                card_image.update_image(card[5])

                stats = self.app.query_one("#builder-card-stats", Static)
                string =  (
                    f"HP: {card[2]}\n"
                    f"Attacks: {card[3]}\n"
                    f"Abilities: {card[4]}\n"
                    f"Name: {card[1]}\n"
                )
                stats.update(string)
                self.app.query_one("#status-message", Label).update(f"Selected: {self.app.current_card_name} - Press 'o' for actions")

        except Exception:
            raise

