from textual.widgets import (
    ListItem,
    Static,
)

from time import time_ns

def populate_decks_list(self):
    try:
        decks_list = self.query_one("#decks-deck-selector")
        deck_cards = self.query_one("#decks-cards-list")

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
