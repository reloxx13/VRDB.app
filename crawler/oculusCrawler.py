# -*- coding: utf-8 -*-

import csv
import datetime
import ftplib
import json
import os
import re
import sqlite3
import sys
import time
import urllib.request

#import undetected_chromedriver as uc
#uc.install()

from bs4 import BeautifulSoup
from ftplib import FTP
from selenium import webdriver
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
from sqlite3 import Error
from urllib.request import urlopen, urlretrieve

from PIL import Image
from resizeimage import resizeimage

sleeptime = 5

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

        
def save_image_rift(appID, imageURL):
    
    filename = imageDirRift + appID + '.jpg'
    
    if(os.path.exists(filename) == False):
	    print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + "Downloading image for AppID " + appID)
	    
	    urlretrieve(imageURL, filename)
	    
	    fd_img = open(filename, 'rb')
	    img = Image.open(fd_img)
	    img = resizeimage.resize_cover(img, [62, 35])
	    img = img.convert('RGB')
	    img.save(filename, img.format)
	    fd_img.close()
        

def modifiedToday(filename):
    
    try:
        modtime = datetime.datetime.fromtimestamp(os.path.getmtime(filename)).strftime('%Y-%m-%d %H')
        
        curtime = datetime.datetime.now().strftime('%Y-%m-%d %H')
        curtimeplus = (datetime.datetime.now() + datetime.timedelta(hours=1)).strftime('%Y-%m-%d %H')
        curtimeminus = (datetime.datetime.now() - datetime.timedelta(hours=1)).strftime('%Y-%m-%d %H')
        
        curhour = datetime.datetime.now().strftime('%H')
        
        if (modtime != curtime and modtime != curtimeplus and modtime != curtimeminus):
            if int(curhour) >= 5 and int(curhour) < 7:
                return False
            elif int(curhour) >= 9 and int(curhour) < 11:
                return False
            elif int(curhour) >= 13 and int(curhour) < 15:
                return False
            elif int(curhour) >= 17 and int(curhour) < 19:
                return False
            elif int(curhour) >= 21 and int(curhour) < 23:
                return False
            else:
                return True
        else:
            return True
    except:
        return False
        

# Rift store functions
    
