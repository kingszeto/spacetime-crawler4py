from threading import Thread
from utils.download import download
from utils import get_logger
from scraper import scraper
import time

import re
from urllib.parse import urlparse


class Worker(Thread):
    WORKER_LOCATION_DOMAINS = {
        'ics': [],
        'stat': [],
        'cs': [],
        'informatics': [],
        'today': []
    }
    def __init__(self, worker_id, config, frontier):
        self.logger = get_logger(f"Worker-{worker_id}", "Worker")
        self.config = config
        self.frontier = frontier
        super().__init__(daemon=True)

    def run(self):
        while True:
            tbd_url = self.frontier.get_tbd_url()
            if not tbd_url:
                self.logger.info("Frontier is empty. Stopping Crawler.")
                break

            #get url components and then sort into static dictionatry
            #limits two crawlers per domain

            #check what domain the worker wants to download
            url_comp = urlparse(tbd_url)
            url_domain = re.match(r'(\S+\.)*(ics|cs|informatics|stat)\.uci\.edu', url_comp.netloc):
            assign_domain = ""
            if bool(url_domain):
                assign_domain = url_domain[2]
            else if url_comp.netloc == "today.uci.edu" and re.match(r'^(\/department\/information_computer_sciences\/)', url_comp.path):
                assign_domain = "today"
            #then, check if that domain is full or not
            if len(Worker.WORKER_LOCATION_DOMAINS[assign_domain]) <= 2:
                Worker.WORKER_LOCATION_DOMAINS[assign_domain].append(1)
                resp = download(tbd_url, self.config, self.logger)
                self.logger.info(
                    f"Downloaded {tbd_url}, status <{resp.status}>, "
                    f"using cache {self.config.cache_server}.")
                scraped_urls = scraper(tbd_url, resp)
                for scraped_url in scraped_urls:
                    self.frontier.add_url(scraped_url)
                self.frontier.mark_url_complete(tbd_url)
                Worker.WORKER_LOCATION_DOMAINS[assign_domain].pop(0)
            time.sleep(self.config.time_delay)
