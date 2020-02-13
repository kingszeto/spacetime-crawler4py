import re
from urllib.parse import urlparse
from urllib.request import urlopen
from urllib.robotparser import RobotFileParser
from bs4 import BeautifulSoup
from simhash import Simhash, SimhashIndex       #from https://github.com/leonsim/simhash
import os
import requests

data_dict = {"url_count": 0, "largest_word_count": 0, "largest_url": "", "urlsfound": 0, "words": {}}
ics_subdomains = {}         #subdomains of ics.uci.edu
robots = {}                 #robots: key - parsedurl's netloc, value: RobotFileParser Instance
STOP_WORDS = {'a', 'about' ,'above' ,'after' ,'again' ,'against' ,'all' ,'am' ,'an' ,'and' ,'any' ,'are' ,'aren\'t' ,'as' ,'at' ,'be' ,'because' ,'been' ,'before' ,'being' ,'below' ,'between' ,'both' ,'but' ,'by' ,'can\'t' ,'cannot' ,'could' ,'couldn\'t' ,'did' ,'didn\'t' ,'do' ,'does' ,'doesn\'t' ,'doing' ,'don\'t' ,'down' ,'during' ,'each' ,'few' ,'for' ,'from' ,'further' ,'had' ,'hadn\'t' ,'has' ,'hasn\'t' ,'have' ,'haven\'t' ,'having' ,'he' ,'he\'d' ,'he\'ll' ,'he\'s' ,'her' ,'here' ,'here\'s' ,'hers' ,'herself' ,'him' ,'himself' ,'his' ,'how' ,'how\'s' ,'i' ,'i\'d' ,'i\'ll' ,'i\'m' ,'i\'ve' ,'if' ,'in' ,'into' ,'is' ,'isn\'t' ,'it' ,'it\'s' ,'its' ,'itself' ,'let\'s' ,'me' ,'more' ,'most' ,'mustn\'t' ,'my' ,'myself' ,'no' ,'nor' ,'not' ,'of' ,'off' ,'on' ,'once' ,'only' ,'or' ,'other' ,'ought' ,'our' ,'ours', 'ourselves' ,'out' ,'over' ,'own' ,'same' ,'shan\'t' ,'she' ,'she\'d' ,'she\'ll' ,'she\'s' ,'should' ,'shouldn\'t' ,'so' ,'some' ,'such' ,'than' ,'that' ,'that\'s' ,'the' ,'their' ,'theirs' ,'them' ,'themselves' ,'then' ,'there' ,'there\'s' ,'these' ,'they' ,'they\'d' ,'they\'ll' ,'they\'re' ,'they\'ve' ,'this' ,'those' ,'through' ,'to' ,'too' ,'under' ,'until' ,'up' ,'very' ,'was' ,'wasn\'t' ,'we' ,'we\'d' ,'we\'ll' ,'we\'re' ,'we\'ve' ,'were' ,'weren\'t' ,'what' ,'what\'s' ,'when' ,'when\'s' ,'where' ,'where\'s' ,'which' ,'while' ,'who' ,'who\'s' ,'whom' ,'why' ,'why\'s' ,'with' ,'won\'t' ,'would' ,'wouldn\'t' ,'you' ,'you\'d' ,'you\'ll' ,'you\'re' ,'you\'ve' ,'your' ,'yours' ,'yourself' ,'yourselves'}
visited_urls = set()
hashed = SimhashIndex([], k=0)
tracker = 0
traps = set()


def scraper(url, resp):
    global tracker
    valid_links = []
    if 200 <= resp.status <= 299 and resp.status != 204:
        visited_urls.add(url)
        #process content returns false if the content was found to be similar to an already crawled url
        if process_content(url, resp):
            links = extract_next_links(url, resp)
            data_dict["urlsfound"] +=  len(links)
            tracker += 1
            for link in links:
                if string_not_none(link) and is_valid(link):
                    print("URL\t" + link)
                    #records the url if it is a subdomain of ics.uci.edu for analytics
                    valid_links.append(link)
                    parsed = urlparse(link)
                    visited_urls.add(link)
                    result = re.match(r'(.+)\.ics\.uci\.edu', parsed.netloc)
                    if result and string_not_none(result[1]) and result[1].rstrip('.') != 'www':
                        add_to_dict_set(result[1], parsed.path, ics_subdomains)       
    write_data_to_files(tracker)
    return valid_links

def extract_next_links(url, resp):
    #list of all the links found in the url
    url = url.replace(' ', '%')                         #replace spaces with %
    link_list = []
    file_handler = urlopen(url)
    parsed = BeautifulSoup(file_handler, "lxml")
    url_parsed = urlparse(url)
    #retrieve all the links found in the parsed url
    #parse the url contents  
    for link_tag in parsed.find_all('a', href=True):
        link = link_tag.get('href')
        link = link.split('#')[0]
        #checks for link formats that is_valid cannot check properly
        if  not link.startswith('//') and link.startswith('/'):
            link = "https://" + url_parsed.netloc + link
        if string_not_none(link):
            link_list.append(link.replace(' ', '%'))
    #returns a set to avoid duplicates within the link_list
    return set(link_list)

def is_valid(url):
    if not string_not_none(url):
        return False
    try:
        #designate url as invalid if it does not meet certain requirements
        #as seen in this big if statement
        parsed = urlparse(url)
        if url in visited_urls \
         or not good_format(parsed.scheme, parsed.query) \
         or not valid_netloc(url, parsed.netloc, parsed.path) \
         or time_in_url(url, parsed.path) \
         or navigation_page(parsed.path) \
         or banned_words_in_url(parsed.path):
            return False
        #getting rid of low information pages - from Ramesh Jain
        # note: these pages are simply pages that link to his other blog posts, their main information is just links to other pages
        # which our crawler already covers ^^

        #check for valid path and validify URL
        return not re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1|php|z|ppsx"
            + r"|thmx|mso|arff|rtf|jar|csv|war"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower())
    except TypeError:
        print ("TypeError for ", parsed)
        raise

