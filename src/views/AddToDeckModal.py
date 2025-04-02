import sqlite3
from textual import on
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import Container, ScrollableContainer

from textual.widgets import (
    Static,
    ListView,
    ListItem,
    RadioSet,
    RadioButton,
    Label,
    Input,
    Button,
)

from textual.message import Message
from textual.binding import Binding

class AddToDeckModal(ModalScreen):
    class DeckSelected(Message):
        """Message sent when a deck is selected."""
        def __init__(self, deck_id, deck_name) -> None:
            super().__init__()
            self.deck_id = deck_id
            self.deck_name = deck_name
    
    class NewDeckCreated(Message):
        """Message sent when a new deck is created."""
        def __init__(self, deck_id, deck_name) -> None:
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
    
    def __init__(self, card_id, card_name, db_conn: sqlite3.Connection):
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
                    yield ListView(*self._get_decks_from_db(), id="decks-list")
            
            # Container for new deck (initially hidden)
            with Container(id="new-deck-container", classes="hidden"):
                yield Static("Enter new deck name:")
                yield Input(placeholder="Deck name", id="new-deck-name")
                yield Button("Create Deck", variant="primary", id="create-deck-btn")
            
            with Container(id="modal-buttons"):
                yield Button("Cancel", variant="error", id="cancel-btn")

    def _get_decks_from_db(self) -> list[ListItem]:
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
        selected_value = event.index
        # self.deck_choice = str(event.pressed).split("-")[0]  # "existing" or "new"
        
        # Show/hide appropriate containers
        if selected_value == 0:
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
        label: Label = event.item.query_one(Label)
        deck_name = str(label.renderable)
        self.post_message(self.DeckSelected(deck_id, deck_name))
        self.dismiss()
    
    @on(Button.Pressed, "#create-deck-btn")
    def on_create_deck(self) -> None:
        """Handle create deck button press"""
        deck_name_input = self.query_one("#new-deck-name", Input)
        deck_name = deck_name_input.value
        
        if not deck_name:
            deck_name_input.focus()
            return
        
        try:
            # Insert the new deck
            self.cursor.execute(
                "INSERT INTO decks (name) VALUES (?)",
                (deck_name,)  # Use the string value, not the Input widget
            )
            self.db_conn.commit()
            
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

