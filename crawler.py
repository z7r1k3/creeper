import datetime
import re
import urllib.request
import requests
from bs4 import BeautifulSoup

# var squad
fileEndings = ['.html','.asp','.php','.htm']
stripText = ['http://', 'https://', 'ftp://', 'ftps://', 'www.', ' ']
crawlList = {}
urlList = {}
emailList = []
phoneList = []
timestamp = ''
urlLogPath = 'logs/url/'
emailLogPath = 'logs/email/'
phoneLogPath = 'logs/phone/'
urlLog = None
emailLog = None
phoneLog = None

 # Just to clarify, totalDepth is the total jumps allowed from the starting URL
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
            if (not (urlStrip(href).startswith(getDomain(ogUrl)) or '://' in href) and not isQualifiedEmail(href) and not isQualifiedPhone(href)):
                href = mergeUrl(passedUrl, href)
            
            # Print domain
            display(href, logCode, totalDepth, depth, ogUrl)

            # Only if link is crawlable
            if (isQualifiedLink(href)):
                # Crawl found link if depth allows it, and link is on entered domain
                if (depth > 1 and urlStrip(href).startswith(getDomain(ogUrl)) and urlStrip(href) != urlStrip(ogUrl)):
                    crawl(totalDepth, depth - 1, ogUrl, href, logCode)

            elif (scrape and isQualifiedEmail(href)):
                href = href.replace('mailto:', '')

                if (href not in emailList):
                    emailList.append(href)
                    emailLog.write(href + '\n')
            
            elif (scrape and isQualifiedPhone(href)):
                href = href.replace('tel:', '')

                if (href not in phoneList):
                    phoneList.append(href)
                    phoneLog.write(href + '\n')
        
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
    return (check in crawlList and check in urlList)


def urlStrip(url):
    bareUrl = url

    # Remove http, https, and www to accurately compare URL's
    for u in stripText:
        bareUrl = bareUrl.replace (u, '')

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
        0: False,
        1: isRootUrl,
        2: True,
    }

    if (not isQualifiedEmail(text) and not isQualifiedPhone(text)):
        if (switch[logCode] and depth > 1):
            print()

        if (switch[logCode] and isRootUrl and getDomain(ogUrl) in text and isQualifiedLink(text)):
            print(indent + text.replace(' ', '') + " | Crawling...")
            if (save): urlLog.write(indent + text.replace(' ', '') + '\n')
        elif (switch[logCode]):
            print(indent + text.replace(' ', ''))
            if (save): urlLog.write(indent + text.replace(' ', '') + '\n')


def getDomain(url):
    url = urlStrip(url)
    index = url.find('/')
    return url[:index]

def getPrefix(url):
    if ('//' in url):
        index = url.find('//')
        return url[:index+2]
    return 'http://'


def mergeUrl(domain, path):
    # Handle '..' backpage href shortcuts
    while (path.startswith('/..') or path.startswith('..')): # Starts with a back link
        path = path[path.index('.')+2:] # Remove everything up to and including the first '..'

        if (domain.endswith('/')):
            domain = getPrefix(domain) + urlStrip(domain)[:urlStrip(domain[:-1]).rindex('/')] # Trim last '/' and then remove everything after new last '/', essentially going back a folder
        else:
            domain = getPrefix(domain) + urlStrip(domain)[:urlStrip(domain).rindex('/')] # Same as above, without trimming a '/' at the end
        # urlStrip ensures the '/' in the prefix (i.e. 'http://') doesn't get counted. In the situation where it would, stripping that out should cause the entire URL to return as nothing ('')
        # This is a good thing, as you can't really go back a folder from the primary domain (i.e. back from 'example.org' instead of 'example.org/something')

    if (path.startswith('/')):
        return getPrefix(domain) + urlStrip(domain) + path[+1:]

    if (not domain == getPrefix(domain)):
        return str(getPrefix(domain) + urlStrip(domain) + path)
    return '' # If we erased the domain above, we have a '..' back link with no previous folder to go back to, so we return nothing as it is worthless


def ftpParse(soup):
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

    offset = 8 # This is used to ignore most of the crap we parsed above and just get the URL path

    for i in range(0, len(items)): # For each item in items, but give me an index number to work with (i)
        string = ''
        
        paths.append(i)
        
        for j in range(offset, len(items[i])): # Parsing paths from items, and converting them into URL's
            string += items[i][j]
            if (offset < len(items[i])-1 and j < len(items[i])-1):
                string += '%20' # %20 is a space in a URL
        
        paths[i] = string
            
    return paths


def getLink(soup, isFtp):
    if (not isFtp): # If it is not an FTP link, bs can parse for the <a> tags
        return soup.findAll('a')
    
    return soup


# Make sure it isn't a mp3, json, png, jpg... Make sure it is a html, asp, php, ftp file without ending
def isQualifiedLink(href): # Not mailto etc.
    if (':' in href and not '://' in href): return False # If it has a : but no ://
    if (href == '#'): return False
    if (urlStrip(href).endswith('../')): return False # Back links
    if (href.endswith('/LICENSE') or href.endswith('/LICENSE/')): return False

    if (href.endswith('/')): href = href[:-1] # Remove trailing / for accurate extension comparison

    if ('.' in urlStrip(href).replace(getDomain(href), '')):
        for ending in fileEndings:
            if (href.endswith(ending) and not (href.startswith('ftp://') or href.startswith('ftps://'))): # If it has a webpage file ending, and it's not on an ftp server
                return True
        return False
    return True


def isQualifiedEmail(href):
    if (href.startswith('mailto:') and href.replace('mailto:', '') != ''):
        return True
    return False

def isQualifiedPhone(href):
    if (href.startswith('tel:') and href.replace('tel:', '') != ''):
        return True
    return False
    


# START MAIN CODE

# Get user variables
url = input('\nPlease enter the target URL(s), separated by spaces:\n').split(' ')
depth = int(input('\nPlease enter how many levels deep the crawler should go:\n'))
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

log = int(input('''
Please select a logging display option:
0: Quiet
1: Standard
2: Verbose
'''))

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
    print('\n\n\nCrawling ' + link + '...\n')
    crawl(depth, depth, link, link, log)

if (scrape and log > 0):
    print('\n\n\nEmails:\n')

    for email in emailList:
        print(email)

    print('\n\n\nPhone Numbers:\n')

    for phone in phoneList:
        print(phone)