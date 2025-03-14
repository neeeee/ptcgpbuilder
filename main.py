from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    Header,
    Footer,
    TabbedContent,
    TabPane,
    Static,
    ListView,
    ListItem,
)
from textual.binding import Binding
from rich_pixels import Pixels
from PIL import Image
import sqlite3
import os
import logging
from time import time_ns

class PokemonCard:
    def __init__(self, id, name, hp, attacks, abilities, image_path):
        self.id = id
        self.name = name
        self.hp = hp
        self.attacks = attacks
        self.abilities = abilities
        self.image_path = image_path


class Deck:
    def __init__(self, id, name, cards=None):
        self.id = id
        self.name = name
        self.cards = cards or {}


class CardImage(Static):
    def __init__(self, image_path: str | None = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.image_path = image_path

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

        self.handler = logging.FileHandler("pokemon_tcg.log")
        self.handler.setLevel(logging.INFO)

        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        self.handler.setFormatter(formatter)
        self.logger.addHandler(self.handler)

    def on_mount(self) -> None:
        try:
            self.update_image(self.image_path)
        except Exception as e:
            self.logger.error(f"Error mounting CardImage: {e}")
            self.update("Error loading image")

    def update_image(self, image_path: str | None) -> None:
        try:
            if image_path and os.path.exists(image_path):
                with Image.open(image_path) as image:
                    terminal_size = os.get_terminal_size()
                    terminal_width = terminal_size.columns
                    terminal_height = terminal_size.lines

                    ratio = min(
                        terminal_width / image.width, terminal_height / image.height
                    )
                    new_size = (int(image.width * ratio), int(image.height * ratio))
                    image = image.resize(new_size, Image.Resampling.LANCZOS)

                    pixels = Pixels.from_image(image)

                    self.update(pixels)
            else:
                self.update("No image available")
        except Exception as e:
            self.logger.error(f"Error updating image: {e}")
            self.update("Error updating image")


class DeckView(Static):
    def compose(self) -> ComposeResult:
        with Horizontal(id="decks-view"):
            yield Vertical(
                Static("Decks"),
                ListView(id="decks-deck-selector"),
                classes="column",
                id="decks-column-1")
            yield Vertical(
                Static("Card List"),
                ListView(id="decks-cards-list"),
                Static("Card Stats"),
                Static("", id="decks-card-stats"),
            )
            yield Vertical(
                Static("Card Image"),
                CardImage(id="card-image-decks-view"),
                id="decks-column-3")


class BuilderView(Static):
    def compose(self) -> ComposeResult:
        yield Horizontal(
            Vertical(
                Static("Cards"),
                ListView(id="builder-cards-list"),
                classes="column",
            ),
            Vertical(
                Static("Card Stats"),
                Static("", id="builder-card-stats"),
            ),
            Vertical(
                Static("Card Image"),
                CardImage(id="card-image-builder-view")),
            id="builder-view",
        )


class PokemonTCGApp(App):
    CSS_PATH = "pokemontcgapp_css.tcss"

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("o", "show_options", "Options"),
        Binding("a", "add_to_deck", "Add to Deck"),
    ]

    def __init__(self):
        super().__init__()
        self.db_conn = sqlite3.connect("pokemon_tcg.db")
        self.current_card = None
        self.current_deck = None
        self.sort_mode = "name"

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        # Create a file handler and set the logging level to INFO
        self.handler = logging.FileHandler("pokemon_tcg.log")
        self.handler.setLevel(logging.INFO)

        # Create a formatter and attach it to the handler
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        self.handler.setFormatter(formatter)
        self.logger.addHandler(self.handler)

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent():
            with TabPane("Decks", id="decks"):
                yield DeckView()
            with TabPane("Builder", id="builder"):
                yield BuilderView()
        yield Footer()

    def on_key(self, event) -> None:
        if event.key == "escape":
            # Focus the tab bar
            self.query_one(TabbedContent).focus()
        else:
            # Check if the tab bar is focused
            tabbed_content = self.query_one(TabbedContent)
            if tabbed_content.has_focus:
                if event.key == "b":
                    # Select the previous tab
                    tabbed_content.active = "builder"
                elif event.key == "d":
                    # Select the next tab
                    tabbed_content.active = "decks"
            else:
                # Handle navigation within the content
                if event.key == "h":
                    # Focus the previous column
                    self.action_focus_previous_column()
                elif event.key == "l":
                    # Focus the next column
                    self.action_focus_next_column()
                elif event.key == "j":
                    # Focus the next row
                    self.action_focus_next()
                elif event.key == "k":
                    # Focus the previous row
                    self.action_focus_previous()


    def action_focus_previous_column(self) -> None:
        focused_widget = self.focused
        if focused_widget:
            parent = focused_widget.parent
            if isinstance(parent, Horizontal):
                index = parent.children.index(focused_widget)
                if index > 0:
                    parent.children[index - 1].focus()

    def action_focus_next_column(self) -> None:
        focused_widget = self.focused
        if focused_widget:
            parent = focused_widget.parent
            if isinstance(parent, Horizontal):
                index = parent.children.index(focused_widget)
                if index < len(parent.children) - 1:
                    parent.children[index + 1].focus()

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

                self.logger.info(f"Added card to list: {card[1]}")

            self.logger.info(f"Populated cards list with {len(cards)} cards")
        except Exception as e:
            self.logger.error(f"Error populating cards list: {e}")
            raise

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

                self.logger.info(f"Added deck to list: {deck[1]}")
            self.logger.info(f"Populated decks list with {len(decks)} decks")

        except Exception as e:
            self.logger.error(f"Error populating decks list: {e}")
            self.logger.error(f"Error populating decks cards list: {e}")

    def on_mount(self) -> None:
        try:
            self.logger.info("Application mounting")
            self.populate_cards_list()
            self.populate_decks_list()

        except Exception as e:
            self.logger.error(f"Error in on_mount: {e}")
            raise

    def on_tabs_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        self.logger.info(f"Tab activated: {event.tab.label}")
        if event.tab.label == "Builder":
            self.populate_cards_list()
        if event.tab.label == "Decks":
            self.populate_decks_list()

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if event.list_view.id == "builder-cards-list":
            try:
                card_id = getattr(event.item, "card_id", None)
                if card_id is None:
                    return

                cursor = self.db_conn.cursor()
                query = """SELECT
                            id, name, hp, attacks, abilities, image_path
                        FROM
                            cards
                        WHERE
                            id = ?;
                        """
                card = cursor.execute(query, (card_id,)).fetchone()

                if card:
                    self.current_card = PokemonCard(*card)
                    card_image = self.query_one("#card-image-builder-view", CardImage)
                    card_image.update_image(card[5])  # image_path

                    stats = self.query_one("#builder-card-stats", Static)
                    stats.update(
                        f"""Name: {card[1]}\nHP: {card[2]}\nAttacks: {card[3]}\nAbilities: {card[4]}\n"""
                    )
            except Exception as e:
                self.logger.error(f"In builder-cards-list -> Error handling card selection: {e}")

        elif event.list_view.id == "decks-deck-selector":
            try:
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

                decks_cards_list = self.query_one("#decks-cards-list")

                for card in cards:
                    unique_id = f"decks-card-list-{str(card[0]).replace(" ", "_")}-{time_ns()}"
                    item = ListItem(
                        Static(card[2]),
                        id=unique_id,
                    )
                    setattr(item, "card_id", card[1])
                    decks_cards_list.mount(item)
            except Exception as e:
                self.logger.error(f"In decks-deck-selector -> Error handling card selection: {e}")

        elif event.list_view.id == "decks-cards-list":
            try:
                card_id = getattr(event.item, "card_id", None)
                # self.logger.info(f"Card id {card_id}")
                if card_id is None:
                    return

                cursor = self.db_conn.cursor()
                query = """SELECT
                            id, name, hp, attacks, abilities, image_path
                        FROM
                            cards
                        WHERE
                            id = ?;
                        """
                card = cursor.execute(query, (card_id,)).fetchone()
                # self.logger.info(f"Card id {card[0]} image_path {card[5]}")

                if card:
                    self.current_card = PokemonCard(*card)
                    card_image = self.query_one("#card-image-decks-view", CardImage)
                    stats = self.query_one("#decks-card-stats", Static)
                    card_image.update_image(card[5])

                    stats.update(
                        f"""Name: {card[1]}\nHP: {card[2]}\nAttacks: {card[3]}\nAbilities: {card[4]}\n"""
                    )
                    # self.logger.info(f"Stats exists? {stats}")

            except Exception as e:
                self.logger.error(f"In 'decks-cards-list' -> Error handling card selection: {e}")


def main():
    app = PokemonTCGApp()
    try:
        app.run()
    except Exception as e:
        print(f"Application crashed. Check pokemon_tcg.log for details.\n{e}")
        raise


if __name__ == "__main__":
    main()