def riftListing():

    print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + 'Initializing Rift listing')
    
    driver.get(listURLRift)
    time.sleep(sleeptime)

    print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + 'Waiting for Rift listing initial load')
    
    soup = BeautifulSoup(driver.page_source.encode('utf-8'), 'html.parser')
    
    data = json.loads(soup.find('script', type='application/ld+json').text)
    appCount = len(data['itemListElement'])
    appCountCurrent = 0
    
    attemptMax = 5
    attemptCur = 0
    
    lenOfPage = driver.execute_script("window.scrollTo(0, document.body.scrollHeight);var lenOfPage=document.body.scrollHeight;return lenOfPage;")
    
    while(appCountCurrent < (appCount)):
        time.sleep(sleeptime)
        lenOfPage = driver.execute_script("window.scrollTo(0, document.body.scrollHeight);var lenOfPage=document.body.scrollHeight;return lenOfPage;")
        
        soup = BeautifulSoup(driver.page_source.encode('utf-8'), 'html.parser')
        items = soup.findAll('div', {'class', 'store-section-item'})
        
        if appCountCurrent == len(items):
            attemptCur += 1
            print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + 'Attempt ' + str(attemptCur) + '...')
        else:
            attemptCur = 0
        
        if attemptCur == attemptMax:
            appCountCurrent = appCount
            print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + 'Aborting Rift load!')
        else:
            appCountCurrent = len(items)
        
        print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + str(appCountCurrent).zfill(4) + '/' + str(appCount).zfill(4) + ' Rift apps loaded')
            
    file = open(inputDir + 'inputRift.html', 'wb')
    file.write(driver.page_source.encode('utf-8'))
    file.close()
    
    # Coming Soon listing
    
    print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + 'Initializing Rift Coming Soon listing')
    
    driver.get(listURLRiftSoon)
    time.sleep(sleeptime)
    
    print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + 'Waiting for Rift Coming Soon listing initial load')
    
    soup = BeautifulSoup(driver.page_source.encode('utf-8'), 'html.parser')
    
    data = json.loads(soup.find('script', type='application/ld+json').text)
    appCount = len(data['itemListElement'])
    appCountCurrent = 0
    
    attemptMax = 5
    attemptCur = 0
    
    lenOfPage = driver.execute_script("window.scrollTo(0, document.body.scrollHeight);var lenOfPage=document.body.scrollHeight;return lenOfPage;")
    
    while(appCountCurrent < (appCount)):
        time.sleep(sleeptime)
        lenOfPage = driver.execute_script("window.scrollTo(0, document.body.scrollHeight);var lenOfPage=document.body.scrollHeight;return lenOfPage;")
        
        soup = BeautifulSoup(driver.page_source.encode('utf-8'), 'html.parser')
        items = soup.findAll('div', {'class', 'store-section-item'})
        
        if appCountCurrent == len(items):
            attemptCur += 1
            print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + 'Attempt ' + str(attemptCur) + '...')
        else:
            attemptCur = 0
        
        if attemptCur == attemptMax:
            appCountCurrent = appCount
            print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + 'Aborting Rift load!')
        else:
            appCountCurrent = len(items)
        
        print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + str(appCountCurrent).zfill(4) + '/' + str(appCount).zfill(4) + ' Rift apps loaded')
            
    file = open(inputDir + 'inputRiftSoon.html', 'wb')
    file.write(driver.page_source.encode('utf-8'))
    file.close()

    print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + 'Rift listings saved succesfully')
    
    
def riftFilter():    
    
    appIDList = []
    
    soup = BeautifulSoup(open(inputDir + 'inputRift.html', 'rb'), 'html.parser')
    
    links = soup.findAll('a', href=re.compile("/experiences/rift/"));
    
    for link in links:
        linkHref  = link['href']
        linkAttrs = link.attrs
        
        if 'google' not in linkHref:
            if '/section/' not in linkHref:
                appID = linkHref.split('/')[3]
                
                if appID.isdigit():
                    appIDList.append(appID)
                    imageLink = linkAttrs['style'].replace('background-image: url("', '').replace('");', '')
                    save_image_rift(appID, imageLink)
                    
    # Coming Soon list
    
    soup = BeautifulSoup(open(inputDir + 'inputRiftSoon.html', 'rb'), 'html.parser')
    
    links = soup.findAll('a', href=re.compile("/experiences/rift/"));
    
    for link in links:
        linkHref  = link['href']
        linkAttrs = link.attrs
        
        if 'google' not in linkHref:
            if '/section/' not in linkHref:
                appID = linkHref.split('/')[3]
                
                if appID.isdigit():
                    appIDList.append(appID)
                    imageLink = linkAttrs['style'].replace('background-image: url("', '').replace('");', '')
                    save_image_rift(appID, imageLink)                    
                        
    appIDList = list(set(appIDList)) # Remove duplicates
    
    print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + str(len(appIDList)) + ' applications found in HTML sources')
    
    os.chdir(rawDirRift)
    appsRaw = sorted(filter(os.path.isfile, os.listdir(rawDirRift)), key=os.path.getmtime)
    os.chdir(mainDir)
    
    appMax = maxCrawled
    appCur = 0
    
    appIDDirPart = []
    appIDDirFull = []
    
    for app in appsRaw:
        
        appID = app.replace('.html', '')
        appIDDirFull.append(appID)
        
        if appCur < appMax:
            appIDDirPart.append(appID)
            appCur += 1
    
    appIDDiffList = list(set(appIDList) - set(appIDDirFull))
    
    appIDList = appIDDirPart + appIDDiffList
    appIDList = list(set(appIDList)) # Remove duplicates
    
    countCurrent = 1
    
    for appID in appIDList:
        riftCrawler(sourceURLRift + appID, appID, driver, countCurrent, len(appIDList))
        countCurrent += 1


