import re
from urllib.parse import urlparse
from urllib.request import urlopen
from bs4 import BeautifulSoup
import os
import requests

data_dict = {"url_count": 0, "largest_word_count": 0, "largest_url": "", "words": {}}
visited_urls = set()
ics_subdomains = {}
tracker = 0
STOP_WORDS = {'a', 'about' ,'above' ,'after' ,'again' ,'against' ,'all' ,'am' ,'an' ,'and' ,'any' ,'are' ,'aren\'t' ,'as' ,'at' ,'be' ,'because' ,'been' ,'before' ,'being' ,'below' ,'between' ,'both' ,'but' ,'by' ,'can\'t' ,'cannot' ,'could' ,'couldn\'t' ,'did' ,'didn\'t' ,'do' ,'does' ,'doesn\'t' ,'doing' ,'don\'t' ,'down' ,'during' ,'each' ,'few' ,'for' ,'from' ,'further' ,'had' ,'hadn\'t' ,'has' ,'hasn\'t' ,'have' ,'haven\'t' ,'having' ,'he' ,'he\'d' ,'he\'ll' ,'he\'s' ,'her' ,'here' ,'here\'s' ,'hers' ,'herself' ,'him' ,'himself' ,'his' ,'how' ,'how\'s' ,'i' ,'i\'d' ,'i\'ll' ,'i\'m' ,'i\'ve' ,'if' ,'in' ,'into' ,'is' ,'isn\'t' ,'it' ,'it\'s' ,'its' ,'itself' ,'let\'s' ,'me' ,'more' ,'most' ,'mustn\'t' ,'my' ,'myself' ,'no' ,'nor' ,'not' ,'of' ,'off' ,'on' ,'once' ,'only' ,'or' ,'other' ,'ought' ,'our' ,'ours', 'ourselves' ,'out' ,'over' ,'own' ,'same' ,'shan\'t' ,'she' ,'she\'d' ,'she\'ll' ,'she\'s' ,'should' ,'shouldn\'t' ,'so' ,'some' ,'such' ,'than' ,'that' ,'that\'s' ,'the' ,'their' ,'theirs' ,'them' ,'themselves' ,'then' ,'there' ,'there\'s' ,'these' ,'they' ,'they\'d' ,'they\'ll' ,'they\'re' ,'they\'ve' ,'this' ,'those' ,'through' ,'to' ,'too' ,'under' ,'until' ,'up' ,'very' ,'was' ,'wasn\'t' ,'we' ,'we\'d' ,'we\'ll' ,'we\'re' ,'we\'ve' ,'were' ,'weren\'t' ,'what' ,'what\'s' ,'when' ,'when\'s' ,'where' ,'where\'s' ,'which' ,'while' ,'who' ,'who\'s' ,'whom' ,'why' ,'why\'s' ,'with' ,'won\'t' ,'would' ,'wouldn\'t' ,'you' ,'you\'d' ,'you\'ll' ,'you\'re' ,'you\'ve' ,'your' ,'yours' ,'yourself' ,'yourselves'}
# traps = {"https://www.ics.uci.edu/community/involved/", "https://www.ics.uci.edu/ugrad/policies/Grade_Options/", "https://www.ics.uci.edu/accessibility/community/", "https://www.ics.uci.edu/involved/corporate_partner.php/",
        # "https://mswe.ics.uci.edu/contact-us/faq/"}
traps = set()
def scraper(url, resp):
    global tracker
    tracker += 1
    print(tracker)
    valid_links = []
    if 200 <= resp.status <= 299 and resp.status != 204:
        visited_urls.add(url)
        process_content(url, resp)
        links = extract_next_links(url, resp)
        for link in links:
            if link != None  and link != "" and is_valid(link):
                #records the url if it is a subdomain of ics.uci.edu
                valid_links.append(link)
                parsed = urlparse(link)
                result = re.match(r'(.+)\.ics\.uci\.edu', parsed.netloc)
                if bool(result) and result[1] != 'www':
                    subdomain = result[1]
                    if subdomain in ics_subdomains:
                        ics_subdomains[subdomain].add(parsed.path)
                    else:
                        ics_subdomains[subdomain] = {parsed.path}
                visited_urls.add(link)

    # ----------------------------------------------------------------------------------------------
    #write shared values to .txt
    if tracker % 50 == 0:
        with open("subdomains.txt", "w") as file_contents:
            file_contents.write(str(ics_subdomains))
        with open("data.txt", "w") as file_contents:
            file_contents.write(str(data_dict))
    # ----------------------------------------------------------------------------------------------
    return valid_links

