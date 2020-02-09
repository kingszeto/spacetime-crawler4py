import re
from urllib.parse import urlparse
from urllib.request import urlopen
from bs4 import BeautifulSoup
import json
import os

STOP_WORDS = {'a', 'about' ,'above' ,'after' ,'again' ,'against' ,'all' ,'am' ,'an' ,'and' ,'any' ,'are' ,'aren\'t' ,'as' ,'at' ,'be' ,'because' ,'been' ,'before' ,'being' ,'below' ,'between' ,'both' ,'but' ,'by' ,'can\'t' ,'cannot' ,'could' ,'couldn\'t' ,'did' ,'didn\'t' ,'do' ,'does' ,'doesn\'t' ,'doing' ,'don\'t' ,'down' ,'during' ,'each' ,'few' ,'for' ,'from' ,'further' ,'had' ,'hadn\'t' ,'has' ,'hasn\'t' ,'have' ,'haven\'t' ,'having' ,'he' ,'he\'d' ,'he\'ll' ,'he\'s' ,'her' ,'here' ,'here\'s' ,'hers' ,'herself' ,'him' ,'himself' ,'his' ,'how' ,'how\'s' ,'i' ,'i\'d' ,'i\'ll' ,'i\'m' ,'i\'ve' ,'if' ,'in' ,'into' ,'is' ,'isn\'t' ,'it' ,'it\'s' ,'its' ,'itself' ,'let\'s' ,'me' ,'more' ,'most' ,'mustn\'t' ,'my' ,'myself' ,'no' ,'nor' ,'not' ,'of' ,'off' ,'on' ,'once' ,'only' ,'or' ,'other' ,'ought' ,'our' ,'ours', 'ourselves' ,'out' ,'over' ,'own' ,'same' ,'shan\'t' ,'she' ,'she\'d' ,'she\'ll' ,'she\'s' ,'should' ,'shouldn\'t' ,'so' ,'some' ,'such' ,'than' ,'that' ,'that\'s' ,'the' ,'their' ,'theirs' ,'them' ,'themselves' ,'then' ,'there' ,'there\'s' ,'these' ,'they' ,'they\'d' ,'they\'ll' ,'they\'re' ,'they\'ve' ,'this' ,'those' ,'through' ,'to' ,'too' ,'under' ,'until' ,'up' ,'very' ,'was' ,'wasn\'t' ,'we' ,'we\'d' ,'we\'ll' ,'we\'re' ,'we\'ve' ,'were' ,'weren\'t' ,'what' ,'what\'s' ,'when' ,'when\'s' ,'where' ,'where\'s' ,'which' ,'while' ,'who' ,'who\'s' ,'whom' ,'why' ,'why\'s' ,'with' ,'won\'t' ,'would' ,'wouldn\'t' ,'you' ,'you\'d' ,'you\'ll' ,'you\'re' ,'you\'ve' ,'your' ,'yours' ,'yourself' ,'yourselves'}
def scraper(url, resp):
    links = extract_next_links(url, resp)
    valid_links = [link for link in links if is_valid(link)]
    print("VALID LINKS:\n----------\n", end = "")
    for link in valid_links:
        print('\t' + str(link))
    print('\n----------\n', end="")

def extract_next_links(url, resp):
    #list of all the links found in the url
    link_list = []
    print('\nUUUUUUUUUUU\n\t' + str(url) + '\nUUUUUUUUUUU\n')
    #check HTTP Status
    if 200 <= resp.status <= 399 and resp.status != 204:
        file_handler = urlopen(url)
        parsed = BeautifulSoup(file_handler)
    #retrieve all the links found in the parsed url
    #parse the url contents  
        for link_tag in parsed.find_all('a', href=True):
            link = link_tag.get('href')
            link = link.split('#')[0]
            #checks if href contains a link like '/about' or '//www.stat.uci.edu'
            if link.startswith('//'):
                link = 'https:' + link
            link_list.append(link)
        process_content(url)
    return link_list

def is_valid(url):
    try:
        parsed = urlparse(url)
        #check if scheme is valid
        if parsed.scheme not in set(["http", "https"]):
            return False
        #check for possible domains
        reg_domains = r'.*\.(ics|cs|informatics|stat)\.uci\.edu'
        domain_valid = [re.match(reg_domains, parsed.netloc)]
        domain_valid.append(parsed.netloc == "today.uci.edu" and re.match(r'^(\/department\/information_computer_sciences\/)', parsed.path))
        if not any(domain_valid):
            return False
                    
        #checking for ICS Calendar Web Cralwer Trap
        if parsed.netloc == "today.uci.edu" and re.match(r"^(\/department\/information_computer_sciences\/calendar\/)", parsed.path):
            return False

        #check for valid path
        return not re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1"
            + r"|thmx|mso|arff|rtf|jar|csv"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower())

    except TypeError:
        print ("TypeError for ", parsed)
        raise

def record_content(token_dict, token_string, url):
    word_count = 0

    #records the contents of the string 
    for token in re.sub('[^A-Za-z\']+', ' ', token_string.lower()).split():
        word_count += 1
        if token not in STOP_WORDS:
            if token in token_dict:
                token_dict[token] += 1
            else:
                token_dict[token] = 1

    #checks if the current parsed url is larger than the largest recorded parsed url
    if 'largest_word_count' in token_dict or word_count > token_dict['largest_word_count']:
        token_dict['largest_word_count'] = word_count
        token_dict['largest_url'] = url
    print("TOKEN DICT: \n\t" + str(token_dict))

def process_content(url):
    #checks if the json file is empty and initializes it if it is
    if os.path.getsize("words.json") <= 2:
        with open("words.json", "w") as file_contents:
            json.dump({"largest_word_count": 0, "largest_url": ""}, file_contents)
    #open and load the json file
    with open("words.json", "r") as file_contents:
        tokens = json.load(file_contents)

    #parse the url contents
    file_handler = urlopen(url)
    parsed = BeautifulSoup(file_handler)

    #gets the webpage content and records the words found in it
    content = parsed.get_text()
    record_content(tokens, content, url)

    #dump the new dictionary into the json file
    with open("words.json", "w") as file_contents:
        json.dump(tokens, file_contents)
