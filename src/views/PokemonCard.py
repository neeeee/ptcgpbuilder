import os
from textual.widgets import (
    Static,
)
from rich_pixels import Pixels
from PIL import Image

class PokemonCard:
    def __init__(self, id = None,
                 name = None,
                 hp = None,
                 attacks = None,
                 abilities = None,
                 image_path = None):
        self.id = id
        self.name = name
        self.hp = hp
        self.attacks = attacks
        self.abilities = abilities
        self.image_path = image_path

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

