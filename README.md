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

### Scraping Card Data

```bash
# Scrape a specific set
python src/scrape_pokemon_cards.py --url https://www.serebii.net/tcgpocket/shiningrevelry/

# Scrape multiple sets
python src/scrape_all_sets.py --sets shiningrevelry geneticapex

# Scrape all supported sets
python src/scrape_all_sets.py
```

### Importing Cards to Database

```bash
# Import cards from JSON file
python src/utils/import_cards.py --input pokemon_cards_shiningrevelry.json
```

## Keyboard Controls

- `1`: Show Decks view
- `2`: Show Builder view
- `o`: Open card actions menu
- `Ctrl+n`: Create a new deck
- `Ctrl+r`: Rename selected deck
- `Ctrl+d`: Delete selected deck
- `Ctrl+y`: Remove card from deck
- `q`: Quit application

## Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest
```

## License

MIT License
