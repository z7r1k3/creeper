# Version 1.2.0
from bs4 import BeautifulSoup
import datetime
import re
import traceback
import urllib.request

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
offset = 8 # FTP parsing returns a bunch of separate, useless items (like dates, etc.) and this offsets it to only take the file path
errorCount = 0
errorLog = None


class CrawlJob:
    def __init__(self, depth, url):
        self.depth = depth # Current, not total, depth level (starts at total depth and counts down to 0)
        self.url = rebuildLink(url)

        # Non args
        self.soup = None # Will be set later, prior to being called
        self.checkLink = getCheckLink(self.url) # Remove inconsistencies in prefixes, etc. for accurate comparisons


class Error:
    def __init__(self, errorCode, errorUrl, errorExceptionType, errorException):
        errorMessage = ['Unable to crawl', 'Too many back links', 'Unkown prefix']
        global errorCount
        errorCount += 1
        self.count = errorCount
        self.code = errorCode
        self.message = errorMessage[self.code]
        self.url = errorUrl
        self.exceptionType = errorExceptionType
        self.exception = errorException


class LogPath:
    def __init__(self):
        timestamp = getTimestamp()
        self.url = defaultLogPath + 'url/' + timestamp + '.txt'
        self.email = defaultLogPath + 'email/' + timestamp + '.txt'
        self.phone = defaultLogPath + 'phone/' + timestamp + '.txt'
        self.error = defaultLogPath + '.error/' + timestamp + '.txt'

        

def crawl(depth, url):
    currentCrawlJob = CrawlJob(depth, url)


    if (currentCrawlJob.depth > 0 and not currentCrawlJob.checkLink in alreadyCrawled):
        currentCrawlJob.soup = getSoup(currentCrawlJob.url)

        if (currentCrawlJob.checkLink not in urlList): urlList[currentCrawlJob.checkLink] = []

        for tag in getTagList(currentCrawlJob.url, currentCrawlJob.soup):
            parsedUrl = parseTag(currentCrawlJob.url, tag)

            if (parsedUrl in ignoreList): continue # Barrier to prevent processing None, etc.

            parsedUrlHasPrefix = '://' in parsedUrl or parsedUrl.startswith('//')


            # Merge path with domain if the URL is missing domain
            if (not parsedUrlHasPrefix and not isQualifiedEmail(parsedUrl) and not isQualifiedPhone(parsedUrl)):
                parsedUrl = mergeUrl(currentCrawlJob.url, parsedUrl)

            if (parsedUrl not in urlList[currentCrawlJob.checkLink]): urlList[currentCrawlJob.checkLink].append(parsedUrl)

            else: continue
            
            log(currentCrawlJob.depth, parsedUrl)

            if (isQualifiedLink(parsedUrl)):
                # Crawl found URL if depth allows it, and URL is on entered domain
                if (currentCrawlJob.depth > 1 and urlStrip(parsedUrl).startswith(ogUrlDomain) and urlStrip(parsedUrl) != urlStrip(ogUrl)):
                    crawl(currentCrawlJob.depth - 1, parsedUrl)
        
        alreadyCrawled.append(currentCrawlJob.checkLink)

    elif (currentCrawlJob.depth > 0): # If URL has already been crawled, use the previously stored URL's
        for url in urlList[currentCrawlJob.checkLink]:

            if (isQualifiedLink(url)):
                log(currentCrawlJob.depth, url)

                # Crawl found URL if depth allows it, and URL is on entered domain
                if (currentCrawlJob.depth > 1 and urlStrip(url).startswith(ogUrlDomain) and urlStrip(url) != urlStrip(ogUrl)):
                    crawl(currentCrawlJob.depth - 1, url)


