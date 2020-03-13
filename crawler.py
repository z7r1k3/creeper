import requests
from bs4 import BeautifulSoup

def crawl(totalLevels, levels, passedUrl):
    totalDepth = int(totalLevels)
    depth = int(levels)

    if(depth > 0 and not hasCrawled(urlStrip(passedUrl))):
        code = requests.get(passedUrl)
        s = BeautifulSoup(code.content, "html.parser")

        for link in s.findAll('a'):
            href = str(link.get('href'))
            indent = ''

            # If list already exists, append. Else, create
            if (urlStrip(passedUrl) in urlList):
                urlList[urlStrip(passedUrl)].append(href)
            else:
                urlList[urlStrip(passedUrl)] = [href]

            # Only if domain is not the same as the one passed into this method
            if ('://' in href):
                # Add line break at start of new branch
                if (depth > 1):
                    print()
                
                # Handle formatting
                for i in range(depth, totalDepth):
                    indent += '     '
                    i
                
                # Print domain
                print(indent + href)

                # Get domains on found domain if depth allows it
                if (depth > 1):
                    crawl(totalDepth, depth - 1, href)

    # If URL has already been crawled, use the previously stored URL's
    if (depth > 0 and hasCrawled(urlStrip(passedUrl))):
        for u in urlList[urlStrip(passedUrl)]:
            indent = ''

            if ('://' in u):
                # Add line break at start of new branch
                if (depth > 1):
                    print()

                # Handle formatting
                for i in range(depth, totalDepth):
                    indent += '     '
                    i

                # Print domain
                print(indent + u)

                # Get domains on listed domain if depth allows it
                if (depth > 1):
                    crawl(totalDepth, depth - 1, u)


def hasCrawled(testUrl):
    check = urlStrip(testUrl)

    # Return True if URL has already been crawled
    if (check in urlList):
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



# START MAIN CODE

urlList = {}

# Get user variables
depth = input("How many levels deep should the crawler go?\n")
url = input("What is the target URL?\n")

crawl(depth, depth, url)