### Creeper: A Cross-Platform Web Crawler and Scraper

from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import traceback
import urllib.request
import uuid

## Config Lists
attributes = ['href', 'src'] # Determines attributes checked from tags to retrieve URLs
defaultLogPath = 'logs/' # Determines where logs are stored. Make sure to put a '/' at the end
disqualifyBeginnings = ['mailto:', 'tel:'] # If a URL starts with any of these, do not consider a qualified URL for crawling
disqualifyEndings = ['/LICENSE'] # If a URL ends with any of these, do not consider a qualified URL for crawling. Do NOT put '/' at the end
fileEndings = ['.html', '.htm', '.php', '.asp', '.cfm'] # Determines what URLs/files will always be crawled, even if ftp(s)://
ignoreList = [None, '#'] # If a URL, etc. is equal to any of these, it will be skipped
markupTags = ['a', 'link', 'script', 'iframe', 'img'] # Determines tags parsed from webpage source code

## Logging
tab = '    '
jobId = str(uuid.uuid4())
timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
debugLogPath = defaultLogPath + '1-debug/' + 'debug_' + timestamp + '.txt'
urlLogPath = defaultLogPath + '2-url/' + 'url_' + timestamp + '.txt'
emailLogPath = defaultLogPath + '3-email/' + 'email_' + timestamp + '.txt'
phoneLogPath = defaultLogPath + '4-phone/' + 'phone_' + timestamp + '.txt'
# fileLogPath = defaultLogPath + '5-file/' + 'file_' + timestamp + '/'

## Error Codes
codeUnableToCrawl = 0
codeTooManyBackLinks = 1
codeUrlNotInDict = 2
errorMessage = [
    'Unable to crawl',
    'Too many back links',
    'URL not in dictionary'
]

## Storage Lists/Dicts
# lastCrawledUrlAtDepth = {} # Depth is key, link/url is value
urlDict = {} # Checklink is key, URL class is value
emailList = []
phoneList = []
# fileDict = {} # Checklink is key, File class is value

## Blanks
errorCount = 0
debugCount = 0
jobStats = ''
ogUrl = ''
ogUrlDomain = ''
startTime = None
totalDepth = 0

# TODO: Once done with writeLog, remove crawl() completely. We should iterate through the tree of links rather than use recursion.
#       Otherwise, a max recursion can be hit, and time complexity increases exponentially rather than linearly.



class DebugError:
    def __init__(self, code, message, url, exceptionType, exception):
        global errorCount
        errorCount += 1
        global debugCount
        debugCount += 1
        
        self.message = message
        self.url = url
        self.code = code
        self.exceptionType = exceptionType
        self.exception = exception

    def getLogOutput(self):
        output = '#' + str(debugCount) + ' ERROR_' + str(self.code) + ': ' + self.message + ' | ' + self.url

        if (self.exceptionType != None):
            output += '\n\n' + str(self.exceptionType)

        if (self.exception != None):
            output += '\n\n' + str(self.exception)
        
        output += '\n\n\n'

        return output

    def getPrintOutput(self):
        output = 'ERROR_' + str(self.code) + ': ' + self.message + ' | ' + self.url

        return output


class DebugInfo:
    def __init__(self, url, header, subheader, body):
        global debugCount
        debugCount += 1

        self.url = url
        self.header = header
        self.subheader = subheader
        self.body = body

    def getLogOutput(self):
        output = '#' + str(debugCount) + ' INFO: ' + self.header + ' | ' + self.url

        if (self.subheader != None):
            output += '\n\n' + self.subheader

        if (self.body != None):
            output += '\n\n' + self.body

        output += '\n\n\n'

        return output

    def getPrintOutput(self):
        output = 'INFO: ' + self.header + ' | ' + self.url

        return output


class Email:
    def __init__(self, email):
        self.email = getStrippedEmail(email)

        # Blank squad
        self.logEntry = ''

    def getLogOutput(self):
        return self.email

    def getPrintOutput(self):
        if (self.logEntry != ''):
            return self.email + ' | ' + self.logEntry
        
        return self.email


class Phone:
    def __init__(self, phone):
        self.phone = getStrippedPhone(phone)

        # Blank squad
        self.logEntry = ''

    def getLogOutput(self):
        return self.phone

    def getPrintOutput(self):        
        if (self.logEntry != ''):
            return self.phone + ' | ' + self.logEntry
        
        return self.phone


