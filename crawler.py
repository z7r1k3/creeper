import requests
from bs4 import BeautifulSoup

def web(totalLevels, levels, passedUrl):
    totalDepth = int(totalLevels)
    depth = int(levels)

    if(int(levels) > 0):
        code = requests.get(passedUrl)
        s = BeautifulSoup(code.content, "html.parser")

        for link in s.findAll('a'):
            href = link.get('href')
            indent = ''

            # Only if domain is not the same as the one passed into this method
            if (passedUrl not in href and 'http' in href):
                # Add line break at start of new branch
                if (depth == totalDepth):
                    print()
                
                # Handle formatting
                for i in range(depth, totalDepth):
                    indent += '     '
                    i += 1
                
                # Print domain
                print(indent + href)

                # Get domains on found domain
                web(totalDepth, depth - 1, href)



# Get user variables
depth = input("How many levels deep should the crawler go?\n")
url = input("What is the target URL?\n")

web(depth, depth, url)