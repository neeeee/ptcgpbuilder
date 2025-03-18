from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import Container, ScrollableContainer
from textual.widgets import (
    Header, Footer, ListView, ListItem, Button, Input, Label, 
    Select, SelectionList, Static, RadioSet, RadioButton
)
from textual.screen import Screen, ModalScreen
from textual.binding import Binding
from textual.message import Message
import sqlite3
from typing import Optional, List, Dict

class AddToDeckModal(ModalScreen):
    """Modal screen for adding a card to a deck."""
    
    class DeckSelected(Message):
        """Message sent when a deck is selected."""
        def __init__(self, deck_id: int, deck_name: str) -> None:
            self.deck_id = deck_id
            self.deck_name = deck_name
            super().__init__()
    
    class NewDeckCreated(Message):
        """Message sent when a new deck is created."""
        def __init__(self, deck_id: int, deck_name: str) -> None:
            self.deck_id = deck_id
            self.deck_name = deck_name
            super().__init__()
    
    class Cancelled(Message):
        """Message sent when the operation is cancelled."""
        pass
    
    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]
    
    def __init__(self, card_id: int, card_name: str, conn: sqlite3.Connection):
        super().__init__()
        self.card_id = card_id
        self.card_name = card_name
        self.conn = conn
        self.cursor = conn.cursor()
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
        self.cursor.execute("SELECT id, name FROM decks ORDER BY name")
        decks = self.cursor.fetchall()
        if not decks:
            return [ListItem(Label("No decks available. Create a new one."))]
        return [ListItem(Label(f"{deck['name']}"), 
                        id=f"deck-{deck['id']}") 
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
            self.conn.commit()
            
            # Get the ID of the newly created deck
            deck_id = self.cursor.lastrowid
            
            self.post_message(self.NewDeckCreated(deck_id, deck_name))
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


class PokemonTCGApp(App):
    CSS = """
    ListView {
        width: 100%;
        height: 1fr;
        border: solid green;
    }
    
    #card-list {
        height: 1fr;
    }
    
    #status-bar {
        height: 1;
        dock: bottom;
    }
    
    /* Modal styling */
    #modal-container {
        width: 60%;
        height: auto;
        padding: 1 2;
        background: $surface;
        border: thick $primary;
        color: $text;
    }
    
    #modal-title {
        text-align: center;
        text-style: bold;
        width: 100%;
        margin-bottom: 1;
    }
    
    #decks-scroll {
        height: 10;
        width: 100%;
        border: solid $primary;
    }
    
    #modal-buttons {
        margin-top: 1;
        width: 100%;
        align-horizontal: right;
    }
    
    .hidden {
        display: none;
    }
    
    #new-deck-name {
        margin-bottom: 1;
    }
    
    #deck-choice-container {
        margin-bottom: 1;
    }
    """

    BINDINGS = [
        Binding("o", "open_actions", "Actions", show=True),
    ]

    def __init__(self):
        super().__init__()
        # Connect to the database
        self.conn = sqlite3.connect("pokemon_tcg.db")
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.selected_card_id = None
        self.selected_card_name = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        
        # Card list
        yield Container(
            Label("Available cards (highlight and press 'o' for actions):"),
            ListView(*self.get_card_items(), id="card-list")
        )
        
        # Status bar
        yield Container(
            Label("Select a card and press 'o' for actions", id="status-message"),
            id="status-bar"
        )
        
        yield Footer()

    def get_card_items(self) -> list[ListItem]:
        """Get all cards from the database"""
        self.cursor.execute("SELECT id, name FROM cards")
        cards = self.cursor.fetchall()
        return [ListItem(Label(f"{card['name']} (ID: {card['id']})"), 
                         id=f"card-{card['id']}") 
                for card in cards]

    @on(ListView.Highlighted, "#card-list")
    def on_card_highlighted(self, event: ListView.Highlighted) -> None:
        """Handle card highlighting"""
        # Extract card ID from the item ID (format: "card-{id}")
        if not event.item.id:
            return
            
        card_id = int(event.item.id.split("-")[1])
        # Extract card name from the label
        card_name = event.item.children[0].renderable.split(" (ID:")[0]
        
        self.selected_card_id = card_id
        self.selected_card_name = card_name
        
        self.query_one("#status-message", Label).update(
            f"Selected: {card_name} - Press 'o' for actions"
        )

    def action_open_actions(self) -> None:
        """Open the actions menu when 'o' is pressed"""
        if not self.selected_card_id:
            self.notify("No card selected", severity="warning")
            return
            
        # Show a modal with the "Add to Deck" option
        self.push_screen(AddToDeckModal(self.selected_card_id, self.selected_card_name, self.conn))

    @on(AddToDeckModal.DeckSelected)
    def on_deck_selected_from_modal(self, event: AddToDeckModal.DeckSelected) -> None:
        """Handle deck selection from the modal"""
        self.add_card_to_deck(self.selected_card_id, event.deck_id, event.deck_name)

    @on(AddToDeckModal.NewDeckCreated)
    def on_new_deck_created(self, event: AddToDeckModal.NewDeckCreated) -> None:
        """Handle new deck creation from the modal"""
        self.add_card_to_deck(self.selected_card_id, event.deck_id, event.deck_name)

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
            self.conn.commit()
            
            # Update status message
            self.query_one("#status-message", Label).update(
                f"Added {self.selected_card_name} to deck: {deck_name}"
            )
            
            # Show notification
            self.notify(f"Added {self.selected_card_name} to {deck_name}", severity="information")
            
        except sqlite3.Error as e:
            # Handle database errors
            self.query_one("#status-message", Label).update(f"Error: {str(e)}")
            self.notify(f"Database error: {str(e)}", severity="error")
            self.conn.rollback()

    def on_unmount(self) -> None:
        """Close the database connection when the app exits"""
        if self.conn:
            self.conn.close()

if __name__ == "__main__":
    app = PokemonTCGApp()
    app.run()

