# Version 1.3.2
from bs4 import BeautifulSoup
from datetime import datetime
import traceback
import urllib.request
import uuid

# Config var squad
defaultLogPath = 'logs/' # Determines where logs are stored. Make sure to put a '/' at the end
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
# lastCrawledUrlAtDepth = {} # Depth is key, link/url is value
crawledUrlDict = {} # Checklink is key, URL class is value
emailList = []
phoneList = []
errorCount = 0
jobId = str(uuid.uuid4())
timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
debugLogPath = defaultLogPath + '1-debug/' + 'debug_' + timestamp + '.txt'
urlLogPath = defaultLogPath + '2-url/' + 'url_' + timestamp + '.txt'
emailLogPath = defaultLogPath + '3-email/' + 'email_' + timestamp + '.txt'
phoneLogPath = defaultLogPath + '4-phone/' + 'phone_' + timestamp + '.txt'
# fileLogPath = defaultLogPath + '5-file/' + 'file_' + timestamp + '/'

# TODO: Keep log() as one function, but make all log entries their own classes, with toPrint() methods that structure the entire entry (or whatev I wanna call it)
# TODO: Add job info (i.e. total job time) at end output



class DebugError:
    def __init__(self, errorCode, errorUrl, errorExceptionType, errorException):
        errorMessage = ['Unable to crawl', 'Too many back links', 'URL not in dictionary']
        global errorCount
        errorCount += 1
        self.count = errorCount
        self.code = errorCode
        self.message = errorMessage[self.code]
        self.url = errorUrl
        self.exceptionType = errorExceptionType
        self.exception = errorException


class Email:
    def __init__(self, email):
        self.email = email


class Phone:
    def __init__(self, phone):
        self.phone = self.phone


class URL:
    def __init__(self, url, depth):
        self.depth = depth # Current, not total, depth level (starts at total depth and counts down to 1)
        self.url = url

        # Blank squad. Will be set later
        self.soup = None
        self.parsedList = []

        

def crawl(currentUrl, currentDepth):
    currentUrl = getRebuiltLink(currentUrl)

    if (currentDepth > 0 and not hasCrawled(currentUrl)):
        currentCrawlJob = URL(currentUrl, currentDepth)
        currentCrawlJob.soup = getSoup(currentCrawlJob.url)
        crawledUrlDict[getCheckLink(currentCrawlJob.url)] = currentCrawlJob

        for tag in getTagList(currentCrawlJob.url, currentCrawlJob.soup):
            parsedUrl = parseTag(currentCrawlJob.url, tag)

            if (parsedUrl in ignoreList): continue # Barrier to prevent processing None, etc.

            # Merge path with domain if the URL is missing domain
            if (not hasPrefix(parsedUrl) and not isQualifiedEmail(parsedUrl) and not isQualifiedPhone(parsedUrl)):
                parsedUrl = mergeUrl(currentCrawlJob.url, parsedUrl)

            if (parsedUrl not in currentCrawlJob.parsedList):
                currentCrawlJob.parsedList.append(parsedUrl)

            else:
                continue
            
            log(currentDepth, parsedUrl)

            if (isQualifiedLink(parsedUrl)):
                # Crawl found URL if currentDepth allows it, and URL is on entered domain
                if (currentDepth > 1 and urlStrip(parsedUrl).startswith(ogUrlDomain) and urlStrip(parsedUrl) != urlStrip(ogUrl)):
                    crawl(parsedUrl, currentDepth - 1)
        
        # lastCrawledUrlAtDepth[currentDepth] = currentUrl

    elif (currentDepth > 0 and isQualifiedRelog(currentUrl, currentDepth)): # If URL has already been crawled, use the previously stored URL's if redundant logging is enabled or URL has higher depth.
        parsedList = crawledUrlDict[getCheckLink(currentUrl)].parsedList

        if (currentDepth > crawledUrlDict[getCheckLink(currentUrl)].depth): # if currentDepth is greater than when we last crawled this URL, update the depth so we don't recrawl (after this recrawl) at anything equal to or less
            crawledUrlDict[getCheckLink(currentUrl)].depth = currentDepth
        
        for item in parsedList:

            if (isQualifiedLink(item)):
                log(currentDepth, item)

                # Crawl found URL if currentDepth allows it, and URL is on entered domain
                if (currentDepth > 1 and urlStrip(item).startswith(ogUrlDomain) and urlStrip(item) != urlStrip(ogUrl)):
                    crawl(item, currentDepth - 1)


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
    
    return urlStrip(url) # Used if getPrefix() returns '', meaning it's a phone or email


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


def getRebuiltLink(url): # Ensure that link is able to be crawled (i.e. replace '//' with 'http://'), while preserving the existing prefix if it has one
    return getPrefix(url) + urlStrip(url)


def getSoup(url):
    try: # Read and store code for parsing
        code = urllib.request.urlopen(url).read()
    except Exception as e:
        log(0, DebugError(0, url, e, traceback.format_exc())) # Unable to crawl
        code = ''
    
    return BeautifulSoup(code, features='lxml')