def ftpParse(soup): # Get contents of FTP soup and return all file paths as a list
    lines = str(soup).splitlines()
    paths = []

    for singleLine in lines:
        lineItems = [x for x in singleLine.split(' ') if x != ''] # Extract all items from that line, separating by whitespace and excluding empty items i.e. ''

        del lineItems[0:8] # Index 8 and further are all parts of the file path. Prior to that are dates, owners, and other unrelated items

        paths.append('%20'.join(lineItems)) # If there are multiple lineItems at this point, the path has at least one space in it and needs '%20' in the URL to represent each
            
    return paths


def getCheckLink(url): # Return a uniform link so that links don't get added twice (i.e. the 'http://' and 'https://' versions)
    if (getPrefix(url).startswith('http')):
        return 'http://' + urlStrip(url)

    elif (getPrefix(url).startswith('ftp')):
        return 'ftp://' + urlStrip(url)

    log(0, Error(2, url, None, None)) # Unknown prefix
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
    except Exception as e:
        log(0, Error(0, url, e, traceback.format_exc())) # Unable to crawl
        code = ''
    
    if (isHtmlParse(url)): # Not FTP, or FTP but webfile i.e. index.html
        soup = BeautifulSoup(code, 'html.parser') # Setup to parse for HTML, etc. tags
    else:
        soup = BeautifulSoup(code, features='lxml') # Setup to parse for FTP links

    return soup


def getTagList(url, soup): # Return a list of links
    if (isHtmlParse(url)): # If it is not an FTP URL, or it is but it's a webpage (i.e. .html file), bs can parse for the tags
        return soup.findAll(markupTags)
    
    # If it is an FTP URL, and not a webpage (i.e. not a .html file), return resulting list of tags from ftpParse()
    return ftpParse(soup)


def getTimestamp():
    now = str(datetime.datetime.now()) # Example: '2020-09-28 19:49:22.108946'
    now = re.split(' |:', now[:now.rindex('.')]) # Split by ' ' and ':' and remove everything after and including the '.'
    timestamp = '-'.join(now)

    return timestamp


def isFtp(url):
    if ((url.startswith('ftp://') or url.startswith('ftps://'))):
        return True

    return False


def isHtmlParse(url):
    ftp = isFtp(url)
    webFile = isWebFile(url)


    return (not ftp) or (ftp and webFile) # Not FTP, or is FTP with webfile (.html, etc.)


def isQualifiedEmail(url): # Return boolean on whether the passed item is a valid email or not
    if (url.startswith('mailto:') and url.replace('mailto:', '') != ''):
        return True

    return False


def isQualifiedLink(url): # Return boolean on whether the passed item is crawlable or not (i.e. not a mailto: or .mp3 file)
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


def isQualifiedPhone(url): # Return boolean on whether the passed item is a valid phone number or not
    if (url.startswith('tel:') and url.replace('tel:', '') != ''):
        return True

    return False


def isWebFile(url): # Return boolean on whether the passed URL ends with one of the extensions in fileEndings or not
    if (url.endswith('/')): url = url[:-1] # Remove last '/' if applicable

    for ending in fileEndings:
        if (url.endswith(ending)): # If it has a webpage file ending like .html, etc.
            return True

    return False


