import os
import shelve

from threading import Thread, RLock
from queue import Queue, Empty

from utils import get_logger, get_urlhash, normalize
from scraper import is_valid
from urllib.parse import urlparse
import re

class Frontier(object):
    def __init__(self, config, restart):
        self.logger = get_logger("FRONTIER")
        self.config = config
        self.to_be_downloaded = {
            'ics': Queue(),
            'stat': Queue(),
            'cs': Queue(),
            'informatics': Queue(),
            'today': Queue()
        }
        self.workers_in_dom = {
            'ics': 0,
            'stat': 0,
            'cs': 0,
            'informatics': 0,
            'today': 0
        }
        if not os.path.exists(self.config.save_file) and not restart:
            # Save file does not exist, but request to load save.
            self.logger.info(
                f"Did not find save file {self.config.save_file}, "
                f"starting from seed.")
        elif os.path.exists(self.config.save_file) and restart:
            # Save file does exists, but request to start from seed.
            self.logger.info(
                f"Found save file {self.config.save_file}, deleting it.")
            os.remove(self.config.save_file)
        # Load existing save file, or create one if it does not exist.
        self.save = shelve.open(self.config.save_file)
        if restart:
            for url in self.config.seed_urls:
                self.add_url(url)
        else:
            # Set the frontier state with contents of save file.
            self._parse_save_file()
            if not self.save:
                for url in self.config.seed_urls:
                    self.add_url(url)

    def _parse_save_file(self):
        ''' This function can be overridden for alternate saving techniques. '''
        total_count = len(self.save)
        tbd_count = 0
        for url, completed in self.save.values():
            if not completed and is_valid(url):
                self.to_be_downloaded[Frontier.place_url_in_dom(url)].put(url)
                tbd_count += 1
        self.logger.info(
            f"Found {tbd_count} urls to be downloaded from {total_count} "
            f"total urls discovered.")

    def get_tbd_url(self):
        print(self.workers_in_dom)
        print()
        worker_tracker = sorted([worker for worker in self.workers_in_dom if self.workers_in_dom[worker] < 2], key=lambda x: self.workers_in_dom[x])
        put_in = worker_tracker[0]
        try:
            self.workers_in_dom[put_in] += 1
            return self.to_be_downloaded[put_in].get()
        except IndexError:
            return None

    def add_url(self, url):
        url = normalize(url)
        urlhash = get_urlhash(url)
        if urlhash not in self.save:
            self.save[urlhash] = (url, False)
            self.save.sync()
            self.to_be_downloaded[Frontier.place_url_in_dom(url)].put(url)
    
    def mark_url_complete(self, url):
        domain = Frontier.place_url_in_dom(url)
        self.workers_in_dom[domain] -= 1
        urlhash = get_urlhash(url)
        if urlhash not in self.save:
            # This should not happen.
            self.logger.error(
                f"Completed url {url}, but have not seen it before.")

        self.save[urlhash] = (url, True)
        self.save.sync()

    @staticmethod
    def place_url_in_dom(url):
        url_comp = urlparse(url)
        url_domain = re.match(r'(\S+\.)*(ics|cs|informatics|stat)\.uci\.edu', url_comp.netloc)
        assign_domain = ""
        if bool(url_domain):
            assign_domain = url_domain[2]
        elif url_comp.netloc == "today.uci.edu" and re.match(r'^(\/department\/information_computer_sciences\/)', url_comp.path):
            assign_domain = "today"
        return assign_domain