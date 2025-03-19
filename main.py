from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, Container, ScrollableContainer
from textual.widgets import (
    Header,
    Footer,
    TabbedContent,
    TabPane,
    Static,
    ListView,
    ListItem,
    Button,
    RadioButton,
    RadioSet,
    Input,
    Label,
)
from textual.message import Message
from textual.binding import Binding
from textual.screen import ModalScreen
from rich_pixels import Pixels
from PIL import Image
import sqlite3
import os
import logging
from time import time_ns

class PokemonCard:
    def __init__(self, id = None, name = None, hp = None, attacks = None, abilities = None, image_path = None):
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

class AddToDeckModal(ModalScreen):
    class DeckSelected(Message):
        """Message sent when a deck is selected."""
        def __init__(self, deck_id: int, deck_name: str) -> None:
            super().__init__()
            self.deck_id = deck_id
            self.deck_name = deck_name
    
    class NewDeckCreated(Message):
        """Message sent when a new deck is created."""
        def __init__(self, deck_id: int, deck_name: str) -> None:
            super().__init__()
            self.deck_id = deck_id
            self.deck_name = deck_name
    
    class Cancelled(Message):
        """Message sent when the operation is cancelled."""
        pass
    
    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("o", "open_actions", "Actions", show=True),
    ]
    
    def __init__(self, card_id: int, card_name: str, db_conn: sqlite3.Connection):
        super().__init__()
        self.card_id = card_id
        self.card_name = card_name
        self.db_conn = db_conn
        self.cursor = db_conn.cursor()
        self.deck_choice = "existing"  # Default to existing decks
    
    def compose(self) -> ComposeResult:
        with Container(id="modal-container"):
            yield Static(f"Add '{self.card_name}' to Deck", id="modal-title")
            
            with Container(id="deck-choice-container"):
                yield RadioSet(
                    RadioButton("Add to existing deck", id="existing-deck"),
                    RadioButton("Create new deck", id="new-deck"),
                )
            
            # Container for existing decks (initially visible)
            with Container(id="existing-decks-container"):
                yield Static("Select a deck:")
                with ScrollableContainer(id="decks-scroll"):
                    yield ListView(*self._get_deck_items(), id="decks-list")
            
            # Container for new deck (initially hidden)
            with Container(id="new-deck-container", classes="hidden"):
                yield Static("Enter new deck name:")
                yield Input(placeholder="Deck name", id="new-deck-name")
                yield Button("Create Deck", variant="primary", id="create-deck-btn")
            
            with Container(id="modal-buttons"):
                yield Button("Cancel", variant="error", id="cancel-btn")

    def _get_deck_items(self) -> list[ListItem]:
        """Get all decks from the database"""
        decks = self.cursor.execute("SELECT id, name FROM decks ORDER BY name").fetchall()

        if not decks:
            return [ListItem(Label("No decks available. Create a new one."))]

        return [ListItem(Label(f"{deck[1]}"), 
                        id=f"deck-{deck[0]}") 
                for deck in decks]


    @on(RadioSet.Changed)
    def on_radio_changed(self, event: RadioSet.Changed) -> None:
        """Handle radio button selection"""
        self.deck_choice = str(event.pressed).split("-")[0]  # "existing" or "new"
        
        # Show/hide appropriate containers
        if self.deck_choice == "existing":
            self.query_one("#existing-decks-container").remove_class("hidden")
            self.query_one("#new-deck-container").add_class("hidden")
        else:
            self.query_one("#existing-decks-container").add_class("hidden")
            self.query_one("#new-deck-container").remove_class("hidden")
    
    @on(ListView.Selected)
    def on_deck_selected(self, event: ListView.Selected) -> None:
        """Handle deck selection from the list"""
        if not event.item.id:
            return  # This is the "No decks available" item
            
        deck_id = int(event.item.id.split("-")[1])
        deck_name = str(event.item.children[0])
        self.post_message(self.DeckSelected(deck_id, deck_name))
        self.dismiss()
    
    @on(Button.Pressed, "#create-deck-btn")
    def on_create_deck(self) -> None:
        """Handle create deck button press"""
        deck_name = self.query_one("#new-deck-name")
        if not deck_name:
            self.query_one("#new-deck-name").focus()
            return
        
        try:
            # Insert the new deck
            self.cursor.execute(
                "INSERT INTO decks (name) VALUES (?)",
                (deck_name,)
            )
            self.db_conn.commit()
            
            # Get the ID of the newly created deck
            deck_id = self.cursor.lastrowid
            
            self.post_message(self.NewDeckCreated(deck_id, str(deck_name)))
            self.dismiss()
        except sqlite3.Error as e:
            # Handle error (in a real app, you'd want better error handling)
            self.app.notify(f"Error creating deck: {str(e)}", severity="error")
    
    @on(Button.Pressed, "#cancel-btn")
    def on_cancel(self) -> None:
        """Handle cancel button press"""
        self.post_message(self.Cancelled())
        self.dismiss()
    
    def action_cancel(self) -> None:
        """Handle escape key press"""
        self.post_message(self.Cancelled())
        self.dismiss()


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
        Binding("o", "open_actions", "Actions"),
    ]

    def __init__(self):
        super().__init__()
        self.db_conn = sqlite3.connect("pokemon_tcg.db")
        self.cursor = self.db_conn.cursor()
        self.current_card = None
        self.current_card_id = None
        self.current_card_name = None
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
        yield Container(
            Label("Select a card and press 'o' for actions", id="status-message"),
            id="status-bar"
        )
        yield Footer()

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

    def action_open_actions(self) -> None:
        """Open the actions menu when 'o' is pressed"""
        if not self.current_card:
            self.notify("No card selected", severity="warning")
            return
            
        # Show a modal with the "Add to Deck" option
        self.push_screen(AddToDeckModal(self.current_card.id, self.current_card.name, self.db_conn))   

    def add_card_to_deck(self, card_id: int, deck_id: int, deck_name: str) -> None:
        """Add a card to a deck"""
        try:
            # Add the card to the selected deck (or increase count if already present)
            self.cursor.execute("""
                INSERT INTO deck_cards (deck_id, card_id, count)
                VALUES (?, ?, 1)
                ON CONFLICT (deck_id, card_id) DO UPDATE SET count = count + 1
            """, (deck_id, card_id))
            
            # Commit the changes
            self.db_conn.commit()
            
            # Update status message
            self.query_one("#status-message", Label).update(
                f"Added {self.current_card.name} to deck: {deck_name}"
            )
            
            # Show notification
            self.notify(f"Added {self.current_card.name} to {deck_name}", severity="information")
            
        except sqlite3.Error as e:
            # Handle database errors
            self.query_one("#status-message", Label).update(f"Error: {str(e)}")
            self.notify(f"Database error: {str(e)}", severity="error")
            self.db_conn.rollback()

    def remove_from_deck(self, deck_id: int, card_id: int):
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
    
    def on_unmount(self) -> None:
        if self.db_conn:
            self.db_conn.close()

    def on_tabs_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        self.logger.info(f"Tab activated: {event.tab.label}")
        if event.tab.label == "Builder":
            self.populate_cards_list()
        if event.tab.label == "Decks":
            self.populate_decks_list()

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
                card_image = self.query_one("#card-image-builder-view", CardImage)
                card_image.update_image(card[5])  # image_path

                stats = self.query_one("#builder-card-stats", Static)
                stats.update(
                    f"""Name: {card[1]}\nHP: {card[2]}\nAttacks: {card[3]}\nAbilities: {card[4]}\n"""
                )

        except Exception as e:
            self.logger.error(f"In builder-cards-list -> Error handling card selection: {e}")

    @on(ListView.Highlighted, '#decks-deck-selector')
    def decks_deck_selector_highlighted(self, event: ListView.Highlighted) -> None:
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

    @on(ListView.Highlighted, '#decks-cards-list')
    def decks_cards_list_highlighted(self, event: ListView.Highlighted) -> None:
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

    @on(ListView.Selected, '#builder-cards-list')
    def builder_card_selected(self, event: ListView.Selected):
        if not event.item.id:
            return

        self.current_card_id = int(event.item.id)
        self.current_card_name = event.item.name
        self.query_one("#status-message", Label).update(
            f"Selected: {self.current_card_name} - Press 'o' for actions"
        )

    @on(AddToDeckModal.DeckSelected)
    def on_deck_selected_from_modal(self, event: AddToDeckModal.DeckSelected) -> None:
        """Handle deck selection from the modal"""
        self.add_card_to_deck(self.current_card_id, event.deck_id, event.deck_name)

    @on(AddToDeckModal.NewDeckCreated)
    def on_new_deck_created(self, event: AddToDeckModal.NewDeckCreated) -> None:
        """Handle new deck creation from the modal"""
        self.add_card_to_deck(self.current_card_id, event.deck_id, event.deck_name)


def main():
    app = PokemonTCGApp()
    try:
        app.run()
    except Exception as e:
        print(f"Application crashed. Check pokemon_tcg.log for details.\n{e}")
        raise


if __name__ == "__main__":
    main()
