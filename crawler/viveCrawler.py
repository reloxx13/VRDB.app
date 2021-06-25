import datetime
import math
import os
import random
import re
import requests
import sys

from bs4 import BeautifulSoup
from urllib.request import urlopen, urlretrieve

from PIL import Image
from resizeimage import resizeimage
from shutil import copyfile

# Start functions

def tryint(s):
    try:
        return int(s)
    except:
        return s
    

def alphanum_key(s):
    """ Turn a string into a list of string and number chunks.
        "z23a" -> ["z", 23, "a"]
    """
    return [ tryint(c) for c in re.split('([0-9]+)', s) ]


def sort_nicely(l):
    """ Sort the given list in the way that humans expect.
    """
    l.sort(key=alphanum_key, reverse=False)
    

def save_image(appID, imageURL):
    
    filename = imageDir + appID + '.jpg'
    
    if(os.path.exists(filename) == False):
	    print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + "Downloading image for AppID " + appID)
	    
	    urlretrieve(imageURL, filename)
	    
	    fd_img = open(filename, 'rb')
	    img = Image.open(fd_img)
	    img = resizeimage.resize_cover(img, [93, 35])
	    img = img.convert('RGB')
	    img.save(filename, img.format)
	    fd_img.close()
        

def extract_field(source, element, classname, property):
    
    result = ''
    
    try:
        if property == 'text':
            result = source.find(element, {'class', classname}).text
        elif classname == '':
            result = source.find(element)[property]
        else:
            result = source.find(element, {'class', classname})[property]
    except:
        return ''

    return result


def crawl_vr_pages(outputDir, url, overwrite, pages):
    
    print(datetime.datetime.now().strftime('%H:%M:%S') + ' - Crawling ' + url)

    if pages == False:
        
        user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
        headers = {'User-Agent': user_agent}
        response = requests.get(url, headers=headers)
        
        soup = BeautifulSoup(response.content, 'html.parser')
        paginator = soup.find('div', {'class', 'search_pagination_right'})
        pageLinks = paginator.findAll('a')
        
        pages = 0
    
        for pageLink in pageLinks:
            pageNum = int(pageLink['href'].split('page=')[1])
            
            if pageNum > pages:
                pages = pageNum
                
        print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + str(pages) + ' pages found. Initializing crawling process.')
        
    for x in range(pages):
        try:
            download_vr_page(outputDir, url + str(x+1), x+1, overwrite)
        except Exception as e:
            print(e)    
    
    
def download_vr_page(outputDir, url, page, overwrite):
    
    if os.path.exists(outputDir + str(page) + '.html') == True and overwrite == False:
        print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + 'Skipping VR page ' + str(page))
        
    else:
        user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
        headers = {'User-Agent': user_agent}
        response = requests.get(url, headers=headers)
    
        open(outputDir + str(page) + '.html', 'wb').write(response.content)
        
        print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + 'Downloading VR page ' + str(page))
        

def crawl_vr_apps(inputDir, download, overwrite, limit):
    
    # Now start parsing the VR listing pages
    
    print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + 'Parsing directory ' + inputDir)
    
    pages = os.listdir(inputDir)
    sort_nicely(pages)
    
    if limit != False:
        if len(pages) > limit:
            pages = pages[:limit]
    
    appCount = 0
    
    for page in pages:
        
        print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + 'Scanning VR page ' + page)
        soup = BeautifulSoup(open(inputDir + page, 'rb'), 'html.parser')
        
        apps = soup.findAll('a', {'class', 'search_result_row'})
        
        for app in apps:

            try:
                appLink = app['href']
        
                appID   = appLink.split('/')[4]
                title   = extract_field(app, 'span', 'title', 'text')
                image   = extract_field(app, 'img', '', 'src')
                reviews = extract_field(app, 'span', 'search_review_summary', 'data-tooltip-html')
                
                if len(image) > 1:
                    save_image(appID, image)
                
                if download == True and len(reviews) > 1:
                    download_vr_app(appsDir, appLink, appID, title, overwrite)
            
            except Exception as e:
                print(e)
    
    print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + str(appCount) + ' apps were succesfully scanned for new images.')
    

def download_vr_app(outputDir, url, appID, title, overwrite):
    
    if os.path.exists(outputDir + appID + '.html') == True and overwrite == False:
        print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + 'Skipping VR app ' + appID)
        
    else:
        try:
            user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
            headers = {'User-Agent': user_agent}
            response = requests.get(url, headers=headers)
        
            open(outputDir + appID + '.html', 'wb').write(response.content)
            
            print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + 'Downloading VR app ' + appID + ' - ' + title)
        
        except Exception as e:
            print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + 'Error downloading VR app ' + appID + ' - ' + title + ' - ' + str(e))

def viveCrawler(url, downloadPage = False, downloadApps = False, limitPages = None):
    
    user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
    headers = {'User-Agent': user_agent}
    response = requests.get(url, headers=headers)
    
    soup = BeautifulSoup(response.content, 'html.parser')
    
    resultCount = soup.find("span", {"class": "toolbar-number"}).text
    pageTotal = math.ceil(int(resultCount) / 30)
    
    if limitPages != None:
        pageTotal = limitPages
    
    # 30 products per page
    
    for page in range(1, pageTotal + 1):
        pageURL = url + '?p=' + str(page)
        
        viveSubCrawler(pageURL, page, downloadPage, downloadApps)
    
        
def viveSubCrawler(url, pageNr, downloadPage = False, downloadApps = False):
    
    user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
    headers = {'User-Agent': user_agent}
    response = requests.get(url, headers=headers)
    
    print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + 'Crawling ' + url)
    
    if downloadPage == True:
        pageFile = url.replace('https://www.viveport.com/', '').replace('.html', '') + '.html'
        print(pageFile)
        open(mainDir + pageFile, 'wb').write(response.content)
    
    if downloadApps == True:
        soup = BeautifulSoup(response.content, 'html.parser')
        products = soup.find_all("li", {"class": "product"})
        
        for product in products:
            appLink = product.find("a", {"class": "product-item-photo"})['href']
            
            if len(appLink) == 61:
                viveDownloader(appLink)

def viveDownloader(url, overwrite = True):
    
    appID = url.replace('https://www.viveport.com/', '')
    
    if os.path.exists(appsDir + appID + '.html') == True and overwrite == False:
        print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + 'Skipping VR app ' + appID)
        
    else:
        try:
            user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
            headers = {'User-Agent': user_agent}
            response = requests.get(url, headers=headers)
        
            open(appsDir + appID + '.html', 'wb').write(response.content)
            
            print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + 'Downloading VR app ' + appID)
        
        except Exception as e:
            print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + 'Error downloading VR app ' + appID + ' - ' + str(e))
        
    
# End functions
    
region = "eu"
    
mainDir = "/VRDB/HTML/Viveport/Pages/" + region + "/"
appsDir = "/VRDB/HTML/Viveport/Apps/" + region + "/"
imageDir = "/VRDB/HTML/Viveport/Images/"

gameURL = "https://www.viveport.com/game.html"
appsURL = "https://www.viveport.com/app.html"

viveCrawler(gameURL, True, True, 3)
viveCrawler(appsURL, True, True, 3)