class URL:
    def __init__(self, url, depth):
        self.url = url
        self.depth = depth # Current, not total, depth level (starts at total depth and counts down to 1)
        self.indent = tab * (totalDepth - self.depth)
        self.logUrl = getRebuiltLink(self.url).replace(' ', '')

        # Blank squad
        self.logEntry = ''
        self.soup = None
        self.parsedList = []

    def getLogOutput(self):
        return self.indent + self.logUrl

    def getPrintOutput(self):        
        if (self.logEntry != ''):
            return self.indent + self.logUrl + ' | ' + self.logEntry

        return self.indent + self.logUrl

    def setSoup(self):
        if (self.soup == None):
            code = ''
            
            try: # Read and store code for parsing
                code = urllib.request.urlopen(self.url).read()
            except Exception as exception:
                writeLog(DebugError(codeUnableToCrawl, errorMessage[codeUnableToCrawl], self.url, exception, traceback.format_exc()))

            self.soup = BeautifulSoup(code, features='lxml')

        

def crawl(currentUrl, currentDepth):
    currentUrl = getRebuiltLink(currentUrl)
    hasCrawled = getCheckLink(currentUrl) in urlDict

    if (currentDepth > 0 and not hasCrawled):
        currentCrawlJob = URL(currentUrl, currentDepth)
        currentCrawlJob.setSoup()
        urlDict[getCheckLink(currentCrawlJob.url)] = currentCrawlJob

        if (isBetaUrl(currentCrawlJob.url, currentCrawlJob.depth) and isQualifiedCrawlUrl(currentCrawlJob.url)):
            currentCrawlJob.logEntry = 'Crawling...'

        writeLog(currentCrawlJob)

        for tag in getTagList(currentCrawlJob.url, currentCrawlJob.soup):
            parsedUrl = getParsedTag(currentCrawlJob.url, tag)

            if (parsedUrl in ignoreList): continue # Barrier to prevent processing None, etc.

            # Merge path with domain if the URL is missing domain
            if (not hasPrefix(parsedUrl) and not isQualifiedEmail(parsedUrl) and not isQualifiedPhone(parsedUrl)):
                parsedUrl = getMergedUrl(currentCrawlJob.url, parsedUrl)

            if (parsedUrl not in currentCrawlJob.parsedList):
                currentCrawlJob.parsedList.append(parsedUrl)

            else:
                continue

            if (currentDepth > 1 and isQualifiedCrawlUrl(parsedUrl) and getStrippedUrl(parsedUrl).startswith(ogUrlDomain) and getStrippedUrl(parsedUrl) != getStrippedUrl(ogUrl)):
                # Crawl found URL if currentDepth allows it, and URL is on entered domain
                crawl(parsedUrl, currentDepth - 1)
            else:
                if (not isQualifiedEmail(parsedUrl) and not isQualifiedPhone(parsedUrl)):
                    writeLog(URL(parsedUrl, currentDepth - 1))
                    
                elif (isQualifiedEmail(parsedUrl)):
                    writeLog(Email(parsedUrl))

                elif (isQualifiedPhone(parsedUrl)):
                    writeLog(Phone(parsedUrl))
        
        # lastCrawledUrlAtDepth[currentDepth] = currentUrl

    elif (currentDepth > 0): # If URL has already been crawled, use the previously stored URL's if redundant logging is enabled or URL has higher depth.
        currentCheckLink = getCheckLink(currentUrl)
        isRelog = isQualifiedRelog(currentUrl, currentDepth)

        currentRelogJob = urlDict[currentCheckLink]
        currentRelogJob.depth = currentDepth
        currentRelogJob.logEntry = "Already crawled"

        writeLog(currentRelogJob)
        
        if (isRelog):
            if (currentDepth > urlDict[currentCheckLink].depth): # if currentDepth is greater than when we last crawled this URL, update the depth so we don't recrawl (after this recrawl) at anything equal to or less
                urlDict[currentCheckLink].depth = currentDepth

            for item in currentRelogJob.parsedList:

                if (currentDepth > 1 and isQualifiedCrawlUrl(item) and getStrippedUrl(item).startswith(ogUrlDomain) and getStrippedUrl(item) != getStrippedUrl(ogUrl)):
                    # Crawl found URL if currentDepth allows it, and URL is on entered domain
                    crawl(item, currentDepth - 1)
                else:
                    if (not isQualifiedEmail(item) and not isQualifiedPhone(item)):
                        writeLog(URL(item, currentDepth - 1))

                    elif (isQualifiedEmail(item)):
                        writeLog(Email(item))

                    elif (isQualifiedPhone(item)):
                        writeLog(Phone(item))


def getCheckLink(url): # Return a uniform link so that links don't get added twice (i.e. the 'http://' and 'https://' versions)
    if (getPrefix(url).startswith('http')):
        return 'http://' + getStrippedUrl(url)

    elif (getPrefix(url).startswith('ftp')):
        return 'ftp://' + getStrippedUrl(url)
    
    return getStrippedUrl(url) # Used if getPrefix() returns '', meaning it's a phone or email


