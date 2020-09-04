# Version 1.1.0
import datetime
import re
import urllib.request
from bs4 import BeautifulSoup

# Config var squad
defaultLogPath = 'logs/' # Determines where logs are stored. Do not forget to put a '/' at the end
fileEndings = ['.html', '.htm', '.php', '.asp', '.cfm'] # Determines what URLs/files will always be crawled, even if ftp(s)://
disqualifyEndings = ['/LICENSE'] # If a URL ends with any of these, do not consider a qualified URL for crawling. Do NOT put '/' at the end
disqualifyBeginnings = ['mailto:', 'tel:'] # If a URL starts with any of these, do not consider a qualified URL for crawling
stripText = ['http://', 'https://', 'ftp://', 'ftps://', 'www.', ' '] # Determines what strings are removed from URLs when stripping
markupTags = ['a', 'link', 'script', 'iframe', 'img'] # Determines tags parsed from webpage source code
attributes = ['href', 'src'] # Determines attributes checked from tags to retrieve URLs
ignoreList = [None, '#']

# Var squad
ogUrl = ''
ogUrlDomain = ''
totalDepth = 0
alreadyCrawled = []
urlList = {}
emailList = []
phoneList = []
timestamp = ''
offset = 8 # FTP parsing returns a bunch of separate, useless items (like dates, etc.) and this offsets it to only take the file path
urlLogPath = defaultLogPath + 'url/'
emailLogPath = defaultLogPath + 'email/'
phoneLogPath = defaultLogPath + 'phone/'
urlLog = None
emailLog = None
phoneLog = None


class CrawlJob:
    def __init__(self, depth, url):
        self.depth = depth # Current, not total, depth level (starts at total depth and counts down to 0)
        self.url = rebuildLink(url)

        # Non args
        self.soup = None
        self.checkLink = getCheckLink(self.url) # Remove inconsistencies in prefixes, etc. for accurate comparisons
        

def crawl(depth, url):
    currentCrawlJob = CrawlJob(depth, url)


    if (currentCrawlJob.depth > 0 and not currentCrawlJob.checkLink in alreadyCrawled): # If URL hasn't been crawled, crawl it
        currentCrawlJob.soup = getSoup(currentCrawlJob.url)

        for tag in getTagList(currentCrawlJob.url, currentCrawlJob.soup):
            parsedUrl = parseTag(currentCrawlJob.url, tag)

            if (parsedUrl in ignoreList): continue # Barrier to prevent processing None, etc.

            parsedUrlHasPrefix = parsedUrl.startswith('//') or '://' in parsedUrl


            # Merge path with domain if the URL is missing domain
            if (not parsedUrlHasPrefix and not isQualifiedEmail(parsedUrl) and not isQualifiedPhone(parsedUrl)):
                parsedUrl = mergeUrl(currentCrawlJob.url, parsedUrl)

            # If URL list already exists, append. Else, create
            if ((currentCrawlJob.checkLink in urlList) and (parsedUrl not in urlList[currentCrawlJob.checkLink])): # If parsedUrl needs to be added to the existing urlList
                urlList[currentCrawlJob.checkLink].append(parsedUrl)
            elif ((currentCrawlJob.checkLink in urlList) and (parsedUrl in urlList[currentCrawlJob.checkLink])): # If parsedUrl is already in the existing urlList
                continue
            else: # parsedUrl needs to be added as first entry to a new urlList
                urlList[currentCrawlJob.checkLink] = [parsedUrl]
            
            log(currentCrawlJob.depth, parsedUrl)

            # Only if URL is crawlable
            if (isQualifiedLink(parsedUrl)):
                # Crawl found URL if depth allows it, and URL is on entered domain
                if (currentCrawlJob.depth > 1 and urlStrip(parsedUrl).startswith(ogUrlDomain) and urlStrip(parsedUrl) != urlStrip(ogUrl)):
                    crawl(currentCrawlJob.depth - 1, parsedUrl)
        
        alreadyCrawled.append(currentCrawlJob.checkLink)

    elif (currentCrawlJob.depth > 0): # If URL has already been crawled, use the previously stored URL's
        for u in urlList[currentCrawlJob.checkLink]:

            # Only if URL is crawlable
            if (isQualifiedLink(u)):
                log(currentCrawlJob.depth, u)

                # Crawl found URL if depth allows it, and URL is on entered domain
                if (currentCrawlJob.depth > 1 and urlStrip(u).startswith(ogUrlDomain) and urlStrip(u) != urlStrip(ogUrl)):
                    crawl(currentCrawlJob.depth - 1, u)


