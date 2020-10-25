import logging


def set_level(args):
    """Set log level to the value passed in from argparse

    :args: dictionary of arguments parsed from argparse
    """
    if not args['verbose']:
        return logging.DEBUG
    elif args['verbose'] == 1:
        return logging.WARNING
    elif args['verbose'] == 2:
        return logging.INFO
    elif args['verbose'] == 3:
        return logging.DEBUG
    else:
        return logging.NOTSET


def set_logger(args):
    """Initiate logger instance and set the logging level

    :args: dictionary of arguments parsed from argparse

    return: instance of logger
    """
    logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s',
                        level=set_level(args))
    logger = logging.getLogger(__name__)
    return logger