def extract_next_links(url, resp):
    #list of all the links found in the url
    url = url.replace(' ', '%')
    link_list = []
    #check HTTP Status
    file_handler = urlopen(url)
    parsed = BeautifulSoup(file_handler)
    url_parsed = urlparse(url)

    #retrieve all the links found in the parsed url
    #parse the url contents  
    for link_tag in parsed.find_all('a', href=True):
        link = link_tag.get('href')
        link = link.split('#')[0]
        #checks if href contains a link like '/about' or '//www.stat.uci.edu'
        if link.startswith('//'):
            pass
        #    link = 'https:' + link
        elif link.startswith('/'):
            link = "https://" + url_parsed.netloc + link
        if link != "" and link != None:
            link_list.append(link)
    return link_list

def is_valid(url):
    if url == None or url == "":
        return False
    #print("CURRENT URL:\t" + str(url))
    try:
        if url in visited_urls or url in traps:
            return False
        parsed = urlparse(url)
        #check if scheme is valid
        if parsed.scheme not in set(["http", "https"]):
            return False
        if not parsed.query == '':
            return False

        #check for possible domains
        reg_domains = r'(\S+\.)*(ics|cs|informatics|stat)\.uci\.edu'
        #reg_domains = r'(\S+\.)*(stat)\.uci\.edu'
        domain_valid = [re.match(reg_domains, parsed.netloc)]
        domain_valid.append(parsed.netloc == "today.uci.edu" and re.match(r'^(\/department\/information_computer_sciences\/)', parsed.path))
        if not any(domain_valid):
            return False
        if bool(domain_valid[0]) and domain_valid[0][1] != None and (domain_valid[0][1].rstrip('.') == "calendar" ):
            return False
        #checking for ICS Calendar Web Cralwer Trap and other types of traps
        #using a regex expression detecting for the calendar and
        #the end of a pathname being solely a number
        if parsed.netloc == "today.uci.edu" and re.match(r"^(\/department\/information_computer_sciences\/calendar\/)", parsed.path):
            return False
        if re.match(r'(\/\S+)*\/(\d+\/?)$', parsed.path) or re.match(r'^(\/tags?)\/?(\S+\/?)?', parsed.path):
            return False
        directory_path = parsed.path.lower().split('/')
        if "pdf" in directory_path or "faq" in directory_path or "zip-attachment" in directory_path:
            return False
        #getting rid of low information pages - from Ramesh Jain
        # note: these pages are simply pages that link to his other blog posts, their main information is just links to other pages
        # which our crawler already covers ^^

        #check for valid path
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

def record_content(token_string, url):
    word_count = 0
    data_dict["url_count"] += 1

    #records the contents of the string 
    for token in re.sub('[^A-Za-z\']+', ' ', token_string.lower()).split():
        word_count += 1
        if token not in STOP_WORDS:
            if token in data_dict["words"]:
                data_dict["words"][token] += 1
            else:
                data_dict["words"][token] = 1

    #checks if the current parsed url is larger than the largest recorded parsed url
    if 'largest_word_count' not in data_dict or word_count > data_dict['largest_word_count']:
        data_dict['largest_word_count'] = word_count
        data_dict['largest_url'] = url

def process_content(url, resp):
    if 200 <= resp.status <= 299 and resp.status != 204:
        #parse the url contents
        file_handler = urlopen(url)
        parsed = BeautifulSoup(file_handler)

        #gets the webpage content and records the words found in it
        content = parsed.get_text()
        record_content(content, url)

