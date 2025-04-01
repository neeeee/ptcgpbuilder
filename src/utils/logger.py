import logging
import os

class Logger():
    def __init__(self, log_file_path):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        self.log_file_path = log_file_path
        self.create_folder_and_log(self.log_file_path)
        self.handler = logging.FileHandler(self.log_file_path)
        self.handler.setLevel(logging.INFO)

        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        self.handler.setFormatter(formatter)
        self.logger.addHandler(self.handler)

    def create_folder_and_log(self, folder_path):
        try:
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)
                print(f"Created folder: {folder_path}")
                return True
            else:
                self.log_file_path = os.path.join(folder_path, "pokemontcgbuilder.log")
                if not os.path.exists(self.log_file_path):
                    with open(self.log_file_path, "w") as f:
                        pass
                    print(f"Created log file: {self.log_file_path}")
                else:
                    print(f"Log file already exists: {self.log_file_path}")
                return True

        except Exception as e:
            print(f"Error: {e}")
            return False
