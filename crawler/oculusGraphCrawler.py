from bs4 import BeautifulSoup 
from PIL import Image
from resizeimage import resizeimage
from urllib.request import urlopen, urlretrieve

import datetime
import json
import os
import re
import requests
import time
import urllib.request
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def save_image(appID, imageURL):
    
    filename = imageDir + appID + '.jpg'
    
    if(os.path.exists(filename) == False):
	    print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + "Downloading image for AppID " + appID)
	    
	    urlretrieve(imageURL, filename)
	    
	    fd_img = open(filename, 'rb')
	    img = Image.open(fd_img)
	    img = resizeimage.resize_cover(img, [62, 35])
	    img = img.convert('RGB')
	    img.save(filename, img.format)
	    fd_img.close()

def crawlSectionIndex(platform, region, hmdType, end_cursor = 'null', access_token_override = ''):

    if end_cursor != 'null':
        end_cursor = '"' + end_cursor + '"'    
        
    else:
        print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + 'Downloading all ' + hmdType + ' sections')
    
    if len(access_token_override) > 1:
        params = {
                  'access_token': access_token_override
                  ,'variables': '{"cursor":' + end_cursor + ',"hmdType":"' + hmdType + '","isTest":false,"sectionCount":null,"storeID":null}'
                  ,'doc_id': '3817711471649061'
                }    
        
    else:
        params = {
                  'access_token': access_token
                  ,'variables': '{"cursor":' + end_cursor + ',"hmdType":"' + hmdType + '","isTest":false,"sectionCount":null,"storeID":null}'
                  ,'doc_id': '3817711471649061'
                }

    
    result = requests.post(url, data = params, verify=False)
    json_output = json.loads(result.text)
    
    sections = json_output['data']['viewer']['app_store']['sections']['edges']
    
    for section in sections:
        
        sectionType = section['node']['__isAppStoreSection']
        sectionName = section['node']['section_name']
        sectionID   = section['node']['id']
        
        if sectionType == 'AppStoreDynamicCategorySection' and sectionName != 'Your Wishlist':
            crawlSection(hmdType, sectionID, outdirCats + platform + '.' + region + '.' + sectionName + '.json')
    
    end_cursor = json_output['data']['viewer']['app_store']['sections']['page_info']['end_cursor']
    
    if end_cursor != None:
        print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + 'End cursor reached, requesting more sections...')
        crawlSectionIndex(platform, region, hmdType, end_cursor, access_token_override)
    else:
        print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + 'Section batch download complete')
    

def crawlSection(hmdType, sectionID, outFile, end_cursor = 'null', access_token_override = ''):

    if end_cursor != 'null':
        end_cursor = '"' + end_cursor + '"'
        
    else:
        print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + 'Downloading ' + hmdType + ' section ' + outFile.replace(outdirList, '').replace(outdirCats, ''))
        
    if len(access_token_override) > 1:
        params = {
                'access_token': access_token_override
                ,'variables': '{"sectionId":"' + sectionID + '","sortOrder":"release_date","sectionItemCount":500,"sectionCursor":' + end_cursor + ',"hmdType":"' + hmdType + '"}'
                ,'doc_id': '3821696797949516'
                }
        
    else:
        params = {
                'access_token': access_token
                ,'variables': '{"sectionId":"' + sectionID + '","sortOrder":"release_date","sectionItemCount":500,"sectionCursor":' + end_cursor + ',"hmdType":"' + hmdType + '"}'
                ,'doc_id': '3821696797949516'
                }      
        
    result = requests.post(url, data = params, verify=False)

    if end_cursor != 'null':
        listFile = open(outFile, "a")
        listFile.write('\n' + result.text)
        listFile.close()
    else:
        listFile = open(outFile, "w")
        listFile.write(result.text)
        listFile.close()
    
    json_output = json.loads(result.text)
    #print(result.text)
    
    end_cursor = json_output['data']['node']['all_items']['page_info']['end_cursor']
    
    if end_cursor != None:
        print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + 'End cursor reached, requesting next 500 result dataset...')
        crawlSection(hmdType, sectionID, outFile, end_cursor, access_token_override)
    else:
        count = json_output['data']['node']['all_items']['count']
        print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + 'Section download complete, ' + str(count) + ' entries in total')
        
    time.sleep(sleepTime)


