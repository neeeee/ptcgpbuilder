import os
from textual.widgets import (
    Static,
)
from rich_pixels import Pixels
from PIL import Image
from textual.app import ComposeResult
from textual.containers import Horizontal

class PokemonCard:
    def __init__(self, id = None,
                 name = None,
                 set_name = None,
                 hp = None,
                 type = None,
                 image_path = None,
                 moves = None,
                 weakness = None,
                 retreat_cost = None,
                 card_type = None,
                 description = None,
                 rule_text = None):
        self.id = id
        self.name = name
        self.set_name = set_name
        self.hp = hp
        self.type = type
        self.image_path = image_path
        self.moves = moves
        self.weakness = weakness
        self.retreat_cost = retreat_cost
        self.card_type = card_type
        self.description = description
        self.rule_text = rule_text

class TypeIcon(Static):
    """A small widget to display a Pokémon type icon"""
    
    def __init__(self, type_name: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.type_name = type_name
        
    def on_mount(self) -> None:
        self.load_icon()
        
    def load_icon(self) -> None:
        from utils.card_functions.card_management import CardManagement
        
        try:
            image_path = CardManagement.get_type_image_path(self.type_name)
            if image_path and os.path.exists(image_path):
                with Image.open(image_path) as img:
                    # Make type icons small
                    img = img.resize((16, 16), Image.Resampling.LANCZOS)
                    pixels = Pixels.from_image(img)
                    self.update(pixels)
            else:
                self.update(self.type_name)
        except Exception as e:
            self.update(self.type_name)

class TypeIconDisplay(Horizontal):
    """A widget to display multiple type icons in a row"""
    
    def __init__(self, type_names: list, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.type_names = type_names
        
    def compose(self) -> ComposeResult:
        for type_name in self.type_names:
            yield TypeIcon(type_name)

class CardImage(Static):
    def __init__(self, image_path: str | None = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.image_path = image_path

    def on_mount(self) -> None:
        try:
            self.update_image(self.image_path)
        except Exception:
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
        except Exception:
            self.update("Error updating image")

