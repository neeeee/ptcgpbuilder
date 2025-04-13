# Pokemon TCG Pocket Builder

A deck building tool for Pokemon TCG Pocket that allows you to build, manage, and analyze your decks.

## Features

- **Card Database**: Browse and search through Pokemon TCG Pocket cards
- **Deck Builder**: Build and save multiple decks
- **Card Scraper**: Scrape card data from Serebii.net
- **Set Management**: Organize cards by sets (Shining Revelry, Genetic Apex, etc.)
- **TUI Interface**: Easy-to-use terminal user interface

## Installation

```bash
# Clone the repository
git clone https://github.com/neeeee/ptcgpbuilder.git
cd ptcgpbuilder

# Install the package
pip install -e .
```

## Usage

### Running the Application

```bash
# Run the main application
python src/main.py
```

### Building a Deck

In the Builder view, filter by set, type, card category, or search by name. Press "o" (the o key) on a highlighted card to bring up a deck builder popup. Add 1 or 2 copies to an existing deck or create a new deck. If the deck contains 2 copies of that card, another cannot be added.

### Scraping Card Data

```bash
# Scrape a specific set
python src/scrape_pokemon_cards.py --url https://www.serebii.net/tcgpocket/shiningrevelry/

# Scrape multiple sets
python src/scrape_all_sets.py --sets shiningrevelry geneticapex

# Scrape all supported sets
python src/scrape_all_sets.py

```
Note: Some data may come back malformed in the json. Manual validating is necessary if something is wrong when searching the card DB.

### Importing Cards to Database

```bash
# Import cards from JSON file
python src/utils/import_cards.py --input pokemon_cards_shiningrevelry.json
```

## Keyboard Controls

- `1`: Show Decks view
- `2`: Show Builder view
- `o`: Open card actions menu (when card is highlighted)
- `q`: Quit application

### Deck View
- `Ctrl+n`: Create a new deck
- `Ctrl+r`: Rename selected deck
- `Ctrl+d`: Delete selected deck
- `Ctrl+y`: Remove card from deck
- `Ctrl+e`: Export deck as txt file

## Known Issues
- Creating an empty deck in Deck View with `Ctrl+n` crashes the program after successfully adding the deck to the database
- In Builder View, card list does not show all cards past the last 4 or so in the list. Highlighting still works with arrow keys
- In Builder View, if one item is returned by the filter, the item cannot be highlighted without switching between Deck View and Builder View
- In Deck View, the cards list card image is off center

## Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest
```
Everything Pokemon is owned by The Pokemon Company, Creatures, Nintendo, DeNA and any other related parties.

I do not own any data scraped from any sources used by this project. If Serebii would like scraping to cease, please let me know.

## License

MIT License