#records contents from the string, done in `process_content`
def record_content(token_string, url):
    word_count = 0
    data_dict["url_count"] += 1
    #records the contents of the string 
    for token in re.sub('[^A-Za-z\']+', ' ', token_string.lower()).split():
        word_count += 1
        #turns 'token' into token (removes apostrophes that aren't there for contractions)
        strip_token = re.sub('^[^a-z]+|[^a-z]+$', '', token)
        if strip_token not in STOP_WORDS:
            update_counter_dict(strip_token, 1, data_dict['words'])
    #checks if the current parsed url is larger than the largest recorded parsed url
    if 'largest_word_count' not in data_dict or word_count > data_dict['largest_word_count']:
        data_dict['largest_word_count'] = word_count
        data_dict['largest_url'] = url

#go though the file and extract data to put into .txt files
#important for write_data_to_files function
def process_content(url, resp):
    try:
        #parse the url contents
        file_handler = urlopen(url).read().decode('utf-8')
        parsed = BeautifulSoup(file_handler, "lxml")
        content = parsed.get_text()
        if check_similar(content, url):
            return False
        #gets the webpage content and records the words found in it
        record_content(content, url)
        return True
    except:
        #returns false if urlopen does not work
        return False

#takes the content and checks if similar content has been found already
#uses simhash
def check_similar(content, url):
    fingerprint = Simhash(content)
    dupes = hashed.get_near_dups(fingerprint)
    if len(dupes) > 0:
        print("Uv####################################")
        print(url)
        print(dupes)
        print("D^####################################")
        return True
    else:
        hashed.add(url, fingerprint)
        return False

#creates a dictionary tracking the number of words from an interable oject
#intentionally implemented with a list
def track_num_word(url_path: list, splitter: str) -> dict:
    url_path = url_path.split(splitter)
    counter_dict = {}
    for word in url_path:
        update_counter_dict(word, 1, counter_dict)
    return counter_dict

#write shared values to .txt based on tracker, so we can avoid collisions of writing to file
def write_data_to_files(tracking_num: int):
    if tracking_num % 8 == 0:
        with open("subdomains.txt", "w") as file_contents:
            file_contents.write(str(ics_subdomains))
        with open("data.txt", "w") as file_contents:
            file_contents.write(str(data_dict))

#create a new RobotFileParser for every domain and subdomain
#places the subdomain robot into `robots` dictionary
#creates a function where robot returns whether or not a url can be crawled
def create_sdomain_robot(url: str):
    url = urlparse(url)
    robot = RobotFileParser()
    robot.set_url(url.scheme + '://' + url.netloc + "/robots.txt")
    def can_crawl(url_with_path: str):
        return robot.can_fetch('*', url_with_path)
    #may not be able to read a file, if so we will just not have a robot for that
    #subdomain. Assumes all pages can be crawled 
    try:
        robot.read()
        robots[url.netloc] = can_crawl
    except: 
        pass
#returns true if it is a valid domain and the url adheres to
#robots.txt politeness, uses the global robots dictionary and
#udpates it at the same time.
def valid_netloc(url: str, url_netloc: str, url_path: str) -> bool:
    #check for possible domains
    reg_domains = r'(\S+\.)*(ics|cs|informatics|stat)\.uci\.edu'
    #reg_domains = r'(\S+\.)*(stat)\.uci\.edu'
    domain_valid = re.match(reg_domains, url_netloc) or (url_netloc == "today.uci.edu" and re.match(r'^(\/department\/information_computer_sciences\/)', url_path))
    if not domain_valid:
        return False
    if not url_netloc in robots:
        create_sdomain_robot(url)
    if url_netloc in robots and not robots[url_netloc](url):
        return False
    return True

#returns True if there are date-like strings in url path
#and an instance of calendar captured by regex in the url
def time_in_url(url: str, urlpath: str) -> bool:
    return re.match(r'^.*calendar.*$', url) or re.match(r'\S*\/(?:\d{1,2}|\d{4})-(?:\d{1,2})(?:-\d{2}|\d{4})?\/?', urlpath)

#returns True if the url seems to be for navigation's sake
#--meaning there are page/1/ ... /100/ or tags
def navigation_page(url_path: str) -> bool:
    return re.match(r'(\/\S+)*\/(\d+\/?)$', url_path) or re.match(r'^(\/tags?)\/?(\S+\/?)?', url_path)

#returns True if some defined, hardcoded words are within the paths of the url
def banned_words_in_url(urlpath: str) -> bool:
    words = set(urlpath.lower().split('/'))
    return "pdf" in words or "faq" in words or "zip-attachment" in words

#helper function returns true if a url is not an empty string
def string_not_none(url: str) -> bool:
    return type(url) == str and url != ""

#helper function adds an element to a set in a dictionary
def add_to_dict_set(key: str, added_item: str, setdict: dict):
    if key in setdict:
        setdict[key].add(added_item)
    else:
        setdict[key] = {added_item}

#makes sure scheme is in http/https and no queries
def good_format(url_scheme, url_query):
    return url_scheme in {"http", "https"} and url_query == ''

#updates a dictionary that counts numver of instances of keys, increment_value
#shoudl usually be 1
def update_counter_dict(key: str, increment_value: int, counting: dict):
    if key in counting:
        counting[key] += increment_value
    else:
        counting[key] = increment_value
