import re
from urllib.parse import urlparse
from urllib.request import urlopen
from urllib.robotparser import RobotFileParser
from bs4 import BeautifulSoup
import os
import requests

data_dict = {"url_count": 0, "largest_word_count": 0, "largest_url": "", "words": {}}
ics_subdomains = {}         #subdomains of ics.uci.edu
robots = {}                 #robots: key - parsedurl's netloc, value: RobotFileParser Instance
STOP_WORDS = {'a', 'about' ,'above' ,'after' ,'again' ,'against' ,'all' ,'am' ,'an' ,'and' ,'any' ,'are' ,'aren\'t' ,'as' ,'at' ,'be' ,'because' ,'been' ,'before' ,'being' ,'below' ,'between' ,'both' ,'but' ,'by' ,'can\'t' ,'cannot' ,'could' ,'couldn\'t' ,'did' ,'didn\'t' ,'do' ,'does' ,'doesn\'t' ,'doing' ,'don\'t' ,'down' ,'during' ,'each' ,'few' ,'for' ,'from' ,'further' ,'had' ,'hadn\'t' ,'has' ,'hasn\'t' ,'have' ,'haven\'t' ,'having' ,'he' ,'he\'d' ,'he\'ll' ,'he\'s' ,'her' ,'here' ,'here\'s' ,'hers' ,'herself' ,'him' ,'himself' ,'his' ,'how' ,'how\'s' ,'i' ,'i\'d' ,'i\'ll' ,'i\'m' ,'i\'ve' ,'if' ,'in' ,'into' ,'is' ,'isn\'t' ,'it' ,'it\'s' ,'its' ,'itself' ,'let\'s' ,'me' ,'more' ,'most' ,'mustn\'t' ,'my' ,'myself' ,'no' ,'nor' ,'not' ,'of' ,'off' ,'on' ,'once' ,'only' ,'or' ,'other' ,'ought' ,'our' ,'ours', 'ourselves' ,'out' ,'over' ,'own' ,'same' ,'shan\'t' ,'she' ,'she\'d' ,'she\'ll' ,'she\'s' ,'should' ,'shouldn\'t' ,'so' ,'some' ,'such' ,'than' ,'that' ,'that\'s' ,'the' ,'their' ,'theirs' ,'them' ,'themselves' ,'then' ,'there' ,'there\'s' ,'these' ,'they' ,'they\'d' ,'they\'ll' ,'they\'re' ,'they\'ve' ,'this' ,'those' ,'through' ,'to' ,'too' ,'under' ,'until' ,'up' ,'very' ,'was' ,'wasn\'t' ,'we' ,'we\'d' ,'we\'ll' ,'we\'re' ,'we\'ve' ,'were' ,'weren\'t' ,'what' ,'what\'s' ,'when' ,'when\'s' ,'where' ,'where\'s' ,'which' ,'while' ,'who' ,'who\'s' ,'whom' ,'why' ,'why\'s' ,'with' ,'won\'t' ,'would' ,'wouldn\'t' ,'you' ,'you\'d' ,'you\'ll' ,'you\'re' ,'you\'ve' ,'your' ,'yours' ,'yourself' ,'yourselves'}
visited_urls = set()

tracker = 0

traps = set()
def scraper(url, resp):
    print('\nURL' + str(url))
    global tracker
    tracker += 1
    valid_links = []
    if 200 <= resp.status <= 299 and resp.status != 204:
        visited_urls.add(url)
        #process content adds filepage contents into data_dict
        process_content(url, resp)
        links = extract_next_links(url, resp)
        for link in links:
            if string_not_none(link) and is_valid(link):
                #add the valid link to list of links returned by scraper
                valid_links.append(link)
                #records the url if it is a subdomain of ics.uci.edu
                parsed = urlparse(link)
                result = re.match(r'(.+)\.ics\.uci\.edu', parsed.netloc)
                if result and string_not_none(result[1]) and result[1].rstrip('.') != 'www':
                    add_to_dict_set(ics_subdomains, result[1], parsed.path)
                visited_urls.add(link)
    write_data_to_files(tracker)
    return valid_links

def extract_next_links(url, resp):
    #list of all the links found in the url
    url = url.replace(' ', '%')             #replace blankspcaes in URLS with %
    link_list = []
    file_handler = urlopen(url)
    parsed = BeautifulSoup(file_handler)
    url_parsed = urlparse(url)

    #retrieve all the links found in the parsed url
    #parse the url contents  
    for link_tag in parsed.find_all('a', href=True):
        link = link_tag.get('href')
        link = link.split('#')[0]
        #checks for link formats that is_valid cannot check properly
        if  not link.startswith('//') and link.startswith('/'):
            link = "https://" + url_parsed.netloc + link
        if link != "" and link != None:
            link_list.append(link)
    return link_list

