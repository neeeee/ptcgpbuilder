from textual import on
from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import (
    Header,
    Footer,
    TabbedContent,
    TabPane,
    Static,
    ListView,
    ListItem,
    Label,
)
from textual.binding import Binding
import sqlite3
from utils.logger import Logger
from time import time_ns

from views.BuilderView import BuilderView
from views.DeckView import DeckView
from views.PokemonCard import PokemonCard, CardImage
from views.AddToDeckModal import AddToDeckModal
from utils.card_functions.card_management import CardManagement

logger = Logger('log/pokemon_tcg.log')

class PokemonTCGApp(App):
    CSS_PATH = "tcss/pokemontcgapp_css.tcss"

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("o", "open_actions", "Actions"),
    ]

    def __init__(self):
        super().__init__()
        self.db_conn = sqlite3.connect("db/pokemon_tcg.db")
        self.db_conn.row_factory = sqlite3.Row
        self.cursor = self.db_conn.cursor()
        self.current_card = None
        self.current_card_id = None
        self.current_card_name = None
        self.current_deck = None
        self.current_deck_id = None
        self.current_deck_name = None
        self.sort_mode = "name"
        self.card_management = CardManagement(self.db_conn, self.cursor, self)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with TabbedContent():
            with TabPane("Decks", id="decks"):
                yield DeckView()
            with TabPane("Builder", id="builder"):
                yield BuilderView()
        yield Container(
            Label("Select a card and press 'o' for actions", id="status-message"),
            id="status-bar"
        )
        yield Footer()

    def action_open_actions(self) -> None:
        """Open the actions menu when 'o' is pressed"""
        if not self.current_card:
            self.notify("No card selected", severity="warning")
            return
 
        # Show a modal with the "Add to Deck" option
        self.push_screen(AddToDeckModal(self.current_card_id, self.current_deck_id, self.db_conn))

    def on_mount(self) -> None:
        try:
            self.card_management.populate_cards_list()
            self.card_management.populate_decks_list()

        except Exception:
            raise
    
    def on_unmount(self) -> None:
        if self.db_conn:
            self.db_conn.close()

    def on_tabs_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        if event.tab.label == "Builder":
            self.card_management.populate_cards_list()
        if event.tab.label == "Decks":
            self.card_management.populate_decks_list()

    @on(ListView.Highlighted, '#builder-cards-list')
    def builder_cards_list_highlighted(self, event: ListView.Highlighted) -> None:
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
                self.current_card_id = card[0]
                self.current_card_name = card[1]
                card_image = self.query_one("#card-image-builder-view", CardImage)
                card_image.update_image(card[5])  # image_path

                stats = self.query_one("#builder-card-stats", Static)
                stats.update(
                    f"""Name: {card[1]}\nHP: {card[2]}\nAttacks: {card[3]}\nAbilities: {card[4]}\n"""
                )

        except Exception:
            raise

    @on(ListView.Highlighted, '#decks-deck-selector')
    def decks_deck_selector_highlighted(self, event: ListView.Highlighted) -> None:
        try:
            decks_cards_list = self.query_one("#decks-cards-list")
            decks_cards_list.remove_children()
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
                unique_id = f"decks-card-list-{str(card[0]).replace(" ", "_")}-{time_ns()}"
                item = ListItem(
                    Static(card[2]),
                    id=unique_id,
                )
                setattr(item, "card_id", card[1])
                decks_cards_list.mount(item)

        except Exception:
            raise

    @on(ListView.Highlighted, '#decks-cards-list')
    def decks_cards_list_highlighted(self, event: ListView.Highlighted) -> None:
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
                card_image = self.query_one("#card-image-decks-view", CardImage)
                stats = self.query_one("#decks-card-stats", Static)
                self.current_card_id = int(card[0])
                self.current_card_name = card[1]
                card_image.update_image(card[5])

                stats.update(
                    f"""Name: {card[1]}\nHP: {card[2]}\nAttacks: {card[3]}\nAbilities: {card[4]}\n"""
                )

        except Exception:
            raise

    @on(ListView.Selected, '#builder-cards-list')
    def builder_card_selected(self, event: ListView.Selected):
        if not event.item.id:
            return
        label: Label = event.item.query_one(Label)
        self.current_card_name = str(label.renderable) 

        self.query_one("#status-message", Label).update(
            f"Selected: {self.current_card_name} - Press 'o' for actions"
        )

    @on(AddToDeckModal.DeckSelected)
    def on_deck_selected_from_modal(self, event: AddToDeckModal.DeckSelected) -> None:
        """Handle deck selection from the modal"""
        self.card_management.add_card_to_deck(self.current_card_id, event.deck_id, event.deck_name)

    @on(AddToDeckModal.NewDeckCreated)
    def on_new_deck_created(self, event: AddToDeckModal.NewDeckCreated) -> None:
        """Handle new deck creation from the modal"""
        self.card_management.add_card_to_deck(self.current_card_id, event.deck_id, event.deck_name)

            # self.query_one("#status-message", Label).update(
            #     f"Added {card_id} to deck: {deck_name}"
            # )

def main():
    app = PokemonTCGApp()
    try:
        app.run()
    except Exception as e:
        print(f"Application crashed. Check pokemon_tcg.log for details.\n{e}")
        raise

if __name__ == "__main__":
    main()
