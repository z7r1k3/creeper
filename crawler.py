import requests
from bs4 import BeautifulSoup

def crawl(totalLevels, levels, passedUrl):
    totalDepth = int(totalLevels)
    depth = int(levels)

    if(int(levels) > 0):
        code = requests.get(passedUrl)
        s = BeautifulSoup(code.content, "html.parser")

        for link in s.findAll('a'):
            href = str(link.get('href'))
            indent = ''

            # Only if domain is not the same as the one passed into this method
            if ('://' in href and not hasCrawled(href)):
                # Add line break at start of new branch
                if (depth == totalDepth):
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
                    urlList.append(urlStrip(href))

def hasCrawled(testUrl):
    check = urlStrip(testUrl)

    # Return True if URL has already been crawled
    for u in urlList:
        if (check == u):
            return True
        elif (u.endswith('/')):
            if (check == u[:-1]):
                return True
        elif (check.endswith('/')):
            if (check[:-1] == u):
                return True

    # Add URL to crawled list and return that it has not been crawled
    return False

def urlStrip(url):
    bareUrl = url

     # Remove http, https, and www to accurately compare URL's
    bareUrl = bareUrl.replace('http://', '')
    bareUrl = bareUrl.replace('https://', '')
    bareUrl = bareUrl.replace('www.', '')

    return bareUrl


urlList = []

# Get user variables
depth = input("How many levels deep should the crawler go?\n")
url = input("What is the target URL?\n")

crawl(depth, depth, url)

print (urlList)