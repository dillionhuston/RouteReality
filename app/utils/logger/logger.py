import logging
import sys
from threading import Lock


_logger = None
_lock = Lock()


def get_logger(
        name :str = "app",
        level: int = logging.INFO) -> logging.Logger:
    global _logger

    if _logger:
        return _logger
    
    with _lock:
        if _logger:
            return _logger
        
        logger = logging.getLogger(name)
        logger.setLevel(level)
        logger.propagate = False

        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s] [%(levelname)s] %(name)s: %(message)s" 
            )
        )


        logger.addHandler(handler)

        _logger = logger
        return _logger




    