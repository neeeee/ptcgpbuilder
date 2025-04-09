from db_management import DBManagement

db_management = DBManagement("src/db/pokemon_tcg.db")

db_management.update_card_image_paths()