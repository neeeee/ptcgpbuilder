from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import Container
from textual.widgets import (
    Static,
    Input,
    Button,
)

from textual.message import Message
from textual.binding import Binding

class CreateEmptyDeckModal(ModalScreen):
    """Modal for creating a new empty deck or renaming an existing deck."""
    
    # Define messages
    class DeckCreated(Message):
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
        Binding("enter", "submit", "Submit"),
    ]
    
    def __init__(self, app=None, deck_id=None, deck_name=None):
        """Initialize modal with optional deck ID and name for renaming."""
        super().__init__()
        self._app = app
        self.deck_id = deck_id
        self.deck_name = deck_name
        self.is_rename_mode = deck_id is not None
    
    def compose(self) -> ComposeResult:
        """Compose the modal with input and buttons."""
        title = "Rename Deck" if self.is_rename_mode else "Create Empty Deck"
        btn_text = "Rename" if self.is_rename_mode else "Create"
        
        yield Container(
            Static(title),
            Input(
                value=self.deck_name if self.is_rename_mode else "", 
                placeholder="Deck Name"
            ),
            Button(btn_text, id="submit-btn", variant="primary"),
            Button("Cancel", id="cancel-btn"),
            id="modal-container",
        )
    
    def on_button_pressed(self, event) -> None:
        """Handle button press events."""
        button_id = event.button.id
        if button_id == "submit-btn":
            self.action_submit()
        elif button_id == "cancel-btn":
            self.action_cancel()
    
    def action_submit(self) -> None:
        """Submit the form - either create a new deck or rename an existing one."""
        deck_name = self.query_one(Input).value
        
        if not deck_name:
            self._app.notify("Deck name is required", severity="warning")
            return
        
        if self.is_rename_mode:
            # Rename existing deck
            self._app.card_management.rename_deck(self.deck_id, deck_name)
            self.dismiss(self.DeckCreated(self.deck_id, deck_name))
        else:
            # Create new deck
            self._app.card_management.create_empty_deck(deck_name)
            # We don't have the deck_id yet, but we'll update the UI through the card_management
            self.dismiss(self.DeckCreated(None, deck_name))
    
    def action_cancel(self) -> None:
        """Cancel the operation."""
        self.dismiss(self.Cancelled())

    def action_rename_deck(self) -> None:
        """Handle renaming the currently highlighted deck"""
        deck_selector = self._app.query_one("#decks-deck-selector")
        if deck_selector.index is None:
            self._app.notify("No deck selected", severity="warning")
            return
        
        # In Textual 2.1.0, we need to use the highlighted_child property
        deck_item = deck_selector.highlighted_child
        self.deck_id = deck_item.deck_id
        self.deck_name = deck_item.query_one(Static).renderable
        
        self._app.card_management.rename_deck(self.deck_id, self.deck_name)