def riftCrawler(inputURL, appID, driver, countCurrent, countMax):
    
    try:
        filename = rawDirRift + appID + '.html'
        
        #if(os.path.exists(filename) == False):
        print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + str(countCurrent).zfill(4) + "/" + str(countMax).zfill(4) + " - Downloading " + appID)
        
        driver.get(inputURL)
        
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CLASS_NAME, 'app__description')))
        
        try:
            driver.find_element_by_class_name('app-details-version-info-row__link').click()
        except:
            pass
        
        time.sleep(1)
        
        file = open(filename, 'wb')
        file.write(driver.page_source.encode('utf-8'))
        file.close()
    except:
        print('Error downloading ' + appID)
    
    
# Quest store functions
    
def questListing():

    print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + 'Initializing Quest listing')
    
    driver.get(listURL)
    time.sleep(sleeptime)

    print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + 'Waiting for Quest listing initial load')
    
    soup = BeautifulSoup(driver.page_source.encode('utf-8'), 'html.parser')
    
    data = json.loads(soup.find('script', type='application/ld+json').text)
    appCount = len(data['itemListElement'])
    appCountCurrent = 0
    
    attemptMax = 5
    attemptCur = 0
    
    lenOfPage = driver.execute_script("window.scrollTo(0, document.body.scrollHeight);var lenOfPage=document.body.scrollHeight;return lenOfPage;")
    
    while(appCountCurrent < (appCount)):
        time.sleep(sleeptime)
        lenOfPage = driver.execute_script("window.scrollTo(0, document.body.scrollHeight);var lenOfPage=document.body.scrollHeight;return lenOfPage;")
        
        soup = BeautifulSoup(driver.page_source.encode('utf-8'), 'html.parser')
        items = soup.findAll('div', {'class', 'store-section-item'})
        
        if appCountCurrent == len(items):
            attemptCur += 1
            print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + 'Attempt ' + str(attemptCur) + '...')
        else:
            attemptCur = 0
        
        if attemptCur == attemptMax:
            appCountCurrent = appCount
            print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + 'Aborting Quest load!')
        else:
            appCountCurrent = len(items)
        
        print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + str(appCountCurrent).zfill(4) + '/' + str(appCount).zfill(4) + ' Quest apps loaded')
            
    file = open(inputDir + 'inputQuest.html', 'wb')
    file.write(driver.page_source.encode('utf-8'))
    file.close()
    
    # Coming Soon listing
    
    print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + 'Initializing Quest Coming Soon listing')
    
    driver.get(listURLSoon)
    time.sleep(sleeptime)
    
    print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + 'Waiting for Quest Coming Soon listing initial load')
    
    soup = BeautifulSoup(driver.page_source.encode('utf-8'), 'html.parser')
    
    data = json.loads(soup.find('script', type='application/ld+json').text)
    appCount = len(data['itemListElement'])
    appCountCurrent = 0
    
    attemptMax = 5
    attemptCur = 0
    
    lenOfPage = driver.execute_script("window.scrollTo(0, document.body.scrollHeight);var lenOfPage=document.body.scrollHeight;return lenOfPage;")
    
    while(appCountCurrent < (appCount)):
        time.sleep(sleeptime)
        lenOfPage = driver.execute_script("window.scrollTo(0, document.body.scrollHeight);var lenOfPage=document.body.scrollHeight;return lenOfPage;")
        
        soup = BeautifulSoup(driver.page_source.encode('utf-8'), 'html.parser')
        items = soup.findAll('div', {'class', 'store-section-item'})
        
        if appCountCurrent == len(items):
            attemptCur += 1
            print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + 'Attempt ' + str(attemptCur) + '...')
        else:
            attemptCur = 0
        
        if attemptCur == attemptMax:
            appCountCurrent = appCount
            print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + 'Aborting Quest load!')
        else:
            appCountCurrent = len(items)
        
        print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + str(appCountCurrent).zfill(4) + '/' + str(appCount).zfill(4) + ' Quest apps loaded')
            
    file = open(inputDir + 'inputQuestSoon.html', 'wb')
    file.write(driver.page_source.encode('utf-8'))
    file.close()
    
    # Crossbuy listing
    
    print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + 'Initializing Quest Crossbuy listing')
    
    driver.get(listURLCB)
    time.sleep(sleeptime)
    
    print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + 'Waiting for Quest Crossbuy listing initial load')
    
    soup = BeautifulSoup(driver.page_source.encode('utf-8'), 'html.parser')
    
    data = json.loads(soup.find('script', type='application/ld+json').text)
    appCount = len(data['itemListElement'])
    appCountCurrent = 0
    
    attemptMax = 5
    attemptCur = 0
    
    lenOfPage = driver.execute_script("window.scrollTo(0, document.body.scrollHeight);var lenOfPage=document.body.scrollHeight;return lenOfPage;")
    
    while(appCountCurrent < (appCount)):
        time.sleep(sleeptime)
        lenOfPage = driver.execute_script("window.scrollTo(0, document.body.scrollHeight);var lenOfPage=document.body.scrollHeight;return lenOfPage;")
        
        soup = BeautifulSoup(driver.page_source.encode('utf-8'), 'html.parser')
        items = soup.findAll('div', {'class', 'store-section-item'})
        
        if appCountCurrent == len(items):
            attemptCur += 1
            print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + 'Attempt ' + str(attemptCur) + '...')
        else:
            attemptCur = 0
        
        if attemptCur == attemptMax:
            appCountCurrent = appCount
            print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + 'Aborting Quest load!')
        else:
            appCountCurrent = len(items)
        
        print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + str(appCountCurrent).zfill(4) + '/' + str(appCount).zfill(4) + ' Quest apps loaded')
            
    file = open(inputDir + 'inputQuestCB.html', 'wb')
    file.write(driver.page_source.encode('utf-8'))
    file.close()

    print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + 'Quest listings saved succesfully')


