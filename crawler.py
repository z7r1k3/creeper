import requests
from bs4 import BeautifulSoup

def crawl(totalLevels, levels, ogUrl, passedUrl, output):
    totalDepth = totalLevels
    depth = levels

    if(depth > 0 and not hasCrawled(urlStrip(passedUrl))):
        if (not '://' in passedUrl and not passedUrl.startswith('/')):
            passedUrl = 'http://' + passedUrl
        code = requests.get(passedUrl)
        s = BeautifulSoup(code.content, "html.parser")

        for link in s.findAll('a'):
            href = str(link.get('href'))
            indent = ''

            # If list already exists, append. Else, create
            if (urlStrip(passedUrl) in urlList):
                if (href not in urlList[urlStrip(passedUrl)]):
                    urlList[urlStrip(passedUrl)].append(href)
            else:
                urlList[urlStrip(passedUrl)] = [href]

            # Only if domain is not the same as the one passed into this method
            if ('://' in href):                
                # Handle formatting
                for i in range(depth, totalDepth):
                    indent += '     '
                    i
                
                # Print domain
                display(indent + href.replace(' ', ''), output, totalDepth == depth, depth, ogUrl)

                # Get domains on found domain if depth allows it
                if (depth > 1 and getDomain(ogUrl) in href):
                    crawl(totalDepth, depth - 1, ogUrl, href, output)
        
        crawlList[urlStrip(passedUrl)] = True

    # If URL has already been crawled, use the previously stored URL's
    if (depth > 0 and hasCrawled(urlStrip(passedUrl))):
        for u in urlList[urlStrip(passedUrl)]:
            indent = ''

            if ('://' in u):
                # Handle formatting
                for i in range(depth, totalDepth):
                    indent += '     '
                    i

                # Print domain
                display(indent + u.replace(' ', ''), output, totalDepth == depth, depth, ogUrl)

                # Get domains on listed domain if depth allows it
                if (depth > 1 and getDomain(ogUrl) in u):
                    crawl(totalDepth, depth - 1, ogUrl, u, output)

        crawlList[urlStrip(passedUrl)] = True


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

    if (not bareUrl.endswith('/')):
        bareUrl += '/'

    return bareUrl


def display(text, logCode, isRootUrl, depth, ogUrl):
    switch = {
        0: isRootUrl,
        1: True
    }

    if (switch[logCode] and depth > 1):
        print()

    if (switch[logCode] and isRootUrl and getDomain(ogUrl) in text):
        print(text + " | Crawling...")
    elif (switch[logCode]):
        print(text)


def getDomain(url):
    index = urlStrip(url).find('/')

    return url[:index]


# START MAIN CODE

urlList = {}
crawlList = {}

# Get user variables
url = input("What is the target URL?\n")
depth = int(input("How many levels deep should the crawler go?\n"))
log = int(input("""Please select a logging option:
0: Display root URL's
1: Display all URL's\n"""))

crawl(depth, depth, url, url, log)