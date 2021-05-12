# Creeper
# A Cross-Platform Web Crawler and Scraper
# Built in Python 3.9

from bs4 import BeautifulSoup
from copy import deepcopy
from datetime import datetime, timedelta
from urllib import request
import traceback
import uuid


# Config Lists
default_log_path = 'logs/'  # Make sure to put a '/' at the end

disqualify_beginnings = ['mailto:',
                         'tel:'
                         ]  # Do not consider URL for crawling
disqualify_endings = ['/LICENSE']  # Do NOT put '/' at the end
disqualify_url = [None,
                  '#']

qualify_attributes = ['href',
                      'src'
                      ]  # Determines attributes checked from tags
qualify_endings = ['.html',
                   '.htm',
                   '.php',
                   '.asp',
                   '.cfm'
                   ]  # Both http and ftp
qualify_tags = ['a',
                'atom:link',
                'iframe',
                'img',
                'link',
                'script'
                ]  # Determines tags parsed


# Logging
debug_log_divider = '=================================================='
tab = '    '

job_id = str(uuid.uuid4())
timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')

debug_log_path = default_log_path + '1-debug/' + 'debug_' + timestamp + '.txt'
url_log_path = default_log_path + '2-url/' + 'url_' + timestamp + '.txt'
email_log_path = default_log_path + '3-email/' + 'email_' + timestamp + '.txt'
phone_log_path = default_log_path + '4-phone/' + 'phone_' + timestamp + '.txt'


# Defaults
is_scrape_mode = True
is_save_mode = True
print_level = 1
redundancy_level = 0
total_depth = 4

timeout = 20


# Error Codes
code_unable_to_crawl = 0
code_too_many_back_links = 1


# Storage Lists/Dicts
url_dict = {}  # Checklink is key, URL class is value
email_list = []
phone_list = []

prefix_cache_dict = {}  # Key = URL, value = prefix
url_log_list = []  # Used for seeing if URL has been logged yet


# Blanks
debug_count = 0
error_count = 0

job_stats = ''
og_url = ''
og_url_domain = ''

email_log = None
url_input_list = None
url_log = None
phone_log = None
start_time = None


class DebugError:
    def __init__(
            self, code, message, url, exception=None, traceback=None):
        global error_count
        error_count += 1
        global debug_count
        debug_count += 1

        self.code = code
        self.message = message
        self.url = url
        self.exception = exception
        self.traceback = traceback

    def get_log_output(self):
        output = ('#' + str(debug_count) +
                  ' ERROR_' + str(self.code) + ': '
                  + self.message + ' | ' + self.url
                  )

        if self.exception is not None:
            output += '\n\n\n' + str(self.exception)

        if self.traceback is not None:
            output += '\n\n\n' + str(self.traceback)

        output += '\n\n\n' + debug_log_divider + '\n\n\n'

        return output

    def get_print_output(self):
        output = ('Entry#' + str(debug_count) +
                  ' | ERROR_' + str(self.code) + ': ' +
                  self.message + ' | ' + self.url
                  )

        return output


class DebugInfo:
    def __init__(self, url, header, subheader=None, body=None):
        global debug_count
        debug_count += 1

        self.url = url
        self.header = header
        self.subheader = subheader
        self.body = body

    def get_log_output(self):
        output = ('#' + str(debug_count) + ' INFO: ' + self.header)

        if self.url is not None:
            output += ' | ' + self.url

        if self.subheader is not None:
            output += '\n\n\n' + self.subheader

        if self.body is not None:
            output += '\n\n\n' + self.body

        output += '\n\n\n' + debug_log_divider + '\n\n\n'

        return output

    def get_print_output(self):
        output = ('Entry#' + str(debug_count) + ' | INFO: ' + self.header)

        if self.url is not None:
            output += ' | ' + self.url

        return output


