import logging

class Logger():
    def __init__(self, log_file):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
# Create a file handler and set the logging level to INFO
        self.handler = logging.FileHandler(log_file)
        self.handler.setLevel(logging.INFO)

# Create a formatter and attach it to the handler
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        self.handler.setFormatter(formatter)
        self.logger.addHandler(self.handler)