def getTagList(url, soup): # Return a list of links
    if (isHtmlParse(url)): # If it is not an FTP URL, or it is but it's a webpage (i.e. .html file), bs can parse for the tags
        return soup.findAll(markupTags)
    
    # If it is an FTP URL, and not a webpage (i.e. not a .html file), return resulting list of tags from ftpParse()
    return ftpParse(soup)


def hasCrawled(url):
    return getCheckLink(url) in crawledUrlDict


def hasPrefix(url):
    return '://' in url or url.startswith('//')


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


def isQualifiedInput(depth, scrape, save, relog, displayLevel):
    binaryInputChecklist = [scrape, save, relog]
    isBinaryInput = True
    isDisplayLevel = True

    for u in binaryInputChecklist:
        if (not u.lower().startswith('y') and not u.lower().startswith('n')):
            isBinaryInput = False

    if (not isinstance(displayLevel, int) or (displayLevel < 0 or displayLevel > 2)):
        isDisplayLevel = False

    return isinstance(depth, int) and isBinaryInput and isDisplayLevel


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


def isQualifiedRelog(url, currentDepth): # If depth is greater than when previously crawled, there is more to be discovered, hence the recrawl. Otherwise check relog setting
    if (getCheckLink(url) not in crawledUrlDict):
        log(0, DebugError(2, url, None, None)) # Tried to recrawl non-existant URL

        return False

    elif (relog or currentDepth > crawledUrlDict[getCheckLink(url)].depth):
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

    if (type(entry) is DebugError):
        errorMessage = '#' + str(entry.count) + ': ERROR_' + str(entry.code) + ' ' + entry.message + ' | ' + entry.url

        if (displayLevel > 0): print(errorMessage)

        debugLog.write(errorMessage)

        if (entry.exceptionType is not None and entry.exception is not None):
            debugLog.write('\n\n' + str(entry.exceptionType) + '\n\n' + entry.exception + '\n\n\n')
        else:
            debugLog.write('\n\n\n')

    elif (type(entry) is str):
        isRootUrl = (totalDepth == depth) and (urlStrip(entry) != urlStrip(ogUrl))
        entry = getRebuiltLink(entry)

        # Handle formatting
        indent = '     ' * (totalDepth - depth)
        
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
    
    while (path.startswith('#/') or path.startswith('/#/')):
        path = path[path.index('#')+1:] # Remove everything up to and including the first '#' from path


    if (path.startswith('/')): # i.e. /example/path should start at the raw domain
        return prefix + getDomain(url) + path

    # Handle '..' backpage href shortcuts
    while (path.startswith('..')):
        path = path[path.index('..')+3:] # Remove everything up to and including the first '..' from path

        try:
            url = prefix + urlStrip(url)[:urlStrip(url).rindex('/')] # Remove everything after new last '/', essentially going back a folder
        except Exception as e:
            log(0, DebugError(1, ogPath, e, traceback.format_exc())) # Too many back links

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

    # Is FTP and not a web file
    else:
        result = tag

    return result


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

while True:
    try:
        totalDepth = int(input('\nPlease enter how many levels deep the crawler should go:\n'))
    except Exception as e:
        totalDepth = None

    scrape = input('''
Do you want to scrape for emails and phone numbers?
y: yes
n: no
''')

    save = input('''
Would you like to save all data to files in the /logs folder?
y: yes
n: no
''')

    relog =  input('''
Would you like to log redundant URL's?
y: yes   (Preserves original tree structure)
n: no    (Reduces overall crawling duration)
''')

    displayLevel = int(input('''
Please select a logging display option:
0: Quiet
1: Standard
2: Verbose
'''))

    if (isQualifiedInput(totalDepth, scrape, save, relog, displayLevel)):
        break
    else:
        print("\n***\nINVALID INPUT\n***\n")

scrape = scrape.lower().startswith('y')
save = save.lower().startswith('y')
relog = relog.lower().startswith('y')

# Open log files if applicable
debugLog = open(debugLogPath, 'w+')
debugLog.write('JobID: ' + jobId + '\n\n')

if (save):
    urlLog = open(urlLogPath, 'w+')
    urlLog.write('JobID: ' + jobId + '\n\n')

    if (scrape):
        emailLog = open(emailLogPath, 'w+')
        emailLog.write('JobID: ' + jobId + '\n\n')
        phoneLog = open(phoneLogPath, 'w+')
        phoneLog.write('JobID: ' + jobId + '\n\n')
        
# Begin crawling/scraping
for link in urlInputList: # Crawl for each URL the user inputs
    ogUrl = link
    ogUrlDomain = getDomain(ogUrl)

    print('\n\n\nCrawling ' + link + '\n')

    crawl(link, totalDepth)

    if (save):
        urlLog.write('END CRAWL: ' + link + '\n\n')

if (displayLevel > 0):
    if (scrape):
        print('\n\nEmails:')

        for email in emailList:
            print(email)

        print('\n\nPhone Numbers:')

        for phone in phoneList:
            print(phone)
    
    # Add job info here, i.e. total job time in seconds

print('\n\n\nErrorCount: ' + str(errorCount))
print('Timestamp: ' + timestamp)
print('JobID: ' + jobId)