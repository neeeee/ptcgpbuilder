from textual.widgets import (
    ListItem,
    Static,
)

from time import time_ns

def populate_cards_list(self):
    try:
        cards_list = self.query_one("#builder-cards-list")
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
