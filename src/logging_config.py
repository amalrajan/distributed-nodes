import logging


def setup_logging():
    logging.basicConfig(
        level=logging.DEBUG,  # Default level
        format="%(asctime)s - %(name)-20s - %(levelname)-8s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(),  # To log to console
            logging.FileHandler("app.log"),  # To log to a file
        ],
    )