def questFilter():    
    
    appIDList = []
    
    soup = BeautifulSoup(open(inputDir + 'inputQuest.html', 'rb'), 'html.parser')
    
    links = soup.findAll('a', href=re.compile("/experiences/quest/"));
    
    for link in links:
        linkHref  = link['href']
        linkAttrs = link.attrs
        
        if 'google' not in linkHref:
            if '/section/' not in linkHref:
                appID = linkHref.split('/')[3]
                
                if appID.isdigit():
                    appIDList.append(appID)
                    imageLink = linkAttrs['style'].replace('background-image: url("', '').replace('");', '')
                    save_image(appID, imageLink)
                    
    # Coming Soon list
    
    soup = BeautifulSoup(open(inputDir + 'inputQuestSoon.html', 'rb'), 'html.parser')
    
    links = soup.findAll('a', href=re.compile("/experiences/quest/"));
    
    for link in links:
        linkHref  = link['href']
        linkAttrs = link.attrs
        
        if 'google' not in linkHref:
            if '/section/' not in linkHref:
                appID = linkHref.split('/')[3]
                
                if appID.isdigit():
                    appIDList.append(appID)
                    imageLink = linkAttrs['style'].replace('background-image: url("', '').replace('");', '')
                    save_image(appID, imageLink)                    
                        
    appIDList = list(set(appIDList)) # Remove duplicates
    
    print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + str(len(appIDList)) + ' applications found in HTML sources')
    
    os.chdir(rawDir)
    appsRaw = sorted(filter(os.path.isfile, os.listdir(rawDir)), key=os.path.getmtime)
    os.chdir(mainDir)
    
    appMax = maxCrawled
    appCur = 0
    
    appIDDirPart = []
    appIDDirFull = []
    
    for app in appsRaw:
        
        appID = app.replace('.html', '')
        appIDDirFull.append(appID)
        
        if appCur < appMax:
            appIDDirPart.append(appID)
            appCur += 1
    
    appIDDiffList = list(set(appIDList) - set(appIDDirFull))
    
    appIDList = appIDDirPart + appIDDiffList
    appIDList = list(set(appIDList)) # Remove duplicates
    
    countCurrent = 1
    
    for appID in appIDList:
        questCrawler(sourceURL + appID, appID, True, driver, countCurrent, len(appIDList))
        countCurrent += 1


