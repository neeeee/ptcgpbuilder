from textual import on
from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import (
    Header,
    Footer,
    TabbedContent,
    TabPane,
    ListView,
    Label,
)
from textual.binding import Binding
import sqlite3
# from utils.logger import Logger

from views.BuilderView import BuilderView
from views.DeckView import DeckView
from views.AddToDeckModal import AddToDeckModal
from views.CreateEmptyDeckModal import CreateEmptyDeckModal
from utils.card_functions.card_management import CardManagement
from utils.db_management import DBManagement


class PokemonTCGApp(App):
    CSS_PATH = "tcss/pokemontcgapp_css.tcss"

    BINDINGS = [
        Binding("q", "quit", "Quit App"),
        Binding("o", "open_actions", "Card Actions"),
        Binding("2", "show_tab('builder')", "Show Builder"),
        Binding("1", "show_tab('decks')", "Show Decks"),
        Binding("ctrl+r", "rename_deck", "Rename Deck"),
        Binding("ctrl+d", "delete_deck", "Delete Deck"),
        Binding("ctrl+y", "remove_from_deck", "Remove from Deck"),
        Binding("ctrl+n", "create_empty_deck", "Create Deck"),
    ]

    def __init__(self):
        super().__init__()
        self.db_conn = sqlite3.connect("src/db/pokemon_tcg.db")
        self.db_conn.row_factory = sqlite3.Row
        self.cursor = self.db_conn.cursor()
        # self.logger = Logger('log')
        self.current_card = ""
        self.current_card_id = 0
        self.current_card_name = ""
        self.current_deck = ""
        self.current_deck_id = 0
        self.current_deck_name = ""
        self.sort_mode = "name"
        self.card_management = CardManagement(self.db_conn, self.cursor, self)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with TabbedContent(id="tabs"):
            with TabPane("Decks", id="decks"):
                yield DeckView()
            with TabPane("Builder", id="builder"):
                yield BuilderView()
        yield Container(
            Label("Select a card and press 'o' for actions", id="status-message"),
            id="status-bar"
        )
        yield Footer()

    def action_show_tab(self, tab: str) -> None:
        self.get_child_by_type(TabbedContent).active = tab

    def action_open_actions(self) -> None:
        if not self.current_card:
            self.notify("No card selected", severity="warning")
            return
        self.push_screen(AddToDeckModal(self.current_card_id, self.current_deck_id, self.db_conn))

    def action_delete_deck(self) -> None:
        self.card_management.delete_deck(self.current_deck_id)

    def action_remove_from_deck(self) -> None:
        self.card_management.remove_from_deck(self.current_deck_id, self.current_card_id)

    def action_create_empty_deck(self) -> None:
        self.push_screen(CreateEmptyDeckModal(self))

    def action_rename_deck(self) -> None:
        """Open the modal to rename the currently selected deck"""
        # Get the current selected deck from the deck selector
        deck_selector = self.query_one("#decks-deck-selector")
        if deck_selector.index is None:
            self.notify("No deck selected", severity="warning")
            return
        
        # In Textual 2.1.0, we need to use the highlighted_child property
        deck_item = deck_selector.highlighted_child
        self.current_deck_id = getattr(deck_item, "deck_id", None)
        self.current_deck_name = deck_item.children[0].renderable
        
        if not self.current_deck_id:
            self.notify("No valid deck selected", severity="warning")
            return
            
        # Open the modal for renaming
        self.push_screen(CreateEmptyDeckModal(self, self.current_deck_id, self.current_deck_name))

    @on(TabbedContent.TabActivated, "#tabs", pane="#decks")
    def update_deck_view_decks_list(self) -> None:
        self.card_management.populate_decks_list()

    @on(TabbedContent.TabActivated, "#tabs", pane="#builder")
    def update_builder_view_cards_list(self) -> None:
        self.card_management.populate_cards_list()

    @on(ListView.Highlighted, '#builder-cards-list')
    def builder_cards_list_highlighted(self, event: ListView.Highlighted) -> None:
        self.card_management.show_builder_cards_list_info(event)
 
    @on(ListView.Highlighted, '#decks-deck-selector')
    def decks_deck_selector_highlighted(self, event: ListView.Highlighted) -> None:
        self.card_management.populate_decks_cards_list(event)

    @on(ListView.Highlighted, '#decks-cards-list')
    def decks_cards_list_highlighted(self, event: ListView.Highlighted) -> None:
        self.card_management.show_decks_cards_list_info(event)

    @on(AddToDeckModal.DeckSelected)
    def on_deck_selected_from_modal(self, event: AddToDeckModal.DeckSelected) -> None:
        """Handle deck selection from the modal"""
        self.card_management.add_card_to_deck(self.current_card_id, event.deck_id, event.deck_name, self.current_card_name)

    @on(AddToDeckModal.NewDeckCreated)
    def on_new_deck_created(self, event: AddToDeckModal.NewDeckCreated) -> None:
        """Handle new deck creation from the modal"""
        self.card_management.add_card_to_deck(self.current_card_id, event.deck_id, event.deck_name, self.current_card_name)

        self.query_one("#status-message", Label).update(
            f"Added {self.current_card_id} to deck: {event.deck_name}"
        )

    @on(CreateEmptyDeckModal.DeckCreated)
    def on_deck_created(self, event: CreateEmptyDeckModal.DeckCreated) -> None:
        """Handle deck creation or rename from the modal"""
        # Refresh the deck list to show the new/renamed deck
        self.card_management.populate_decks_list()
        
        # Update status message
        action = "renamed" if event.deck_id else "created"
        self.query_one("#status-message", Label).update(
            f"Deck {action}: {event.deck_name}"
        )

    def on_mount(self) -> None:
        try:
            self.card_management.populate_cards_list()
            self.card_management.populate_decks_list()
        except Exception:
            raise
 
    def on_unmount(self) -> None:
        if self.db_conn:
            self.db_conn.close()

def main():
    app = PokemonTCGApp()
    try:
        app.run()
    except Exception as e:
        print(f"Application crashed. Check pokemon_tcg.log for details.\n{e}")
        raise

if __name__ == "__main__":
    main()
