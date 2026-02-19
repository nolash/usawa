import logging
import sys

from usawa.gui import Usawa

logging.basicConfig(level=logging.DEBUG)


def main():
    app = Usawa(application_id='org.usawa.app')
    app.run(sys.argv)