class Email:
    def __init__(self, email, log_entry=None):
        self.email = get_stripped_email(email)
        self.log_entry = log_entry

    def get_log_output(self):
        return self.email

    def get_print_output(self):
        if self.log_entry is not None:
            return self.email + ' | ' + self.log_entry

        return self.email


class Phone:
    def __init__(self, phone, log_entry=None):
        self.phone = get_stripped_phone(phone)
        self.log_entry = log_entry

    def get_log_output(self):
        return self.phone

    def get_print_output(self):
        if self.log_entry is not None:
            return self.phone + ' | ' + self.log_entry

        return self.phone


class URL:
    def __init__(self, url, depth, log_entry=None, source=None):
        self.url = url
        self.depth = depth  # Current, not total, depth level
        self.log_entry = log_entry
        self.source = str(source)  # Never let this be a soup, always str
        self.log_url = get_rebuilt_link(url)

        # Blank squad
        self.parsed_list = []

    def get_log_output(self):
        if redundancy_level != 0:
            indent = tab * (total_depth - self.depth)
        else:
            indent = ''

        return indent + self.log_url

    def get_print_output(self):
        if redundancy_level != 0:
            indent = tab * (total_depth - self.depth)
        else:
            indent = ''

        if self.log_entry is not None:
            return indent + self.log_url + ' | ' + self.log_entry

        return indent + self.log_url


def crawl(current_url, current_depth):
    current_url = get_rebuilt_link(current_url)
    current_check_link = get_check_link(current_url)
    has_crawled = current_check_link in url_dict

    if current_depth > 0 and not has_crawled:
        current_soup = get_soup(current_url)
        url_class = URL(current_url, current_depth, None, current_soup)
        current_crawl_job, url_dict[current_check_link] = url_class, url_class
        has_qualified_attributes = False
        tag_list = get_tag_list(current_url, current_soup)

        if (is_beta_url(current_url, current_depth)
                and is_qualified_crawl_url(current_url)):
            current_crawl_job.log_entry = 'Crawling...'

        write_log(current_crawl_job)

        for tag in tag_list:  # Update parsed lists before crawling them
            parsed_url = get_parsed_attribute(current_url, tag)

            if parsed_url is not None:
                has_qualified_attributes = True

            if parsed_url in disqualify_url:
                continue  # Barrier to prevent processing None, etc.

            # Merge path with domain if the URL is missing domain
            if (not has_prefix(parsed_url)
                    and not is_qualified_email(parsed_url)
                    and not is_qualified_phone(parsed_url)):
                parsed_url = get_merged_url(current_url, parsed_url)

            # Add to URL class for preserving tree structure
            if parsed_url not in current_crawl_job.parsed_list:
                current_crawl_job.parsed_list.append(parsed_url)
            else:
                continue

        url_dict[current_check_link].parsed_list = deepcopy(
            current_crawl_job.parsed_list)

        for parsed_url in current_crawl_job.parsed_list:  # Crawl parsed lists
            bare_parsed_url = get_stripped_url(parsed_url)

            if (current_depth > 1
                    and is_qualified_crawl_url(parsed_url)
                    and bare_parsed_url.startswith(og_url_domain)
                    and bare_parsed_url != get_stripped_url(og_url)):
                # Crawl if current_depth allows it, and on og domain
                crawl(parsed_url, current_depth - 1)
            else:
                if (not is_qualified_email(parsed_url)
                        and not is_qualified_phone(parsed_url)):
                    write_log(URL(parsed_url, current_depth - 1))
                elif is_qualified_email(parsed_url):
                    write_log(Email(parsed_url))
                elif is_qualified_phone(parsed_url):
                    write_log(Phone(parsed_url))

        if not has_qualified_attributes:
            debug_header = 'No attributes detected'
            debug_subheader = ('The tags were parsed from the URL, ' +
                               'but no qualified attributes were detected')
            debug_body = 'SOURCE:\n\n' + str(current_crawl_job.source)

            write_log(DebugInfo(current_crawl_job.url,
                                debug_header,
                                debug_subheader,
                                debug_body))
    elif current_depth > 0:  # URL has already been crawled, get the result
        is_higher_depth = (
            current_depth > url_dict[get_check_link(current_url)].depth)

        # If current_depth is greater than when we last crawled this URL,
        # update the depth so we don't recrawl at anything equal to or less
        if (is_higher_depth):
            url_dict[current_check_link].depth = current_depth

        if is_higher_depth or redundancy_level == 2:
            current_relog_job = deepcopy(url_dict[current_check_link])
            current_relog_job.depth = current_depth
            current_relog_job.log_entry = 'Already crawled'

            write_log(current_relog_job)

            for item in current_relog_job.parsed_list:
                bare_item_url = get_stripped_url(item)

                if (current_depth > 1
                        and is_qualified_crawl_url(item)
                        and bare_item_url.startswith(og_url_domain)
                        and bare_item_url != get_stripped_url(og_url)):
                    # Crawl if current_depth allows it, and on og domain
                    crawl(item, current_depth - 1)
                else:
                    if (not is_qualified_email(item)
                            and not is_qualified_phone(item)):
                        write_log(URL(item, current_depth - 1))
                    elif is_qualified_email(item):
                        write_log(Email(item))
                    elif is_qualified_phone(item):
                        write_log(Phone(item))