def crawlApps(platform, region, hmdType, outdirApps, end_cursor = 'null', countCurrent = 0, countTotal = 0, sectionID = None, access_token_override = ''):
    
    print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + 'Retrieving list of all ' + hmdType + ' apps...')
    
    if sectionID == None:
        if hmdType == 'RIFT':
            sectionID = '1736210353282450'
        else:
            sectionID = '1888816384764129'
        
    if end_cursor != 'null':
        end_cursor = '"' + end_cursor + '"'
      
    if len(access_token_override) > 1:
        params = { # BROWSE ALL SECTION
                  'access_token': access_token_override
                  ,'variables': '{"sectionId":"'+ sectionID + '","sortOrder":"release_date","sectionItemCount":500,"sectionCursor":' + end_cursor + ',"hmdType":"' + hmdType + '"}'
                  ,'doc_id': '3821696797949516'
                }
    
    else:
        params = { # BROWSE ALL SECTION
                  'access_token': access_token
                  ,'variables': '{"sectionId":"'+ sectionID + '","sortOrder":"release_date","sectionItemCount":500,"sectionCursor":' + end_cursor + ',"hmdType":"' + hmdType + '"}'
                  ,'doc_id': '3821696797949516'
                }
    
    result = requests.post(url, data = params, verify=False)
    
    json_output = json.loads(result.text)
    
    #print(json_output)
    
    if end_cursor == 'null':
        countTotal = json_output['data']['node']['all_items']['count']
        countCurrent = 0
        
    # Apps limit per run (per result set)
    
    appIDList = []
    
    for app in json_output['data']['node']['all_items']['edges']:
        appID = app['node']['id']
        appIDList.append(appID)
    
    if sectionID in ('1736210353282450', '1888816384764129'):
        os.chdir(outdirApps)
        appsRaw = sorted(filter(os.path.isfile, os.listdir(outdirApps)), key=os.path.getmtime)
        os.chdir(mainDir)
        
        appMax = maxCrawled
        appCur = 0
        
        if platform == 'rift':
            appMax = appMax / 2
        
        appIDDirPart = []
        appIDDirFull = []
        
        for app in appsRaw: 
            
            if platform + '.' + region in app:
                appID = app.replace('.json', '').replace(platform + '.' + region + '.', '')
                appIDDirFull.append(appID)
                
                if appCur < appMax:
                    appIDDirPart.append(appID)
                    appCur += 1
        
        appIDDiffList = list(set(appIDList) - set(appIDDirFull))
        
        appIDList = appIDDirPart + appIDDiffList
        appIDList = list(set(appIDList)) # Remove duplicates
    
    # App limit end
    
    for app in appIDList:
        appID = app
        countCurrent += 1
        
        try:
            crawlAppData(platform, region, hmdType, appID, countCurrent, countTotal, outdirApps)
        except:
            print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + 'Error downloading ' + appID)
            
    end_cursor = json_output['data']['node']['all_items']['page_info']['end_cursor']
    
    if end_cursor != None:
        print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + 'End cursor reached, proceeding with next batch')
        crawlApps(platform, region, hmdType, outdirApps, end_cursor, countCurrent, countTotal)
        
        
def crawlAppData(platform, region, hmdType, appID, countCurrent, countTotal, outDir, access_token_override = ''):
    
    if len(access_token_override) > 1:
        params = { # QUEST APP
                  'access_token': access_token_override
                  ,'variables': '{"itemId":"' + appID + '","first":5,"last":null,"after":null,"before":null,"forward":true,"ordering":null,"ratingScores":null,"hmdType":"' + hmdType + '"}'
                  ,'doc_id': '4136219906435554'
                }
        
    else:
        params = { # QUEST APP
                  'access_token': access_token
                  ,'variables': '{"itemId":"' + appID + '","first":5,"last":null,"after":null,"before":null,"forward":true,"ordering":null,"ratingScores":null,"hmdType":"' + hmdType + '"}'
                  ,'doc_id': '4136219906435554'
                }        
    
    result = requests.post(url, data = params, verify=False)

    data = json.loads(result.text)
    data = data['data']['node']
    
    imageURL = data['hero']['uri']
    save_image(appID, imageURL)
    
    appFile = open(str(outDir + platform + '.' + region + '.' + appID + '.json'), "w")
    appFile.write(result.text)
    appFile.close()
    
    print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + str(countCurrent).zfill(4) + '/' + str(countTotal).zfill(4) + ' - Downloading ' + appID)
    
    time.sleep(sleepTime)
    
    
def crawlApplabDB():
    
    print(datetime.datetime.now().strftime('%H:%M:%S') + ' - Querying ApplabDB.com...')
    
    linkList = []
    
    # AppLabDB
    
    for i in range(6):
    
        try:
            req = urllib.request.Request(
                'https://www.applabdb.com/new/pages/' + str(i + 1), 
                data=None, 
                headers={
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
                }
            )
            
            soup = BeautifulSoup(urlopen(req), 'html.parser')
            wiki = soup.find('body')
            links = wiki.findAll('a', href=re.compile("/experiences/quest/"));
            
            for link in links:
                linkHref  = link['href']
                
                if '/experiences/quest/' in linkHref:
                    linkList.append(linkHref)
                    
        except Exception as e:
            print("Error refreshing AppLabDB source")
            print(e)
            
    return linkList


