import re
import urllib.request
import requests
from bs4 import BeautifulSoup

# var squad
fileEndings = ['.html','.asp','.php','.htm']
crawlList = {}
urlList = {}
#emailList = []
#phoneList = []

 # Just to clarify, totalDepth is the total jumps allowed from the starting URL
 # depth
def crawl(totalDepth, depth, ogUrl, passedUrl, logCode):
    isFtp = False

    if (depth > 0 and not hasCrawled(urlStrip(passedUrl))): # If URL hasn't been crawled, crawl it
        if (not '://' in passedUrl): # Only applies to first inputted link, as all others get prefixed from here on out
            passedUrl = 'http://' + passedUrl

        if (not (passedUrl.startswith('ftp://') or passedUrl.startswith('ftps://'))):
            code = requests.get(passedUrl)
            s = BeautifulSoup(code.content, 'html.parser')
        else:
            try:
                code = urllib.request.urlopen(passedUrl).read()
            except:
                print("ERROR: Unable to crawl")
                code = ''
            s = BeautifulSoup(code, features='lxml')
            s = ftpParse(s)
            isFtp = True        

        for link in getLink(s, isFtp):
            if (not isFtp):
                href = str(link.get('href'))
            else:
                href = link

            # If URL list already exists, append. Else, create
            if ((urlStrip(passedUrl) in urlList) and (href not in urlList[urlStrip(passedUrl)])): # If passedUrl is in urlList, and href is not an item in the urlList[passedUrl] list (two dimensional)
                urlList[urlStrip(passedUrl)].append(href)
            else:
                urlList[urlStrip(passedUrl)] = [href]


            # Merge path with domain if the URL is missing domain
            if (not (urlStrip(href).startswith(getDomain(ogUrl)) or '://' in href)):
                href = str(mergeUrl(passedUrl, href))
            
            # Print domain
            display(href, logCode, totalDepth, depth, ogUrl)

            # Only if link is crawlable
            if (isQualifiedLink(href)):
                # Crawl found link if depth allows it, and link is on entered domain
                if (depth > 1 and urlStrip(href).startswith(getDomain(ogUrl)) and urlStrip(href) != urlStrip(ogUrl)):
                    crawl(totalDepth, depth - 1, ogUrl, href, logCode)
        
        crawlList[urlStrip(passedUrl)] = True
    elif (depth > 0): # If URL has already been crawled, use the previously stored URL's
        for u in urlList[urlStrip(passedUrl)]:

            # Only if link is crawlable
            if (isQualifiedLink(u)):
                # Print domain
                display(u, logCode, totalDepth, depth, ogUrl)

                # Crawl found link if depth allows it, and link is on entered domain
                if (depth > 1 and urlStrip(u).startswith(getDomain(ogUrl)) and urlStrip(u) != urlStrip(ogUrl)):
                    crawl(totalDepth, depth - 1, ogUrl, u, logCode)


# def scrape()


def hasCrawled(testUrl):
    check = urlStrip(testUrl)

    # Return True if URL has already been crawled
    return (check in crawlList and check in urlList)


def urlStrip(url):
    bareUrl = url

     # Remove http, https, and www to accurately compare URL's
    bareUrl = bareUrl.replace('http://', '')
    bareUrl = bareUrl.replace('https://', '')
    bareUrl = bareUrl.replace('ftp://', '')
    bareUrl = bareUrl.replace('ftps://', '')
    bareUrl = bareUrl.replace('www.', '')
    bareUrl = bareUrl.replace(' ', '')

    if (bareUrl.startswith('//')):
        bareUrl = bareUrl[+2:]

    if (not bareUrl.endswith('/')):
        bareUrl += '/'

    return bareUrl


def display(text, logCode, totalDepth, depth, ogUrl):
    isRootUrl = (totalDepth == depth) and (urlStrip(text) != urlStrip(ogUrl))
    indent = ''

    # Handle formatting
    for i in range(depth, totalDepth):
        indent += '     '
    
    switch = {
        0: isRootUrl,
        1: True
    }

    if (switch[logCode] and depth > 1):
        print()

    if (switch[logCode] and isRootUrl and getDomain(ogUrl) in text and isQualifiedLink(text)):
        print(indent + text.replace(' ', '') + " | Crawling...")
    elif (switch[logCode]):
        print(indent + text.replace(' ', ''))


def getDomain(url):
    url = urlStrip(url)
    index = url.find('/')
    return url[:index]

def getPrefix(url):
    index = url.find('//')
    return url[:index+2]


def mergeUrl(domain, path):
    if (path.startswith('/')):
        return getPrefix(domain) + urlStrip(domain) + path[+1:]
    return getPrefix(domain) + urlStrip(domain) + path

# Make sure it isn't a mp3, json, png, jpg... Make sure it is a html, asp, php, ftp file without ending
def isQualifiedLink(href): # Not mailto etc.
    if (':' in href and not '://' in href): return False # If it has a : but no ://
    if (href.startswith('#')): return False         # false if it starts with << those things.
    if (href.endswith('../')): return False # FTP back links

    if (href.endswith('/')): href = href[:-1] # Remove trailing / for accurate extension comparison

    if ('.' in urlStrip(href).replace(getDomain(href), '')):
        for ending in fileEndings:
            if (href.endswith(ending)): return True
        return False
    return True


def ftpParse(soup):
    lines = str(soup).splitlines()
    items = []
    paths = []
    
    for i in range(0, len(lines)):
        for u in lines[i].split(' '):
            if (i in items and u.replace(' ', '') != ''):
                items[i].append(u)
            elif (u.replace(' ', '') != ''):
                items.append(i)
                items[i] = [u]

    for i in range (0, len(items)-1):
        index = 8
        string = ''
        if (re.search('[0-9]', items[i][0])):
            index = 7
        
        paths.append(i)
        
        for j in range(index, len(items[i])):
            string += items[i][j]
            if (index < len(items[i])-1 and j < len(items[i])-1):
                string += '%20'
        
        paths[i] = string
            
    return paths


def getLink(soup, isFtp):
    if (not isFtp):
        return soup.findAll('a')
    
    return soup


# START MAIN CODE

# Get user variables
url = input('What is the target URL?\n')
depth = int(input('How many levels deep should the crawler go?\n'))
log = int(input('''Please select a logging option:
0: Display root URL\'s
1: Display all URL\'s\n'''))

print('\n\nCrawling ' + url + '...\n')
crawl(depth, depth, url, url, log)