def questCrawler(inputURL, appID, download, driver, countCurrent, countMax):
    
    try:    
        if download == True:
            
            filename = rawDir + appID + '.html'
            
            print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + str(countCurrent).zfill(4) + "/" + str(countMax).zfill(4) + " - Downloading " + appID)
            driver.get(inputURL)
            WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CLASS_NAME, 'app__description')))
            
            try:
                driver.find_element_by_class_name('app-details-version-info-row__link').click()
            except:
                pass
            
            time.sleep(1)
            
            file = open(filename, 'wb')
            file.write(driver.page_source.encode('utf-8'))
            file.close()
    
        else:
            soup = BeautifulSoup(driver.page_source, 'lxml')
                
            links = soup.findAll('a', {'class': 'store-section-item-tile'});
            
            for link in links:
                linkHref = link['href']
                
                if '/quest/section/' in linkHref:
                    print(link['href'])
                
                elif '/quest/' in linkHref:
                    print(link['href'])
    
    except Exception as e:
        print("Error downloading app " + appID)
        print(e)
        
        
def questLabListing():
    
    print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + " - Refreshing Quest App Lab listing...")
    
    linkList = []
    
    # Reddit
    
    try:
        req = urllib.request.Request(
            'https://old.reddit.com/r/oculusquest/wiki/faq/applab', 
            data=None, 
            headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
            }
        )
        
        soup = BeautifulSoup(urlopen(req), 'html.parser')
        
        wiki = soup.find('div', {'class', 'wiki'})
        
        links = wiki.findAll('a', href=re.compile("/experiences/quest/"));
        
        for link in links:
            
            linkHref  = link['href']
            
            if '/experiences/quest/' in linkHref:
                linkList.append(linkHref)
                
    except Exception as e:
        print("Error refreshing Reddit wiki App Lab source")
        print(e)
        
    # AppLabDB
    
    try:
        req = urllib.request.Request(
            'https://www.applabdb.com/new', 
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
        
    # Make link list unique and start crawling
    
    linkList = list(set(linkList))
    
    print(linkList)
    
    for link in linkList:
        appID = re.findall('\d+', link)[0]
        questLabCrawler(link, appID, driver)


def questLabCrawler(inputURL, appID, driver):
    
    try:    
        filename = labDir + appID + '.html'
        
        print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + " - Downloading App Lab " + appID)
        driver.get(inputURL)
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CLASS_NAME, 'app__description')))
        
        try:
            driver.find_element_by_class_name('app-details-version-info-row__link').click()
        except:
            pass
        
        time.sleep(1)
        
        if 'App Lab' in driver.page_source:
            file = open(filename, 'wb')
            file.write(driver.page_source.encode('utf-8'))
            file.close()
            
        else:
            print('Skipping ' + inputURL + ', not an App Lab entry')
    
    except Exception as e:
        print("Error downloading lab app " + appID)
        print(e)         
                
                

# Multiplatform category crawling functions
                