def get_check_link(url):  # Return uniform link so links don't get added twice
    prefix = get_prefix(url)
    url = get_stripped_url(url)

    if prefix.startswith('http'):
        return 'http://' + url

    elif prefix.startswith('ftp'):
        return 'ftp://' + url

    return url  # Used if get_prefix() returns ''


def get_domain(url):  # Return domain only of passed URL
    url = get_stripped_url(url) + '/'

    # Return from start of string to first '/'
    return url[:url.find('/')]


def get_ftp_parse(soup):  # Get contents of FTP soup, return all paths as list
    lines = str(soup).splitlines()
    paths = []

    for single_line in lines:
        # Extract all items from line
        # Separate by whitespace and exclude empty items i.e. ''
        line_items = [x for x in single_line.split(' ') if x != '']

        del line_items[0:8]  # Index 8 and further are parts of the file path

        # If there are multiple line_items at this point,
        # the path has at least one space in it and needs '%20' for each
        paths.append('%20'.join(line_items))

    return paths


def get_merged_url(url, path):  # Merge passed domain with passed path
    og_path = path
    prefix = get_prefix(url)

    if url.endswith('/'):  # Trim last '/' in domain if applicable
        url = url[:-1]

    # If current domain is a webfile (i.e. ends with '.html')
    #  we need to remove the file before merging the path
    if is_web_file(url):  # Remove everything after and including new last '/'
        url = url[:url.rindex('/')]

    while path.startswith('#/') or path.startswith('/#/'):
        # Remove everything up to and including the first '#' from path
        path = path[path.index('#') + 1:]

    if path.startswith('/'):
        # i.e. /example/path should start at the raw domain
        return prefix + get_domain(url) + path

    # Handle '..' backpage href shortcuts
    while path.startswith('..'):
        # Remove everything up to and including the first '..' from path
        path = path[path.index('..')+3:]

        try:
            # Remove everything after new last '/',
            # essentially going back a folder
            url = (prefix +
                   get_stripped_url(url)[:get_stripped_url(url).rindex('/')])
        except Exception as exception:
            write_log(DebugError(code_too_many_back_links,
                                 'Too many back links',
                                 og_path,
                                 exception,
                                 traceback.format_exc()))

    if url != prefix:  # If domain is more than just a prefix like http://
        return str(prefix + get_stripped_url(url) + '/' + path)

    # If we erased the domain above
    # we have a '..' back link with no previous folder
    # so we return nothing as it is worthless
    return ''


def get_parsed_attribute(parent_url, tag):
    attribute = ''

    if is_html_parse(parent_url):  # Is a crawlable web file, FTP or otherwise
        for u in qualify_attributes:
            attribute = tag.get(u)

            if (attribute is not None):
                break
    else:  # Is FTP and not a web file
        attribute = tag

    return attribute