def ftpParse(soup): # Get contents of FTP soup and return all file paths as a list
    lines = str(soup).splitlines()
    items = []
    paths = []
    index = 0


    for line in lines: # Get each individual line
        for value in line.split(' '): # Separate values on each line by whitespace
            if ((len(items) == index + 1) and value.replace(' ', '') != ''): # If it already exists, append. If it's just whitespace, don't worry about it
                items[index].append(value)
            elif (value.replace(' ', '') != ''): # Doesn't already exist, so create
                items.append(index)
                items[index] = [value]
        if (len(items) > index): index += 1 # (len(items) > index) protects against index out of bounds, in the event a wrong file is crawled and the outcome is unpredictable

    for i in range(0, len(items)): # For each item in items, but give me an index number to work with (i)
        string = ''
        
        paths.append(i)
        
        for j in range(offset, len(items[i])): # Parsing paths from items, and converting them into URL's
            string += items[i][j]
            if (offset < len(items[i])-1 and j < len(items[i])-1): # If there's multiple items in this path, since they were separated by whitespace the path had a space
                string += '%20' # %20 is a space in a URL
        
        paths[i] = string
            
    return paths


def getCheckLink(url): # Return a uniform link so that links don't get added twice (i.e. the 'http://' and 'https://' versions)
    if (getPrefix(url).startswith('http')):
        return 'http://' + urlStrip(url)
    elif (getPrefix(url).startswith('ftp')):
        return 'ftp://' + urlStrip(url)

    print("ERROR-3: Unkown prefix | " + url)
    return urlStrip(url)


def getDomain(url): # Return domain only of passed URL (i.e. 'example.org' if passed 'http://example.org/about-us')
    url = urlStrip(url) + '/'


    # Return from start of string to first '/'
    return url[:url.find('/')]

def getPrefix(url): # Return prefix only of passed URL (i.e. http://, ftp://, etc.)
    if (isQualifiedEmail(url) or isQualifiedPhone(url)):
        return ''

    if ('//' in url and not url.startswith('//')):
        index = url.find('//')
        return url[:index+2]

    return 'http://' # Default to this prefix if none is included


def getSoup(url):
    try: # Read and store code for parsing
        code = urllib.request.urlopen(url).read()
    except:
        if (displayLevel > 0): print("ERROR-1: Unable to crawl | " + url)
        code = ''
    
    if (isHtmlParse(url)): # Not FTP, or FTP but webfile i.e. index.html
        soup = BeautifulSoup(code, 'html.parser') # Setup to parse for HTML, etc. tags
    else:
        soup = BeautifulSoup(code, features='lxml') # Setup to parse for FTP links

    return soup


def getTagList(url, soup): # Return a list of links
    if (isHtmlParse(url)): # If it is not an FTP URL, or it is but it's a webpage (i.e. .html file), bs can parse for the <a> tags
        return soup.findAll(markupTags)
    
    # If it is an FTP URL, and not a webpage (i.e. not a .html file), return resulting list of tags from ftpParse()
    return ftpParse(soup)


def isFtp(url):
    if ((url.startswith('ftp://') or url.startswith('ftps://'))):
        return True

    return False


def isHtmlParse(url):
    ftp = isFtp(url)
    webFile = isWebFile(url)


    return (not ftp) or (ftp and webFile) # Not FTP, or is FTP with webfile (.html, etc.)


def isQualifiedEmail(url): # Return boolean on whether the passed href is a valid email or not
    if (url.startswith('mailto:') and url.replace('mailto:', '') != ''):
        return True

    return False


def isQualifiedLink(url): # Return boolean on whether the passed href is crawlable or not (i.e. not a mailto: or .mp3 file)
    if (urlStrip(url).endswith('..')): return False # Back links

    for u in disqualifyEndings:
        if (url.endswith(urlStrip(u))):
            return False

    for u in disqualifyBeginnings:
        if (url.startswith(urlStrip(u))):
            return False

    if (url.endswith('/')): url = url[:-1] # Remove trailing / for accurate extension comparison

    if ('.' in urlStrip(url).replace(ogUrl, '').replace(getDomain(url), '').replace('/.', '')): # After removing the domain, prefix, and any '/.' (i.e. unix hidden folders/files), if there's a '.' left, check like a file extension
        return isWebFile(url)

    return True


def isQualifiedPhone(url): # Return boolean on whether the passed href is a valid phone number or not
    if (url.startswith('tel:') and url.replace('tel:', '') != ''):
        return True

    return False


def isWebFile(url): # Return boolean on whether the passed href ends with one of the extensions in fileEndings or not
    if (url.endswith('/')): url = url[:-1] # Remove last '/' if applicable

    for ending in fileEndings:
        if (url.endswith(ending)): # If it has a webpage file ending like .html, etc.
            return True

    return False