def sectionCrawler(platform, mainURL, catDir):
    
    # Start crawling process
    
    sleeptime = 5
    
    if platform != 'quest':
        sleeptime = 10

    print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + 'Loading main platform page')
    
    driver.get(mainURL)
    time.sleep(sleeptime)
    
    print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + 'Waiting for main platform page')
    
    soup = BeautifulSoup(driver.page_source.encode('utf-8'), 'html.parser')
    
    lenOfPage = driver.execute_script("window.scrollTo(0, document.body.scrollHeight);var lenOfPage=document.body.scrollHeight;return lenOfPage;")
    match = False
    
    while(match == False):
        lastCount = lenOfPage
        time.sleep(sleeptime)
        lenOfPage = driver.execute_script("window.scrollTo(0, document.body.scrollHeight);var lenOfPage=document.body.scrollHeight;return lenOfPage;")
        print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + 'Scrolling through main platform page...')
        if lastCount == lenOfPage:
            match = True
        
    soup = BeautifulSoup(driver.page_source.encode('utf-8'), 'html.parser')
    
    links = soup.findAll('a', {'class': 'store-section-header__title'});
    
    for link in links:
        linkHref = link['href']
        
        if 'Browse all' not in link.text and 'Browse All' not in link.text:
            if '/' + platform + '/section/' in linkHref:
                sectionDownloader(platform, link['href'], catDir, link.text)
    

def sectionDownloader(platform, catURL, catDir, catTitle):
    
    print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + 'Initializing category downloader for ' + catTitle)
    print(catURL)
    
    print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + 'Waiting for category initial load')
    driver.get(rootURL + catURL)
    time.sleep(sleeptime)
    
    try:
        soup = BeautifulSoup(driver.page_source.encode('utf-8'), 'html.parser')
        
        data = json.loads(soup.find('script', type='application/ld+json').text)
        appCount = len(data['itemListElement'])
        appCountCurrent = 0
        
        attemptMax = 5
        attemptCur = 0
        
        lenOfPage = driver.execute_script("window.scrollTo(0, document.body.scrollHeight);var lenOfPage=document.body.scrollHeight;return lenOfPage;")
        
        while(appCountCurrent < (appCount)):
            time.sleep(sleeptime)
            lenOfPage = driver.execute_script("window.scrollTo(0, document.body.scrollHeight);var lenOfPage=document.body.scrollHeight;return lenOfPage;")
            
            soup = BeautifulSoup(driver.page_source.encode('utf-8'), 'html.parser')
            items = soup.findAll('div', {'class', 'store-section-item'})
            
            if appCountCurrent == len(items):
                attemptCur += 1
                print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + 'Attempt ' + str(attemptCur) + '...')
            else:
                attemptCur = 0
            
            if attemptCur == attemptMax:
                appCountCurrent = appCount
                print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + 'Aborting category load!')
            else:
                appCountCurrent = len(items)
            
            print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + str(appCountCurrent).zfill(4) + '/' + str(appCount).zfill(4) + ' apps loaded')
            
        catFile = catTitle + '.html'
        
        try:
            if os.path.isfile(catDir + catFile):
                os.unlink(catDir + catFile)
        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (catDir + catFile, e))
    
        file = open(catDir + catFile, 'wb')
        file.write(driver.page_source.encode('utf-8'))
        file.close()
        
    except:
        print('Error loading category! Skipping...')

            
def sectionDownloader(platform, catURL, catDir, catTitle):
    
    print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + 'Initializing category downloader for ' + catTitle)
    
    print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + 'Waiting for category initial load')
    driver.get(rootURL + catURL)
    time.sleep(sleeptime)
    
    try:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);var lenOfPage=document.body.scrollHeight;return lenOfPage;")
        
        data = json.loads(soup.find('script', type='application/ld+json').text)
        appCount = len(data['itemListElement'])
        appCountCurrent = 0
        
        attemptMax = 5
        attemptCur = 0
        
        while(appCountCurrent < (appCount)):
            time.sleep(sleeptime)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);var lenOfPage=document.body.scrollHeight;return lenOfPage;")
            
            soup = BeautifulSoup(driver.page_source.encode('utf-8'), 'html.parser')
            items = soup.findAll('div', {'class', 'store-section-item'})
            
            if appCountCurrent == len(items):
                attemptCur += 1
                print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + 'Attempt ' + str(attemptCur) + '...')
            else:
                attemptCur = 0
            
            if attemptCur == attemptMax:
                appCountCurrent = appCount
                print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + 'Aborting category load!')
            else:
                appCountCurrent = len(items)
            
            print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + str(appCountCurrent).zfill(4) + '/' + str(appCount).zfill(4) + ' apps loaded')
            
        catFile = catTitle + '.html'
        
        file = open(catDir + catFile, 'wb')
        file.write(driver.page_source.encode('utf-8'))
        file.close()
    
    except:
        print('Error loading section page.')
    
                   