def crawlApplabGames():
    
    print(datetime.datetime.now().strftime('%H:%M:%S') + ' - Querying Applab.games...')
    
    linkList = []
    
    # AppLab.games
    
    try:
        req = requests.get('https://api.sidequestvr.com/v2/apps?limit=500&is_app_lab=true&has_oculus_url=true&sortOn=hot_sort_rating')
        
        data = req.json()
        
        for item in data:
            appLink = item['oculus_url']
            
            if '/experiences/quest/' in appLink:
                linkList.append(appLink)
                
    except Exception as e:
        print("Error refreshing AppLabDB source")
        print(e)
            
    return linkList
    
    
def crawlLabListing(outdirApps, region, access_token_override = ''):
    
    print(datetime.datetime.now().strftime('%H:%M:%S') + ' - Refreshing Quest App Lab listing...')
    
    linkList = []
    
    # Read CSV file
    
    lablist = open('lablist.csv', 'r')
    lablistApps = lablist.readlines()
    
    for app in lablistApps:
        linkList.append('https://www.oculus.com/experiences/quest/' + app)
        
    # Scan directory for previously crawled entries
#    
#    lablistDir = os.listdir(outdirApps)
#    
#    for labFile in lablistDir:
#        if 'lab.' + region + '.' in labFile:
#            linkList.append('https://www.oculus.com/experiences/quest/' + labFile.replace('.json', ''))
    
    # Add additional sources
    
    linkList = linkList + crawlApplabDB()
    linkList = linkList + crawlApplabGames()
        
    # Make link list unique and start crawling
    
    appList = []
    
    for link in linkList:
        appID = re.findall('\d+', link)[0]
        appList.append(appID)
        
    appList = list(set(appList))
    
    # Apps limit per run (per result set)
    
    appIDList = []
    
    for app in appList:
        appID = app
        appIDList.append(appID)
    
    os.chdir(outdirApps)
    appsRaw = sorted(filter(os.path.isfile, os.listdir(outdirApps)), key=os.path.getmtime)
    os.chdir(mainDir)
    
    appMax = maxCrawled
    appCur = 0
    
    appIDDirPart = []
    appIDDirFull = []
    
    for app in appsRaw:
        
        if 'lab.' + region in app:
            appID = app.replace('.json', '').replace('lab.' + region + '.', '')
            appIDDirFull.append(appID)
            
            if appCur < appMax:
                appIDDirPart.append(appID)
                appCur += 1
    
    appIDDiffList = list(set(appIDList) - set(appIDDirFull))
    
    appIDList = appIDDirPart + appIDDiffList
    appIDList = list(set(appIDList)) # Remove duplicates
    
    # App limit end
    
    countTotal = len(appIDList)
    countCurrent = 0
    
    for appID in appIDList:
        countCurrent += 1
        
        try:
            crawlAppData('lab', region, 'MONTEREY', appID, countCurrent, countTotal, outdirApps, access_token_override)
        except Exception as e:
            print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + 'Error downloading ' + appID)
            print(e)
 

url = 'https://graph.oculus.com/graphql?forced_locale=en_US'
access_token = 'OC|1317831034909742|' # Generic Oculus token

region = 'eu'

mainDir = '/VRDB/Crawler/'
rootDir = '/VRDB/JSON'

outdirList = rootDir + '/Oculus/Sections/'
outdirCats = rootDir + '/Oculus/Categories/'
outdirApps = rootDir + '/Oculus/Apps/'

imageDir   = rootDir + '/Oculus/Images/'

sleepTime = 10

os.chdir(mainDir)

maxCrawled = 40

# MONTEREY = Quest
# RIFT = Rift (Duh...)

crawlSection('MONTEREY', '1888816384764129', outdirList + region + '.inputQuest.json')
crawlSection('MONTEREY', '2540605779297669', outdirList + region + '.inputQuestSoon.json')
crawlSection('MONTEREY', '2335732183153590', outdirList + region + '.inputQuestCB.json')
crawlSectionIndex('quest', region, 'MONTEREY')

crawlSection('RIFT', '1736210353282450', outdirList + region + '.inputRift.json')
crawlSection('RIFT', '1895750390540682', outdirList + region + '.inputRiftSoon.json')
crawlSectionIndex('rift', region, 'RIFT')

crawlApps('quest', region, 'MONTEREY', outdirApps)
crawlApps('quest', region, 'MONTEREY', outdirApps, sectionID = '2540605779297669')

crawlLabListing(outdirApps, region)

crawlApps('rift', region, 'RIFT', outdirApps)
crawlApps('rift', region, 'RIFT', outdirApps, sectionID = '1895750390540682')

print(datetime.datetime.now().strftime('%H:%M:%S') + ' - Crawling complete.')