def getDomain(url): # Return domain only of passed URL (i.e. 'example.org' if passed 'http://example.org/about-us')
    url = getStrippedUrl(url) + '/'


    # Return from start of string to first '/'
    return url[:url.find('/')]


def getFtpParse(soup): # Get contents of FTP soup and return all file paths as a list
    lines = str(soup).splitlines()
    paths = []

    for singleLine in lines:
        lineItems = [x for x in singleLine.split(' ') if x != ''] # Extract all items from that line, separating by whitespace and excluding empty items i.e. ''

        del lineItems[0:8] # Index 8 and further are all parts of the file path. Prior to that are dates, owners, and other unrelated items

        paths.append('%20'.join(lineItems)) # If there are multiple lineItems at this point, the path has at least one space in it and needs '%20' in the URL to represent each
            
    return paths


def getMergedUrl(url, path): # Merge passed domain with passed path (i.e. 'example.org' and '/about-us' to 'http://example.org/about-us')
    ogPath = path
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
            url = prefix + getStrippedUrl(url)[:getStrippedUrl(url).rindex('/')] # Remove everything after new last '/', essentially going back a folder
        except Exception as exception:
            writeLog(DebugError(codeTooManyBackLinks, errorMessage[codeTooManyBackLinks], ogPath, exception, traceback.format_exc()))

    if (not url == prefix): # If domain is more than just a prefix like http://
        return str(prefix + getStrippedUrl(url) + '/' + path)

    return '' # If we erased the domain above, we have a '..' back link with no previous folder to go back to, so we return nothing as it is worthless


def getParsedTag(parentUrl, tag):
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


def getPrefix(url): # Return prefix only of passed URL (i.e. http://, ftp://, etc.)
    if (isQualifiedEmail(url) or isQualifiedPhone(url)):
        return ''

    if ('//' in url and not url.startswith('//')):
        index = url.find('//')
        return url[:index+2]

    writeLog(DebugInfo(url, 'Prefix unknown', 'Passed URL does not contain known prefix', 'getPrefix()\nReturning \'http://\''))
    return 'http://' # Default to this prefix if none is included


def getRebuiltLink(url): # Ensure that link is able to be crawled (i.e. replace '//' with 'http://'), while preserving the existing prefix if it has one
    return getPrefix(url) + getStrippedUrl(url)


def getStrippedEmail(email): # Return raw email i.e. 'email@example.com' instead of 'mailto:email@example.com'
    strToRemove = ['mailto:', ' ']

    for u in strToRemove:
        email = email.replace(u, '')

    return email


def getStrippedPhone(phone): # Return raw phone # i.e. '1234567890' instead of '(123) 456-7890' or 'tel:1234567890'
    strToRemove = ['tel:', '(', ')', '-', ' ']
    
    for u in strToRemove:
        phone = phone.replace(u, '')

    return phone


def getStrippedUrl(url): # Returns the bare URL after removing http, https, www, etc. (i.e. 'example.org' instead of 'http://www.example.org')
    strToRemove = ['http://', 'https://', 'ftp://', 'ftps://', 'www.', ' ']

    for u in strToRemove:
        url = url.replace (u, '')

    if (url.startswith('//')):
        url = url[+2:]

    if (url.endswith('/')):
        url = url[:-1]

    return url


def getTagList(url, soup): # Return a list of links
    if (isHtmlParse(url)): # If it is not an FTP URL, or it is but it's a webpage (i.e. .html file), bs can parse for the tags
        return soup.findAll(markupTags)
    
    # If it is an FTP URL, and not a webpage (i.e. not a .html file), return resulting list of tags from getFtpParse()
    return getFtpParse(soup)


def hasPrefix(url):
    return '://' in url or url.startswith('//')


def isBetaUrl(url, depth): # URLs that are both on the og domain, as well as at the second-highest depth or higher (beginning of the rabbit holes basically)
        return totalDepth <= (depth + 1)


def isFtp(url):
    if ((url.startswith('ftp://') or url.startswith('ftps://'))):
        return True

    return False


def isHtmlParse(url):
    ftp = isFtp(url)
    webFile = isWebFile(url)


    return (not ftp) or (ftp and webFile) # Not FTP, or is FTP with webfile (.html, etc.)


def isQualifiedCrawlUrl(url): # Return boolean on whether the passed item is crawlable or not (i.e. not a mailto: or .mp3 file) TODO: Refactor this?
    if (getStrippedUrl(url).endswith('..')): return False # Back links

    for u in disqualifyEndings:
        if (url.endswith(getStrippedUrl(u))):
            return False

    for u in disqualifyBeginnings:
        if (url.startswith(getStrippedUrl(u))):
            return False

    if (url.endswith('/')): url = url[:-1] # Remove trailing / for accurate extension comparison

    if ('.' in getStrippedUrl(url).replace(ogUrl, '').replace(getDomain(url), '').replace('/.', '')): # After removing the domain, prefix, and any '/.' (i.e. unix hidden folders/files), if there's a '.' left, check like a file extension
        return isWebFile(url)

    return True