# End functions
    
rootURL  = 'https://www.oculus.com'

sourceURL   = 'https://www.oculus.com/experiences/quest/'
listURL     = 'https://www.oculus.com/experiences/quest/section/1888816384764129/'
listURLSoon = 'https://www.oculus.com/experiences/quest/section/2540605779297669/'
listURLCB   = 'https://www.oculus.com/experiences/quest/section/2335732183153590/'

sourceURLRift   = 'https://www.oculus.com/experiences/rift/'
listURLRift     = 'https://www.oculus.com/experiences/rift/section/1736210353282450/'
listURLRiftSoon = 'https://www.oculus.com/experiences/rift/section/1895750390540682/'

sourceURLGo = 'https://www.oculus.com/experiences/go/'
listURLGo   = 'https://www.oculus.com/experiences/go/section/174868819587665/'

region = "eu"

if len(sys.argv) >= 2:
    if sys.argv[1] != None:
        region = sys.argv[1]

mainDir    = "/VRDB/HTML/Oculus/"
slash      = "/"
inputDir   = mainDir + "Sections/" + region + slash
#rawDir     = mainDir + "Apps/Quest/" + region + slash
rawDir     = mainDir + "Apps/Quest/ww/"
catDir     = mainDir + "Categories/Quest/" + region + slash
imageDir   = mainDir + "Images/Quest/"
labDir     = mainDir + "Apps/Lab/" + region + slash

chromePath = "/usr/bin/chromedriver"
userProfile = "/.config/google-chrome/Default"

#rawDirRift   = mainDir + "Apps/Rift/" + region + slash
rawDirRift   = mainDir + "Apps/Rift/ww/" 
catDirRift   = mainDir + "Categories/Rift/" + region + slash
imageDirRift = mainDir + "Images/Rift/"

rawDirGo   = mainDir + "Apps/Go/" + region + slash
catDirGo   = mainDir + "Categories/Go/" + region + slash
imageDirGo = mainDir + "Images/Go/"

maxCrawled = 10

options = webdriver.ChromeOptions()
options.add_argument('--headless') 
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--start-maximized')
options.add_argument('--blink-settings=imagesEnabled=false')
options.add_argument("user-data-dir={}".format(userProfile))
options.add_argument('--disable-blink-features=AutomationControlled')
options.add_experimental_option('excludeSwitches', ['enable-automation'])
options.add_experimental_option('useAutomationExtension', False)
       
driver = webdriver.Chrome(options=options, executable_path=chromePath)
driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

#options = uc.ChromeOptions()
#options.add_argument("--start-maximized")
#options.headless=False
#options.add_argument('--headless')
#driver = uc.Chrome(options=options)

print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + "CRAWLING QUEST DATABASE - REGION " + region.upper())

questListing()
questFilter()

riftFilter()

sectionCrawler('quest', sourceURL, catDir)
sectionCrawler('rift', sourceURLRift, catDirRift)

if modifiedToday(inputDir + 'inputRift.html') == False:
    print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + "CRAWLING RIFT DATABASE - REGION " + region.upper())
    riftListing()
    sectionCrawler('rift', sourceURLRift, catDirRift)
    questLabListing()
    
driver.close()
