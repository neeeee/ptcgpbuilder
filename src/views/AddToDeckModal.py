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
    Select,
)

from textual.message import Message
from textual.binding import Binding
from time import time_ns

class AddToDeckModal(ModalScreen):
    class DeckSelected(Message):
        """Message sent when a deck is selected."""
        def __init__(self, deck_id, deck_name, quantity=1) -> None:
            super().__init__()
            self.deck_id = deck_id
            self.deck_name = deck_name
            self.quantity = quantity
    
    class NewDeckCreated(Message):
        """Message sent when a new deck is created."""
        def __init__(self, deck_id, deck_name, quantity=1) -> None:
            super().__init__()
            self.deck_id = deck_id
            self.deck_name = deck_name
            self.quantity = quantity
    
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
        self.quantity = 1  # Default quantity
        self.decks_data = self._get_decks_from_db()  # Store deck data for filtering
        self.all_decks = self._create_deck_list_items()  # Create list items from data
    
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
                yield Input(placeholder="Search decks...", id="deck-search")
                with ScrollableContainer(id="decks-scroll"):
                    yield ListView(*self.all_decks, id="decks-list")
            
            # Container for new deck (initially hidden)
            with Container(id="new-deck-container", classes="hidden"):
                yield Static("Enter new deck name:")
                yield Input(placeholder="Deck name", id="new-deck-name")
                yield Button("Create Deck", variant="primary", id="create-deck-btn")
            
            # Quantity selector
            with Container(id="quantity-container"):
                yield Static("Quantity:")
                yield Select(
                    options=[
                        ("1", "1"),
                        ("2", "2"),
                    ],
                    value="1",
                    id="quantity-selector"
                )
            
            with Container(id="modal-buttons"):
                yield Button("Cancel", variant="error", id="cancel-btn")

    def _get_decks_from_db(self) -> list[tuple]:
        """Get all decks from the database"""
        decks = self.cursor.execute("SELECT id, name FROM decks ORDER BY name").fetchall()
        return decks

    def _create_deck_list_items(self) -> list[ListItem]:
        """Create list items from deck data"""
        if not self.decks_data:
            return [ListItem(Label("No decks available. Create a new one."))]
        
        return [
            ListItem(Label(f"{deck[1]}"), id=f"deck-{deck[0]}")
            for deck in self.decks_data
        ]

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
        quantity = int(self.query_one("#quantity-selector", Select).value)
        self.post_message(self.DeckSelected(deck_id, deck_name, quantity))
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
            quantity = int(self.query_one("#quantity-selector", Select).value)
            
            self.post_message(self.NewDeckCreated(deck_id, deck_name, quantity))
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

    @on(Input.Changed, "#deck-search")
    def on_search_changed(self, event: Input.Changed) -> None:
        """Handle search input changes"""
        search_text = event.value.lower()
        decks_list = self.query_one("#decks-list")
        decks_list.clear()
        
        if not search_text:
            # If search is empty, show all decks
            decks_list.append(*self.all_decks)
        else:
            # Filter decks based on search text
            filtered_decks = []
            for deck_data in self.decks_data:
                deck_name = deck_data[1].lower()
                if search_text in deck_name:
                    # Create a unique ID for each ListItem
                    unique_id = f"deck-{deck_data[0]}-{time_ns()}"
                    filtered_decks.append(
                        ListItem(Label(f"{deck_data[1]}"), id=unique_id)
                    )
            decks_list.append(*filtered_decks)
            
        # If no decks match the search, show a message
        if not decks_list.children:
            decks_list.append(ListItem(Label("No decks found matching search.")))

