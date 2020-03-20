import requests
from bs4 import BeautifulSoup

# var squad
fileEndings = ['.html','.asp','.php','.htm']

 # Just to clarify, totalDepth is the total jumps allowed from the starting URL
 # depth
def crawl(totalDepth, depth, ogUrl, passedUrl, logCode):

    if (depth > 0 and not hasCrawled(urlStrip(passedUrl))): # If URL hasn't been crawled, crawl it
        if (not '://' in passedUrl and not passedUrl.startswith('/')):
            passedUrl = 'http://' + passedUrl
        code = requests.get(passedUrl)
        s = BeautifulSoup(code.content, 'html.parser')

        for link in s.findAll('a'):
            href = str(link.get('href'))

            # If URL list already exists, append. Else, create
            if (urlStrip(passedUrl) in urlList):
                if (href not in urlList[urlStrip(passedUrl)]):
                    urlList[urlStrip(passedUrl)].append(href)
            else:
                urlList[urlStrip(passedUrl)] = [href]

            # Only if link is crawlable
            if (isQualifiedLink(href)):                
                # Print domain
                display(href, logCode, totalDepth, depth, ogUrl)

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


def hasCrawled(testUrl):
    check = urlStrip(testUrl)

    # Return True if URL has already been crawled
    if (check in crawlList and check in urlList):
        return True

    # Return that it has not been crawled
    return False


def urlStrip(url):
    bareUrl = url

     # Remove http, https, and www to accurately compare URL's
    bareUrl = bareUrl.replace('http://', '')
    bareUrl = bareUrl.replace('https://', '')
    bareUrl = bareUrl.replace('ftp://', '')
    bareUrl = bareUrl.replace('www.', '')

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

    # Merge path with domain if the URL is missing domain
    if ('://' not in text):
        text = str(mergeUrl(ogUrl, text))
    
    switch = {
        0: isRootUrl,
        1: True
    }

    if (switch[logCode] and depth > 1):
        print()

    if (switch[logCode] and isRootUrl and getDomain(ogUrl) in text):
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
        return getPrefix(domain) + getDomain(domain) + path
    return getPrefix(domain) + getDomain(domain) + '/' + path


# Make sure it isn't a mp3, json, png, jpg... Make sure it is a html, asp, php, ftp file without ending
def isQualifiedLink(href): # Not mailto etc.
    if(href.startswith('//') or href.startswith('#')): return False         # false if it starts with << those things.
    for ending in fileEndings:
        if(href.endswith(ending)): return True
    # add support for FTP links
    return False
    


# START MAIN CODE

crawlList = {}
urlList = {}
#emailList = []
#phoneList = []

# Get user variables
url = input('What is the target URL?\n')
depth = int(input('How many levels deep should the crawler go?\n'))
log = int(input('''Please select a logging option:
0: Display root URL\'s
1: Display all URL\'s\n'''))

print('\n\nCrawling ' + url + '...\n')
crawl(depth, depth, url, url, log)