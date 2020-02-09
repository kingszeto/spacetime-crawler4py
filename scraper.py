import re
from urllib.parse import urlparse
from urllib.request import urlopen
from bs4 import BeautifulSoup
import json

STOP_WORDS = {'a', 'about' ,'above' ,'after' ,'again' ,'against' ,'all' ,'am' ,'an' ,'and' ,'any' ,'are' ,'aren\'t' ,'as' ,'at' ,'be' ,'because' ,'been' ,'before' ,'being' ,'below' ,'between' ,'both' ,'but' ,'by' ,'can\'t' ,'cannot' ,'could' ,'couldn\'t' ,'did' ,'didn\'t' ,'do' ,'does' ,'doesn\'t' ,'doing' ,'don\'t' ,'down' ,'during' ,'each' ,'few' ,'for' ,'from' ,'further' ,'had' ,'hadn\'t' ,'has' ,'hasn\'t' ,'have' ,'haven\'t' ,'having' ,'he' ,'he\'d' ,'he\'ll' ,'he\'s' ,'her' ,'here' ,'here\'s' ,'hers' ,'herself' ,'him' ,'himself' ,'his' ,'how' ,'how\'s' ,'i' ,'i\'d' ,'i\'ll' ,'i\'m' ,'i\'ve' ,'if' ,'in' ,'into' ,'is' ,'isn\'t' ,'it' ,'it\'s' ,'its' ,'itself' ,'let\'s' ,'me' ,'more' ,'most' ,'mustn\'t' ,'my' ,'myself' ,'no' ,'nor' ,'not' ,'of' ,'off' ,'on' ,'once' ,'only' ,'or' ,'other' ,'ought' ,'our' ,'ours', 'ourselves' ,'out' ,'over' ,'own' ,'same' ,'shan\'t' ,'she' ,'she\'d' ,'she\'ll' ,'she\'s' ,'should' ,'shouldn\'t' ,'so' ,'some' ,'such' ,'than' ,'that' ,'that\'s' ,'the' ,'their' ,'theirs' ,'them' ,'themselves' ,'then' ,'there' ,'there\'s' ,'these' ,'they' ,'they\'d' ,'they\'ll' ,'they\'re' ,'they\'ve' ,'this' ,'those' ,'through' ,'to' ,'too' ,'under' ,'until' ,'up' ,'very' ,'was' ,'wasn\'t' ,'we' ,'we\'d' ,'we\'ll' ,'we\'re' ,'we\'ve' ,'were' ,'weren\'t' ,'what' ,'what\'s' ,'when' ,'when\'s' ,'where' ,'where\'s' ,'which' ,'while' ,'who' ,'who\'s' ,'whom' ,'why' ,'why\'s' ,'with' ,'won\'t' ,'would' ,'wouldn\'t' ,'you' ,'you\'d' ,'you\'ll' ,'you\'re' ,'you\'ve' ,'your' ,'yours' ,'yourself' ,'yourselves'}

def scraper(url, resp):
    links = extract_next_links(url, resp)
    return [link for link in links if is_valid(link)]

def extract_next_links(url, resp):
    #list of all the links found in the url
    link_list = []

    file_handler = urlopen(url)
    parsed = BeautifulSoup(file_handler)
    #retrieve all the links found in the parsed url
    if 200 <= resp.status <= 599 and resp.status != 204:    #check if in a good HTTP code range, and check if there is content
    #parse the url contents                                  within the document (e.g. checking if code is not 204)
        for link_tag in parsed.find_all('a'):
            link = link_tag.get('href')
            link = link.split('#')[0]
            #checks if href contains a link like '/about' or '//www.stat.uci.edu'
            if link.startswith('//'):
                link = 'https:' + link
            elif link.startswith('/'):
                link = url + link
            link_list.append(link)
    print(url)
    print('\n#########\n')
    for url in link_list:
        print(url)
    print('\n#########\n')
    return link_list

def is_valid(url):
    try:
        parsed = urlparse(url)
        #check if scheme is valid
        if parsed.scheme not in set(["http", "https"]):
            return False
        #check for possible domains
        reg_domain = {r"(\.ics\.uci\.edu)$", r"(\.cs\.uci\.edu)$", r"(\.informatics\.uci\.edu)$", r"(\.stat\.uci\.edu)$",
        r"(ics\.uci\.edu)$", r"(cs\.uci\.edu)$", r"(informatics\.uci\.edu)$", r"(stat\.uci\.edu)$"}
        domain_valid = [re.match(regex_exp, parsed.netloc) for regex_exp in reg_domain]
        domain_valid.append(parsed.netloc == "today.uci.edu")
        if not any(domain_valid):
            print("\nINVALID DOMAIN: " + str(url))
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
    for token in re.sub('[^A-Za-z0-9\']+', ' ', token_string).split():
        word_count += 1
        if token not in STOP_WORDS:
            if token in token_dict or token_dict[token] == 0:
                token_dict[token] += 1
            else:
                token_dict[token] = 1

    #checks if the current parsed url is larger than the largest recorded parsed url
    if word_count > token_dict['largest_word_count']:
        token_dict['largest_word_count'] = word_count
        token_dict['largest_url'] = url

def process_content(url):
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
    with open("words.json", "r") as file_contents:
        json.dump(tokens, file_contents)
