from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    Static,
    ListView,
)
from views.PokemonCard import CardImage

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
                id="decks-column-2")
            yield Vertical(
                Static("Card Stats"),
                Static("", id="decks-card-stats"),
                Static("Card Image"),
                CardImage(id="card-image-decks-view"),
                id="decks-column-3")