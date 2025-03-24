import sqlite3
from textual.widgets import Static, ListItem
from time import time_ns

class CardManagement:
    def __init__(self, db, cursor, app):
        self.db_conn = db
        self.cursor = cursor
        self.app = app

    def add_card_to_deck(self, card_id, deck_id, deck_name):
        try:
            self.cursor.execute("""
                INSERT INTO deck_cards (deck_id, card_id, count)
                VALUES (?, ?, 1)
                ON CONFLICT (deck_id, card_id) DO UPDATE SET count = count + 1
            """, (deck_id, card_id))
            self.db_conn.commit()

            msg = f"Added {card_id} to {deck_name}"

            return msg

        except sqlite3.Error as e:
            error_msg = f"Error: {str(e)}"
            # self.query_one("#status-message", Label).update(error_msg)
            # self.notify(f"Database error: {str(e)}", severity="error")
            self.db_conn.rollback()
            # msg = f"Failed to add {card_id} to {deck_name}"
            return error_msg

    def remove_from_deck(self, deck_id, card_id):
        query = f"""BEGIN TRANSACTION;
                UPDATE deck_cards
                SET count = CASE
                    WHEN count > 1 THEN count - 1
                    ELSE 0
                END
                WHERE deck_id = {deck_id} AND card_id = {card_id};

                DELETE FROM deck_cards
                WHERE count = 0;
                COMMIT;
                """
        cursor = self.db_conn.cursor()
        cursor.execute(query)

    def populate_decks_list(self):
        try:
            decks_list = self.app.query_one("#decks-deck-selector")
            deck_cards = self.app.query_one("#decks-cards-list")

            decks_list.remove_children()
            deck_cards.remove_children()

            cursor = self.db_conn.cursor()

            decks_query = "SELECT decks.id, decks.name FROM decks;"
            decks = cursor.execute(decks_query).fetchall()

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

    def populate_cards_list(self):
        try:
            cards_list = self.app.query_one("#builder-cards-list")
            cards_list.remove_children()

            cursor = self.db_conn.cursor()
            query = """SELECT
                        id, name, image_path
                    FROM
                        cards
                    ORDER BY
                        name;
                    """
            cards = cursor.execute(query).fetchall()

            for card in cards:
                unique_id = f"card-list-{card[0]}-{time_ns()}"
                item = ListItem(
                    Static(card[1]),
                    id=unique_id,
                )
                setattr(item, "card_id", card[0])  # Store the card ID
                cards_list.mount(item)  # Use mount to add the item


        except Exception:
            raise
