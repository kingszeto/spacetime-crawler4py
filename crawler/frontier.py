import os
import shelve

from threading import Thread, RLock
from queue import Queue, Empty

from utils import get_logger, get_urlhash, normalize
from scraper import is_valid
from urllib.parse import urlparse
import re

import time

#changes have been made so that self.to_be_downloaded implements a dictionary of Queues. Every single enqueue/put
#function and dequeue/get is preceded by the key, which is a domain

class Frontier(object):
    def __init__(self, config, restart):
        self.logger = get_logger("FRONTIER")
        self.config = config
        
        #dictionary of Queues, organized by their domains
        self.to_be_downloaded = {
            'ics': Queue(),
            'stat': Queue(),
            'cs': Queue(),
            'informatics': Queue(),
            'today': Queue()
        }
        self.set_delay = 5    #unit in seconds, 500ms = 1 ms
        self.delay_tracker = {domain: -0.5 for domain in self.to_be_downloaded}
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
        if all([self.to_be_downloaded[domain].empty() for domain in self.to_be_downloaded]):
            return None
        #sort the domains based on how little workers they have (least to greatest) then take the domain with the
        #least amount of workers and assign the url based on that domain
        non_empty = []
        while non_empty == []:
            non_empty = [domain for domain in sorted(self.to_be_downloaded,
             key=lambda x: self.delay_tracker[x])
            if not self.to_be_downloaded[domain].empty() and 
            time.time() - self.delay_tracker[domain] >= self.set_delay]
        domain = non_empty[0]
        try:
            self.delay_tracker[domain] = time.time()
            return self.to_be_downloaded[domain].get()
        except:
            return None

    def add_url(self, url):
        url = normalize(url)
        urlhash = get_urlhash(url)
        if urlhash not in self.save:
            self.save[urlhash] = (url, False)
            self.save.sync()
            domain = Frontier.place_url_in_dom(url)
            self.delay_tracker
            self.to_be_downloaded[domain].put(url)
    
    def mark_url_complete(self, url):
        urlhash = get_urlhash(url)
        if urlhash not in self.save:
            # This should not happen.
            self.logger.error(
                f"Completed url {url}, but have not seen it before.")

        self.save[urlhash] = (url, True)
        self.save.sync()

    #determines what domain to use based on the url, special case with today.uci.edu/...
    @staticmethod
    def place_url_in_dom(url):
        url_comp = urlparse(url)
        url_domain = re.search(r'(?:\S+\.)*(?P<domain>ics|cs|informatics|stat)\.uci\.edu', url_comp.netloc)
        assign_domain = ""
        if bool(url_domain.group):
            assign_domain = url_domain.group('domain')
        elif url_comp.netloc == "today.uci.edu" and re.match(r'^(\/department\/information_computer_sciences\/)', url_comp.path):
            assign_domain = "today"
        return assign_domain

