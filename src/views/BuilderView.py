from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, Grid, Container
from textual.widgets import (
    Static,
    ListView,
    Input,
    Select,
    RadioSet,
    RadioButton,
    Button,
)

from views.PokemonCard import CardImage

class BuilderView(Static):
    def compose(self) -> ComposeResult:
        with Container(id="builder-container"):
            # Column 1 - Filters and card list
            with Vertical(id="column-1"):
                with Container(id="filter-controls"):
                    yield Static("Filter Cards", id="filter-title")
                    with Grid(id="filter-grid"):
                        # Set, Name, Category labels
                        yield Static("Set:")
                        yield Static("Name:")
                        yield Static("Category:")
                        
                        # Pokémon Type label (new)
                        yield Static("Type:")
                        
                        # Set filter dropdown
                        yield Select(
                            options=[],  # Empty options - will be populated later
                            id="set-filter"
                            # No initial value - will be set after options are populated
                        )
                        
                        # Name filter input
                        yield Input(placeholder="Filter by name", id="name-filter")
                        
                        # Category filter (renamed from type filter)
                        with RadioSet(id="category-filter"):
                            yield RadioButton("All", id="category-all", value=True)
                            yield RadioButton("Pokémon", id="category-pokemon")
                            yield RadioButton("Trainer", id="category-trainer")
                        
                        # Pokémon Type filter dropdown (new)
                        yield Select(
                            options=[
                                ("All", "all"),
                                ("Water", "water"),
                                ("Grass", "grass"),
                                ("Fire", "fire"),
                                ("Electric", "electric"),
                                ("Fighting", "fighting"),
                                ("Psychic", "psychic"),
                                ("Dark", "dark"),
                                ("Metal", "metal"),
                                ("Colorless", "colorless"),
                            ],
                            id="type-filter",
                            value="all"
                        )
                        
                        # Filter buttons
                        yield Button("Apply Filters", id="apply-filters", variant="primary")
                        yield Button("Clear Filters", id="clear-filters")
                
                yield Static("Cards", id="builder-cards-title")
                yield ListView(id="builder-cards-list")
            
            # Column 2 - Card stats and image
            with Vertical(id="column-2"):
                yield Static("Card Stats", id="builder-card-stats-title")
                yield Static("", id="builder-card-stats")
                yield Static("Card Image", id="builder-card-image-title")
                yield CardImage(id="card-image-builder-view")

