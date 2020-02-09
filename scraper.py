import re
from urllib.parse import urlparse
from urllib.request import urlopen
from bs4 import BeautifulSoup

def scraper(url, resp):
    links = extract_next_links(url, resp)
    return [link for link in links if is_valid(link)]

def extract_next_links(url, resp):
    #list of all the links found in the url
    link_list = []

    #parse the url contents
    file_handler = urlopen(url)
    parsed = BeautifulSoup(file_handler)

    #retrieve all the links found in the parsed url
    for link in parsed.find_all('a'):
        link_list.append(link.get('href'))
    return link_list

def is_valid(url):
    try:
        parsed = urlparse(url)
        #check if scheme is valid
        if parsed.scheme not in set(["http", "https"]):
            return False
        #check for possible domains
        reg_domain = {r"(\.ics\.uci\.edu)$", r"(\.cs\.uci\.edu)$", r"(\.informatics\.uci\.edu)$", r"(\.stat\.uci\.edu)$"}
        domain_valid = [re.match(regex_exp, parsed.netloc) for regex_exp in reg_domain]
        domain_valid.append(parsed.netloc == "today.uci.edu")
        if not any(domain_valid):
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