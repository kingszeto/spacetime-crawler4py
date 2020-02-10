from configparser import ConfigParser
from argparse import ArgumentParser

from utils.server_registration import get_cache_server
from utils.config import Config
from crawler import Crawler

#imports for changes
import os


def main(config_file, restart):
    file_count = 1
    #reads data.txt to check if it has data and moves it to a different file
    if os.path.exists("data.txt") and os.path.getsize("data.txt") > 2:
        #generate a new file
        while os.path.exists("records/data_record" + str(file_count) + ".txt"):
            file_count += 1
        
        with open("data.txt", "r") as infile:
            with open("records/data_record" + str(file_count) + ".txt", "w") as outfile:
                outfile.write(infile.read())

    #reads subdomains.txt to check if it has data and moves it to a different file
    if os.path.exists("subdomains.txt") and os.path.getsize("subdomains.txt") > 2:
        #generate a new file
        with open("subdomains.txt", "r") as infile:
            with open("records/subdomains_record" + str(file_count) + ".txt", "w") as outfile:
                outfile.write(infile.read())

    #create or overwrite subdomains.txt
    # with open("subdomains.txt", "w") as file_contents:
    #     file_contents.write("{}")
    
    cparser = ConfigParser()
    cparser.read(config_file)
    config = Config(cparser)
    config.cache_server = get_cache_server(config, restart)
    crawler = Crawler(config, restart)
    crawler.start()


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--restart", action="store_true", default=False)
    parser.add_argument("--config_file", type=str, default="config.ini")
    args = parser.parse_args()
    main(args.config_file, args.restart)