def is_valid(url):
    print("VALIDIFYING URL\t" + url)
    if not string_not_none(url):
        return False
    try:
        #checks if url has already been visited
        if url in visited_urls:
            return False
        parsed = urlparse(url)

        #check if scheme is valid
        if parsed.scheme not in set(["http", "https"]):
            return False
        if not parsed.query == '':
            return False
            
        #check for possible domains
        reg_domains = r'(\S+\.)*(ics|cs|informatics|stat)\.uci\.edu'
        # reg_domains = r'(\S+\.)*(ics)\.uci\.edu'
        domain_valid = re.match(reg_domains, parsed.netloc) or (parsed.netloc == "today.uci.edu" and re.match(r'^(\/department\/information_computer_sciences\/)', parsed.path))
        if not domain_valid:
            return False
        #trap detection
        if re.match(r'^.*calendar.*$', url):
            return False    
        #check for hidden calendars - e.g. WICS.ICS.UCI.EDU
        if re.match(r'\/(\d{1,2}|\d{4})-(\d{1,2})(-\d{2}|\d{4})?\/?', parsed.path):
            return False
        #checking that we only crawl files with that subdomain and path
        if parsed.netloc == "today.uci.edu" and re.match(r"^(\/department\/information_computer_sciences\/calendar\/)", parsed.path):
            return False
        #disallow tags and numbered end paths and tags from being in the url path
        if re.match(r'(\/\S+)*\/(\d+\/?)$', parsed.path) or re.match(r'^(\/tags?)\/?(\S+\/?)?', parsed.path):
            return False

        #checks for webpages that contain content that is not text or a webpage
        directory_path = parsed.path.lower().split('/')
        pathwords_count = track_num_word(parsed.path, '/')
        if len([word for word in pathwords_count if pathwords_count[word] >= 2]):
            return False
        if "pdf" in directory_path or "faq" in directory_path or "zip-attachment" in directory_path:
            return False
        # parsed = urlparse(url)
        # if ban_hammer(url, parsed):
        #     return False
        #check for valid file extension
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
            if strip_token in data_dict["words"]:
                data_dict["words"][strip_token] += 1
            else:
                data_dict["words"][strip_token] = 1

    #checks if the current parsed url is larger than the largest recorded parsed url
    if 'largest_word_count' not in data_dict or word_count > data_dict['largest_word_count']:
        data_dict['largest_word_count'] = word_count
        data_dict['largest_url'] = url

#go though the file and extract data to put into .txt files
#data put in through the `write_data_to_files` function
def process_content(url, resp):
    #parse the url contents
    file_handler = urlopen(url)
    parsed = BeautifulSoup(file_handler, "lxml")

    #gets the webpage content and records the words found in it
    content = parsed.get_text()
    record_content(content, url)

#creates a dictionary tracking the number of words from an interable oject
#intentionally implemented with a list
def track_num_word(url_path: list, splitter: str) -> dict:
    url_path = url_path.split(splitter)
    counter_dict = {}
    for word in url_path:
        if word in counter_dict:
            counter_dict[word] += 1
        else:
            counter_dict[word] = 1
    return counter_dict

#checks if a string is not None and not an empty string
def string_not_none(url: str) -> bool:
    return type(url) == str and url != ""

#write shared global values to .txt files
def write_data_to_files(tracking_num: int):
    if tracking_num % 8 == 0:
        with open("subdomains.txt", "w") as file_contents:
            file_contents.write(str(ics_subdomains))
        with open("data.txt", "w") as file_contents:
            file_contents.write(str(data_dict))

#create a new RobotFileParser for every domain and subdomain
#places the subdomain robot into `robots` dictionary
#places a function (which returns a boolean saying
# something is poltely retrievable) into the dictionary
def create_sdomain_robot(url_netloc: str):
    robot = RobotFileParser()
    robot.set_url(url_netloc + "/robots.txt")
    robot.read()
    def polite_fetch(url):
        return robot.can_fetch("*", url)
    robots[str] = polite_fetch

#helper method to add an item to a dictionary of sets
def add_to_dict_set(dict_set: dict, item_key, added_item):
    if item_key in dict_set:
        dict_set[item_key].add(added_item)
    else:
        dict_set[item_key] = {added_item}

#!!!    UNDER CONSTRUCTION  !!!
#deny validity if any of these are violated
def ban_hammer(url: str, parsed) -> bool:
    reg_domains = r'(\S+\.)*(ics|cs|informatics|stat)\.uci\.edu'
    directory_path = parsed.path.lower().split('/')
    pathwords_count = track_num_word(parsed.path, '/')
    #if any of the below are true, return False:
    return any([
        #do not visit another url twice, ignore not http/https, ignore queries
        url in visited_urls,
        parsed.scheme not in {"http", "https"},
        parsed.query == '',

        #check for invalid domain
        not (re.match(reg_domains, parsed.netloc) or 
        (parsed.netloc == "today.uci.edu" and 
        re.match(r'^(\/department\/information_computer_sciences\/)', parsed.path))),
        
        #check for traps - filtering out:
        re.match(r'^.*calendar.*$', url),                                           #calendars
        re.match(r'\/(\d{1,2}|\d{4})-(\d{1,2})(-\d{2}|\d{4})?\/?', parsed.path),    #dates
        re.match(r'(\/\S+)*\/(\d+\/?)$', parsed.path),                              #numbers (page nums)
        re.match(r'^(\/tags?)\/?(\S+\/?)?', parsed.path),                           #tags
        len([word for word in pathwords_count if pathwords_count[word] >= 2]) > 2,  #duplicated words in path
        "pdf" in directory_path,
        "faq" in directory_path,
        "zip-attachment" in directory_path,
        "calendar" in directory_path
    ])