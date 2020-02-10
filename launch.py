from configparser import ConfigParser
from argparse import ArgumentParser

from utils.server_registration import get_cache_server
from utils.config import Config
from crawler import Crawler

#imports for changes
import json
import os


def main(config_file, restart):
    #reads words.json if it has data and moves it to a different file
    if os.path.exists("data.json") and os.path.getsize("data.json") > 2:
        #generate a new file
        file_count = 1
        while os.path.exists("records/data_record" + str(file_count) + ".json"):
            file_count += 1
        
        with open("data.json", "r") as infile:
            with open("records/data_record" + str(file_count) + ".json", "w") as outfile:
                json.dump(json.load(infile), outfile)

    #reset and initialize the data in the json file
    with open("data.json", "w") as file_contents:
        json.dump({"url_count": 0, "largest_word_count": 0, "largest_url": "", "words": {}}, file_contents)
    #end of changes to launch.py

    #create subdomains.txt
    with open("subdomains.txt", "w") as file_contents:
                file_contents.write("{}")
    
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