def get_prefix(url):  # Return prefix only of passed URL
    prefix = ''

    if is_qualified_email(url) or is_qualified_phone(url):
        return prefix

    if url in prefix_cache_dict:
        return prefix_cache_dict[url]

    if '//' in url and not url.startswith('//'):
        index = url.find('//') + 2
        prefix = url[:index]
    else:
        prefix = 'http://'  # Default to this prefix if none is included
        debug_header = 'Prefix not detected'
        debug_subheader = (
            'The passed URL was scanned, but no prefix was detected')
        debug_body = 'Location: get_prefix()\nResult: Returning \'http://\''

        write_log(DebugInfo(url, debug_header, debug_subheader, debug_body))

    prefix_cache_dict[url] = prefix

    return prefix


def get_rebuilt_link(url):
    return (get_prefix(url) + get_stripped_url(url)).replace(' ', '')


def get_stripped_email(email):  # Return raw email
    # i.e. 'email@example.com' instead of 'mailto:email@example.com'
    str_to_remove = ['mailto:', ' ']

    for u in str_to_remove:
        email = email.replace(u, '')

    return email


def get_stripped_phone(phone):  # Return raw phone
    # i.e. '1234567890' instead of '(123) 456-7890' or 'tel:1234567890'
    str_to_remove = ['tel:', '(', ')', '-', ' ']

    for u in str_to_remove:
        phone = phone.replace(u, '')

    return phone


def get_soup(url):
    url = get_rebuilt_link(url)
    code = None

    try:  # Read and store code for parsing
        code = request.urlopen(url, timeout=timeout).read()
    except Exception as exception:
        write_log(DebugError(code_unable_to_crawl,
                             'Unable to crawl',
                             url,
                             exception,
                             traceback.format_exc()
                             ))

    if code is None:
        code = ''

    return BeautifulSoup(code, features='lxml')


def get_stripped_url(url):  # Returns the bare URL
    # Remove http, https, www, etc.
    # (i.e. 'example.org' instead of 'http://www.example.org')
    check_end_path = ''
    str_to_remove = ['http://', 'https://', 'ftp://', 'ftps://', 'www.', ' ']

    for u in str_to_remove:
        url = url.replace(u, '')

    if url.startswith('//'):
        url = url[+2:]

    if url.endswith('/'):
        url = url[:-1]

    slash_index = url.rfind('/')

    if (slash_index + 1 < len(url)):
        check_end_path = url[slash_index:]

    if check_end_path.startswith('/#'):
        id_index = url.rfind(check_end_path)
        url = url[:id_index]  # If it's an ID i.e. '/#content'

    return url


def get_tag_list(url, soup):  # Return a list of links
    tag_list = []

    if is_html_parse(url):
        # If it is not an FTP URL,
        # or it is but it's a webpage (i.e. .html file),
        # bs can parse for the tags
        tag_list = soup.findAll(qualify_tags)
    else:
        # If it is an FTP URL, and not a webpage (i.e. not a .html file),
        # return resulting list of tags from get_ftp_parse()
        tag_list = get_ftp_parse(soup)

    if len(tag_list) == 0:
        debug_header = 'No tags detected'
        debug_subheader = 'The URL was parsed, but no tags were detected'
        debug_body = 'SOURCE:\n\n' + str(soup)

        write_log(DebugInfo(url, debug_header, debug_subheader, debug_body))

    return tag_list


def has_prefix(url):
    return '://' in url or url.startswith('//')


def is_beta_url(url, depth):
    # URLs that are both on the og domain,
    # as well as at the second-highest depth or higher
    # (beginning of the rabbit holes basically)
    return total_depth <= (depth + 1)


def is_ftp(url):
    if url.startswith('ftp://') or url.startswith('ftps://'):
        return True

    return False


def is_html_parse(url):
    # Not FTP, or is FTP with webfile (.html, etc.)
    if not is_ftp(url):
        return True

    return is_web_file(url)