def isQualifiedEmail(url): # Return boolean on whether the passed item is a valid email or not
    if (url.startswith('mailto:') and url.replace('mailto:', '') != ''):
        return True

    return False


def isQualifiedInput(depth, scrape, save, relog, logLevel):
    binaryInputChecklist = [scrape, save, relog]
    isBinaryInput = True
    isDisplayLevel = True

    for u in binaryInputChecklist:
        if (not u.lower().startswith('y') and not u.lower().startswith('n')):
            isBinaryInput = False

    if (not isinstance(logLevel, int) or (logLevel < 0 or logLevel > 2)):
        isDisplayLevel = False

    return isinstance(depth, int) and isBinaryInput and isDisplayLevel


def isQualifiedPhone(url): # Return boolean on whether the passed item is a valid phone number or not
    if (url.startswith('tel:') and url.replace('tel:', '') != ''):
        return True

    return False


def isQualifiedRelog(url, currentDepth): # If depth is greater than when previously crawled, there is more to be discovered, hence the recrawl. Otherwise check relog setting
    if (getCheckLink(url) not in urlDict):
        writeLog(DebugError(codeUrlNotInDict, errorMessage[codeUrlNotInDict], url, None, None)) # Tried to recrawl non-existant URL

        return False

    elif (relog or currentDepth > urlDict[getCheckLink(url)].depth):
        return True

    return False


def isWebFile(url): # Return boolean on whether the passed URL ends with one of the extensions in fileEndings or not
    if (url.endswith('/')): url = url[:-1] # Remove last '/' if applicable

    for ending in fileEndings:
        if (url.endswith(ending)): # If it has a webpage file ending like .html, etc.
            return True

    return False


def writeLog(entry):
    if (type(entry) is DebugError or type(entry) is DebugInfo):
        if (logLevel > 0):
            print(entry.getPrintOutput())

        debugLog.write(entry.getLogOutput())

    elif (type(entry) is URL):
        # logLevel
        switch = {
            0: False,
            1: isBetaUrl(entry.url, entry.depth),
            2: True,
        }

        if (switch[logLevel]): # If it's a root URL that it's going to crawl, or full logging is enabled
            print(entry.getPrintOutput())

        if (save):
            urlLog.write(entry.getLogOutput() + '\n')

    elif (type(entry) is Email):
        if (scrape and entry not in emailList):
            emailList.append(entry.getPrintOutput()) # Will print at end regardless of log level

            if (save):
                emailLog.write(entry.getLogOutput() + '\n')

    elif (type(entry) is Phone):
        if (scrape and entry not in phoneList):
            phoneList.append(entry.getPrintOutput()) # Will print at end regardless of log level

            if (save):
                phoneLog.write(entry.getLogOutput() + '\n')



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
y: yes (Default)
n: no
''')

    if (scrape == ''):
        scrape = 'y'

    save = input('''
Would you like to save all data to files in the /logs folder?
y: yes (Default)
n: no
''')

    if (save == ''):
        save = 'y'

    relog =  input('''
Would you like to log redundant URL's? Doing so increases overall crawling duration.
y: yes
n: no (Default)
''')

    if (relog == ''):
        relog = 'n'

    logLevel = input('''
Please select a logging display option:
0: Quiet
1: Standard (Default)
2: Verbose
''')

    if (logLevel == ''):
        logLevel = 1

    logLevel = int(logLevel)

    if (isQualifiedInput(totalDepth, scrape, save, relog, logLevel)):
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
startTime = datetime.now()

for link in urlInputList: # Crawl for each URL the user inputs
    ogUrl = link
    ogUrlDomain = getDomain(ogUrl)

    crawl(link, totalDepth)

    if (save):
        urlLog.write('END CRAWL: ' + link + '\n\n')

if (logLevel > 0):
    if (scrape):
        print('\n\nEmails:')

        for email in emailList:
            print(email)

        print('\n\nPhone Numbers:')

        for phone in phoneList:
            print(phone)

jobStats = ('\n\n\n**Job Stats**\n' +
    'Errors: ' + str(errorCount) + '\n' +
    str(timedelta.total_seconds(datetime.now() - startTime)) + ' seconds\n' +
    'Timestamp: ' + timestamp
)

print(jobStats)
print('JobID: ' + jobId)
debugLog.write(jobStats)