def log(depth, entry): # entry can be either a string (URL, Phone, Email) or an Error()
    indent = ''

    if (type(entry) is Error):
        global errorLog
        errorMessage = 'ERROR ' + str(entry.count) + '.' + str(entry.code) + ': ' + entry.message + ' | ' + entry.url

        if (errorLog == None): errorLog = open(logPath.error, 'w+')

        if (displayLevel > 0): print(errorMessage)

        errorLog.write(errorMessage)

        if (entry.exceptionType is not None and entry.exception is not None):
            errorLog.write('\n\n' + str(entry.exceptionType) + '\n\n' + entry.exception + '\n\n\n')
        else:
            errorLog.write('\n\n\n')

    elif (type(entry) is str):
        isRootUrl = (totalDepth == depth) and (urlStrip(entry) != urlStrip(ogUrl))
        entry = rebuildLink(entry)

        # Handle formatting
        for i in range(depth, totalDepth):
            indent += '     '
        
        switch = {
            0: False,
            1: isRootUrl,
            2: True,
        }

        if (not isQualifiedEmail(entry) and not isQualifiedPhone(entry)):
            if (switch[displayLevel] and depth > 1):
                print()

            if (switch[displayLevel] and isRootUrl and urlStrip(entry).startswith(ogUrlDomain) and isQualifiedLink(entry)): # If it's a root URL that it's going to crawl
                print(indent + entry.replace(' ', '') + " | Crawling...")
            elif (switch[displayLevel]):
                print(indent + entry.replace(' ', ''))

            if (save): urlLog.write(indent + entry.replace(' ', '') + '\n')
            
        elif (scrape and isQualifiedEmail(entry)):
            entry = entry.replace('mailto:', '')


            if (entry not in emailList):
                emailList.append(entry)

                if (save): emailLog.write(entry + '\n')
            
        elif (scrape and isQualifiedPhone(entry)):
            entry = entry.replace('tel:', '')


            if (entry not in phoneList):
                phoneList.append(entry)

                if save: phoneLog.write(entry + '\n')


def mergeUrl(url, ogPath): # Merge passed domain with passed path (i.e. 'example.org' and '/about-us' to 'http://example.org/about-us')
    path = ogPath
    prefix = getPrefix(url)


    if (url.endswith('/')): url = url[:-1] # Trim last '/' in domain if applicable

    # If current domain is a webfile (i.e. ends with '.html') we need to remove the file before merging the path
    if (isWebFile(url)): url = url[:url.rindex('/')] # Remove everything after and including new last '/'
    
    while (path.startswith('#/') or path.startswith('/#')): # TODO: Keep an eye on this. Potential for actual IDs to get broken, but not sure if it can even happen i.e. /#bottom/something/something-more
        path = path[path.index('#')+1:] # Remove everything up to and including the first '#' from path


    if (path.startswith('/')): # i.e. /example/path should start at the raw domain
        return prefix + getDomain(url) + path

    # Handle '..' backpage href shortcuts
    while (path.startswith('..')):
        path = path[path.index('..')+3:] # Remove everything up to and including the first '..' from path

        try:
            url = prefix + urlStrip(url)[:urlStrip(url).rindex('/')] # Remove everything after new last '/', essentially going back a folder
        except Exception as e:
            log(0, Error(1, ogPath, e, traceback.format_exc())) # Too many back links

    if (not url == prefix): # If domain is more than just a prefix like http://
        return str(prefix + urlStrip(url) + '/' + path)

    return '' # If we erased the domain above, we have a '..' back link with no previous folder to go back to, so we return nothing as it is worthless

        
def parseTag(parentUrl, tag):
    result = ''

    if (isHtmlParse(parentUrl)): # Is a crawlable web file, FTP or otherwise
        for attribute in attributes:
            result = tag.get(attribute)

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
urlInputList = input('\nPlease enter the target URL(s), separated by spaces:\n').split(' ')
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

logPath = LogPath()

# Open log files if applicable
if (save):
    global urlLog
    urlLog = open(logPath.url, 'w+')
    if (scrape):
        global emailLog
        emailLog = open(logPath.email, 'w+')
        global phoneLog
        phoneLog = open(logPath.phone, 'w+')
        
# Begin crawling/scraping
for link in urlInputList: # Crawl for each URL the user inputs
    ogUrl = link
    ogUrlDomain = getDomain(ogUrl)

    print('\n\n\nCrawling ' + link + '\n')
    crawl(totalDepth, link)

if (displayLevel > 0):
    print("\n\nErrors: " + str(errorCount))

    if (scrape):
        print('\n\n\nEmails:\n')

        for email in emailList:
            print(email)

        print('\n\n\nPhone Numbers:\n')

        for phone in phoneList:
            print(phone)