def log(depth, text): # If it's a URL, and the log code allows it, format and display the passed text to the console
    isRootUrl = (totalDepth == depth) and (urlStrip(text) != urlStrip(ogUrl))
    indent = ''
    text = rebuildLink(text)


    # Handle formatting
    for i in range(depth, totalDepth):
        indent += '     '
    
    switch = {
        0: False,
        1: isRootUrl,
        2: True,
    }

    if (not isQualifiedEmail(text) and not isQualifiedPhone(text)):
        if (switch[displayLevel] and depth > 1):
            print()

        if (switch[displayLevel] and isRootUrl and urlStrip(text).startswith(ogUrlDomain) and isQualifiedLink(text)): # If it's a root URL that it's going to crawl
            print(indent + text.replace(' ', '') + " | Crawling...")
        elif (switch[displayLevel]):
            print(indent + text.replace(' ', ''))

        if (save): urlLog.write(indent + text.replace(' ', '') + '\n')
        
    elif (scrape and isQualifiedEmail(text)):
        text = text.replace('mailto:', '')


        if (text not in emailList):
            emailList.append(text)

            if (save): emailLog.write(text + '\n')
        
    elif (scrape and isQualifiedPhone(text)):
        text = text.replace('tel:', '')


        if (text not in phoneList):
            phoneList.append(text)

            if save: phoneLog.write(text + '\n')


def mergeUrl(url, ogPath): # Merge passed domain with passed path (i.e. 'example.org' and '/about-us' to 'example.org/about-us')
    path = ogPath
    prefix = getPrefix(url)


    if (url.endswith('/')): url = url[:-1] # Trim last '/' in domain if applicable

    # If current domain is a webfile (i.e. ends with '.html') we need to remove the file before merging the path
    if (isWebFile(url)): url = url[:url.rindex('/')] # Remove everything after and including new last '/'
    
    while (path.startswith('#/') or path.startswith('/#')):
        path = path[path.index('#')+1:] # Remove everything up to and including the first '#' from path


    if (path.startswith('/')): # i.e. /example/path should start at the raw domain
        return prefix + getDomain(url) + path

    # Handle '..' backpage href shortcuts
    while (path.startswith('..')):
        path = path[path.index('..')+3:] # Remove everything up to and including the first '..' from path

        try:
            url = prefix + urlStrip(url)[:urlStrip(url).rindex('/')] # Remove everything after new last '/', essentially going back a folder
        except:
            if (displayLevel > 0): print('ERROR-2: Too many back links | ' + ogPath)
        # urlStrip ensures the '/' in the prefix (i.e. 'http://') doesn't get counted

    if (not url == prefix): # If domain is more than just a prefix like http://
        return str(prefix + urlStrip(url) + '/' + path)

    return '' # If we erased the domain above, we have a '..' back link with no previous folder to go back to, so we return nothing as it is worthless

        
def parseTag(parentUrl, tag):
    result = ''


    if (isHtmlParse(parentUrl)): # Is a crawlable web file, FTP or otherwise
        for u in attributes:
            result = tag.get(u)

            if (result != None):
                break

    else: # Is FTP and not a web file
        result = tag

    return result


def rebuildLink(url): # Ensure that link is able to be crawled (i.e. replace '//' with 'http://'), while preserving the existing prefix if it has one
    return getPrefix(url) + urlStrip(url)


def urlStrip(url): # Returns the bare URL after removing http, https, www, etc. (i.e. 'example.org' instead of 'http://www.example.org')
    bareUrl = url


    for u in stripText:
        bareUrl = bareUrl.replace (u, '')

    if (bareUrl.startswith('//')):
        bareUrl = bareUrl[+2:]

    if (bareUrl.endswith('/')):
        bareUrl = bareUrl[:-1]

    return bareUrl



# START MAIN CODE

# Get user variables
url = input('\nPlease enter the target URL(s), separated by spaces:\n').split(' ')
totalDepth = int(input('\nPlease enter how many levels deep the crawler should go:\n'))
scrape = input('''
Do you want to scrape for emails and phone numbers?
y: yes
n: no
''')

scrape = scrape.lower() == 'y' or scrape.lower() == 'yes'

save = input('''
Would you like to save all data to files in the /logs folder?
y: yes
n: no
''')
    
save = save.lower() == 'y' or save.lower() == 'yes'

displayLevel = int(input('''
Please select a logging display option:
0: Quiet
1: Standard
2: Verbose
'''))

# Create timestamp for log files
now = str(datetime.datetime.now())

now = re.split(' |:', now[:now.rindex('.')])

for u in now:
    timestamp += u + '-'

timestamp = timestamp[:-1] # Trim last '-'

# Form the complete paths including the log files themselves
urlLogPath += timestamp + '.txt'
emailLogPath += timestamp + '.txt'
phoneLogPath += timestamp + '.txt'

# Open log files if applicable
if (save):
    urlLog = open(urlLogPath, 'w+')
    if (scrape):
        emailLog = open(emailLogPath, 'w+')
        phoneLog = open(phoneLogPath, 'w+')
        
# Begin crawling/scraping
for link in url: # Crawl for each URL the user inputs
    ogUrl = link
    ogUrlDomain = getDomain(ogUrl)

    print('\n\n\nCrawling ' + link + '\n')
    crawl(totalDepth, link)

if (scrape and displayLevel > 0):
    print('\n\n\nEmails:\n')

    for email in emailList:
        print(email)

    print('\n\n\nPhone Numbers:\n')

    for phone in phoneList:
        print(phone)