def is_qualified_crawl_url(url):
    # Return boolean on whether the passed URL is crawlable or not
    # (i.e. not a mailto: or .mp3 file)
    check_url = get_stripped_url(url)

    if check_url.endswith('..'):  # Back links
        return False

    for u in disqualify_endings:
        if check_url.endswith(get_stripped_url(u)):
            return False

    for u in disqualify_beginnings:
        if url.startswith(get_stripped_url(u)):
            return False

    if url.endswith('/'):  # Remove trailing /
        url = url[:-1]

    check_url = check_url.replace(og_url, '')
    check_url = check_url.replace(get_domain(url), '')
    check_url = check_url.replace('/.', '')

    if '.' in check_url:
        # After removing the domain, prefix, and any '/.'
        # (i.e. unix hidden folders/files),
        # if there's a '.' left check like a file extension
        return is_web_file(url)

    return True


def is_qualified_email(url):
    # Return boolean on whether the passed item is a valid email or not
    if url.startswith('mailto:') and url != 'mailto:':
        return True

    return False


def is_qualified_phone(url):
    # Return boolean on whether the passed item is a valid phone number or not
    if url.startswith('tel:') and url != 'tel:':
        return True

    return False


def is_web_file(url):
    # Return: URL ends with one of the extensions in qualify_endings
    if url.endswith('/'):
        url = url[:-1]  # Remove last '/' if applicable

    for ending in qualify_endings:
        if url.endswith(ending):
            return True

    return False


def write_log(entry):
    if type(entry) is DebugError or type(entry) is DebugInfo:
        if print_level > 1:
            print(entry.get_print_output())

        debug_log.write(entry.get_log_output())
    elif type(entry) is URL:
        is_qualified_log = False
        is_qualified_print = False
        is_unique = False

        if get_check_link(entry.url) not in url_log_list:
            is_unique = True
            url_log_list.append(get_check_link(entry.url))

        if redundancy_level == 0:
            is_qualified_log = is_save_mode and is_unique
            is_qualified_print = print_level > 0 and is_unique
        else:
            is_qualified_log = is_save_mode
            is_qualified_print = print_level > 0

        if is_qualified_print:
            # If it's a root URL that it's going to crawl,
            # or full logging is enabled
            print(entry.get_print_output())

        if is_qualified_log:
            url_log.write(entry.get_log_output() + '\n')
    elif type(entry) is Email:
        if is_scrape_mode and entry.email not in email_list:
            email_list.append(entry.get_print_output())

            if is_save_mode:
                email_log.write(entry.get_log_output() + '\n')

    elif type(entry) is Phone:
        if is_scrape_mode and (entry.phone not in phone_list):
            phone_list.append(entry.get_print_output())

            if is_save_mode:
                phone_log.write(entry.get_log_output() + '\n')


# START MAIN CODE

# Get user variables
while True:
    url_input_list = input(
        '\nPlease enter the target URL(s), separated by spaces:\n').split(' ')

    if url_input_list == ['']:
        print("\n***\nINVALID INPUT\n***\n")
        continue
    break

while True:
    total_depth_input = input(
        '\nPlease enter how many levels deep to crawl (default = 4):\n')

    if total_depth_input == '':
        break
    else:
        try:
            if int(total_depth_input) > 0:
                total_depth = int(total_depth_input)
                break
            else:
                print("\n***\nINVALID INPUT\n***\n")
                continue
        except Exception:
            print("\n***\nINVALID INPUT\n***\n")
            continue

while True:
    scrape_mode_input = input(
        '\n' +
        'Do you want to scrape for emails and phone numbers?\n' +
        'y: yes (Default)\n' +
        'n: no\n')

    if scrape_mode_input == '':
        break
    elif (scrape_mode_input.lower().startswith('y') or
            scrape_mode_input.lower().startswith('n')):
        is_scrape_mode = scrape_mode_input.lower().startswith('y')
        break
    else:
        print("\n***\nINVALID INPUT\n***\n")
        continue

