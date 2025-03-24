from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    Static,
    ListView,
)

from views.PokemonCard import CardImage

class BuilderView(Static):
    def compose(self) -> ComposeResult:
        with Horizontal(id="builder-view"):
            yield Vertical(
                Static("Cards"),
                ListView(id="builder-cards-list"),
                classes="column",
            )
            yield Vertical(
                Static("Card Stats"),
                Static("", id="builder-card-stats"),
            )
            yield Vertical(
                Static("Card Image"),
                CardImage(id="card-image-builder-view"))