while True:
    save_mode_input = input(
        '\n' +
        'Would you like to save all data to files in the /logs folder?\n' +
        'y: yes (Default)\n' +
        'n: no\n')

    if save_mode_input == '':
        break
    elif (save_mode_input.lower().startswith('y') or
            save_mode_input.lower().startswith('n')):
        is_save_mode = save_mode_input.lower().startswith('y')
        break
    else:
        print("\n***\nINVALID INPUT\n***\n")
        continue

while True:
    redundancy_level_input = input(
        '\n' +
        'Please select a level of redundancy:\n' +
        ' Unique will log each URL in a list once and only once.\n' +
        ' Standard will log a tree while skipping already crawled URLs.\n' +
        ' Redundant will log the full tree including already crawled URLs.\n' +
        '0: Unique (Default)\n' +
        '1: Standard\n' +
        '2: Redundant\n')

    if redundancy_level_input == '':
        break
    else:
        try:
            if (int(redundancy_level_input) >= 0 and
                    int(redundancy_level_input) <= 2):
                redundancy_level = int(redundancy_level_input)
                break
            else:
                print("\n***\nINVALID INPUT\n***\n")
                continue
        except Exception:
            print("\n***\nINVALID INPUT\n***\n")
            continue

while True:
    print_level_input = input(
        '\n' +
        'Please select an output display option:\n' +
        '0: Quiet\n' +
        '1: Standard (Default)\n' +
        '2: Verbose\n')

    if print_level_input == '':
        break
    else:
        try:
            if (int(print_level_input) >= 0 and
                    int(print_level_input) <= 2):
                print_level = int(print_level_input)
                break
            else:
                print("\n***\nINVALID INPUT\n***\n")
                continue
        except Exception:
            print("\n***\nINVALID INPUT\n***\n")
            continue


# Open log files if applicable
debug_log = open(debug_log_path, 'w+')
debug_log.write('JobID: ' + job_id + '\n\n')

if is_save_mode:
    url_log = open(url_log_path, 'w+')
    url_log.write('JobID: ' + job_id + '\n\n')

    if is_scrape_mode:
        email_log = open(email_log_path, 'w+')
        email_log.write('JobID: ' + job_id + '\n\n')
        phone_log = open(phone_log_path, 'w+')
        phone_log.write('JobID: ' + job_id + '\n\n')

# Begin crawling/scraping
start_time = datetime.now()
debug_header = 'Starting crawl job'
debug_subheader = 'START: ' + str(datetime.utcnow()) + ' UTC'
debug_body = ('CONFIG:' +
              '\ntotal_depth = ' + str(total_depth) +
              '\nscrape = ' + str(is_scrape_mode) +
              '\nsave = ' + str(is_save_mode) +
              '\nredundancy_level = ' + str(redundancy_level) +
              '\nprint_level = ' + str(print_level) +
              '\nurl_input_list =' +
              '\n' + tab + ('\n' + tab).join(map(str, url_input_list)))

write_log(DebugInfo(None, debug_header, debug_subheader, debug_body))

for link in url_input_list:  # Crawl for each URL the user inputs
    og_url = link
    og_url_domain = get_domain(og_url)

    crawl(link, total_depth)

    if is_save_mode:
        url_log.write('END CRAWL: ' + link + '\n\n')

if print_level > 0:
    if is_scrape_mode:
        print('\n\nEmails:')
        print('\n'.join(map(str, email_list)))

        print('\n\nPhone Numbers:')
        print('\n'.join(map(str, phone_list)))

job_stats = (
    '**Job Stats**\n' +
    'Errors: ' + str(error_count) + '\n' +
    str(timedelta.total_seconds(datetime.now() - start_time)) + ' seconds\n' +
    'Timestamp: ' + timestamp
    )

print('\n\n\n' + job_stats)
print('JobID: ' + job_id)
debug_log.write(job_stats)
