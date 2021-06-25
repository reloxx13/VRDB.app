# -*- coding: utf-8 -*-

import cssutils
import datetime
import glob
import json
import math
import os
import os.path
import re
import sqlite3
import sys
import time
import uuid

from bs4 import BeautifulSoup
from shutil import copyfile
from sqlite3 import Error

from PIL import Image
from resizeimage import resizeimage
from urllib.request import urlopen, urlretrieve

sleeptime = 5

# DB functions

def create_connection(db_file):
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except Error as e:
        print(e)
 
    return None

def format_bytes(size):
    # 2**10 = 1024
    power = 2**10
    n = 0
    power_labels = {0 : '', 1: 'KB', 2: 'MB', 3: 'GB', 4: 'TB'}
    while size > power:
        size /= power
        n += 1
    
    if n == 2:
        return str(round(size, 1)) + ' ' + power_labels[n]

    elif n == 3:
        return str(round(size, 2)) + ' ' + power_labels[n]
    
    else:
        return str(round(size, 1)) + ' ' + power_labels[n]
    
    
def update_app_index(conn, platform, app):
    sql = 'INSERT OR REPLACE INTO app_index(platform,region,unid,appid,title,price,sale) VALUES("' + platform + '",?,?,?,?,?,?)'
    cur = conn.cursor()
    cur.execute(sql, app)
    
def update_app_details(conn, app):
    sql = 'INSERT OR REPLACE INTO app_details(appid,title,ratings,score,popularity,genres,crossbuy,rdate,gamesize,storelink,released,modes,gamemodes) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)'
    cur = conn.cursor()
    cur.execute(sql, app)
    
def update_app_history(conn, app):
    sql = 'INSERT INTO app_details_history(hdate,appid,title,ratings,score,popularity,genres,crossbuy,rdate,gamesize,storelink,released,modes,gamemodes) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)'
    cur = conn.cursor()
    cur.execute(sql, app)
    
def update_app_versions(conn, app):
    try:
        sql = 'INSERT INTO app_versions(appver,udate,appid,version,notes) VALUES(?,?,?,?,?)'
        cur = conn.cursor()
        cur.execute(sql, app)
    except:
        pass
    
def delete_app_history_duplicates(conn):
    # NOTE TO SELF: This only leaves changes in the DB so we'll have to backtrack through history to find 'em!
    sql = 'DELETE FROM app_details_history WHERE hdate NOT IN (SELECT MAX(hdate) FROM app_details_history GROUP BY appid, ratings, score, popularity, crossbuy, rdate, released)'
    cur = conn.cursor()
    cur.execute(sql)
    conn.commit()
    
def update_app_price(conn, app_price):
    sql = 'INSERT INTO app_prices(appid,pdate,price,currency,sale) VALUES(?,?,?,?,?)'
    cur = conn.cursor()
    cur.execute(sql, app_price)
    
def delete_app_price_duplicates(conn):
    sql = 'DELETE FROM app_prices WHERE priceid NOT IN (SELECT MAX(priceid) FROM app_prices GROUP BY SUBSTR(pdate,0,11),appid, price, currency, sale)'
    cur = conn.cursor()
    cur.execute(sql)
    conn.commit()
    
def update_crossbuy(conn):
    sql = '''INSERT INTO crossbuy (title, appIDQuest, appIDRift)
             SELECT DISTINCT a1.title, MAX(a1.appid), MAX(a2.appid) FROM app_index AS a1 
			 INNER JOIN app_details AS ad1 ON a1.appid = ad1.appid
             INNER JOIN app_index AS a2 ON a1.title = a2.title
             WHERE ad1.crossbuy = 1 AND a1.platform = 'quest' AND a2.platform = 'rift' 
			 AND a1.appid NOT IN (SELECT appIDQuest FROM crossbuy) AND a1.region = "us"
			 GROUP BY a1.title'''
            
    cur = conn.cursor()
    cur.execute(sql)
    conn.commit()
    
def link_crossbuy(conn, value, appID, region, platform):
        
    if platform == 'quest':
        plat1 = 'quest'
        plat2 = 'rift'
    elif platform == 'rift':
        plat1 = 'rift'
        plat2 = 'quest'
    
    sql = 'SELECT appID' + plat2 + ' FROM crossbuy WHERE appID' + plat1 +' = "' + str(appID) + '"'
    cur = conn.cursor()
    cur.execute(sql)
    
    result_row = cur.fetchone()
    
    if result_row:
        result = result_row[0]
        
        plat1Price = current_price(plat1, region, appID)
        plat2Price  = current_price(plat2, region, result)
        
        try:
            if plat1Price > plat2Price:
                return '<a href="https://www.oculus.com/experiences/' + plat2 + '/' + str(result) + '" target="_blank">Yes</a> - <span class="sale">' + str('{:.2f}'.format(plat2Price)) + '</span>'
            else:
                return '<a href="https://www.oculus.com/experiences/' + plat2 + '/' + str(result) + '" target="_blank">Yes</a>'
        except:
            return '<a href="https://www.oculus.com/experiences/' + plat2 + '/' + str(result) + '" target="_blank">Yes</a>'
        
    else:
        return ''
   
def set_crossbuy(appID):    
    sql = 'UPDATE app_details SET crossbuy = 1 WHERE appID = "' + str(appID) + '"'
    cur = conn.cursor()
    cur.execute(sql)
    
    sql = 'UPDATE app_details_history SET crossbuy = 1 WHERE appID = "' + str(appID) + '"'
    cur = conn.cursor()
    cur.execute(sql)
    
def current_price(platform, region, appID):    
    sql = 'SELECT price FROM app_index WHERE appID = "' + str(appID) + '" AND region = "' + region + '" LIMIT 1'
    
    cur = conn.cursor()
    cur.execute(sql)
    result = cur.fetchone()
    
    try:
        return result[0]
    except:
        return 9999;

def format_price(price, currency, sale):
    if price == 'TBD':
        return '<span>TBD</span>'
    elif price == 0:
        return '<span>Free</span>'
    else:    
        return '<span>' + currency + str('{:.2f}'.format(price)) + '</span>'
          
def format_price_raw(price):
    if price == 'TBD':
        return '0'
    else:
        return str(price)
    
def format_price_max(region,platform,questcompat):
    cur = conn.cursor()
    
    if platform == 'lab':
        cur.execute("SELECT price FROM app_details INNER JOIN app_index ON app_details.appid = app_index.appid LEFT OUTER JOIN app_categories ON app_index.appid = app_categories.appid WHERE released = 1 AND app_index.region = '" + region + "' AND app_index.platform = '" + platform + "' AND price != 'TBD' AND app_details.appid NOT IN (SELECT appid FROM hidden) GROUP BY app_index.appid ORDER BY CAST(price AS integer) DESC LIMIT 1")
    elif questcompat == False:
        cur.execute("SELECT price FROM app_details INNER JOIN app_index ON app_details.appid = app_index.appid LEFT OUTER JOIN app_categories ON app_index.appid = app_categories.appid WHERE released = 1 AND app_index.region = '" + region + "' AND app_index.platform = '" + platform + "' AND price != 'TBD' AND app_index.title NOT LIKE '% Demo' AND app_details.appid NOT IN (SELECT appid FROM hidden) GROUP BY app_index.appid ORDER BY CAST(price AS integer) DESC LIMIT 1")
    elif questcompat == True:
        cur.execute("SELECT price FROM app_details INNER JOIN app_index ON app_details.appid = app_index.appid LEFT OUTER JOIN app_categories ON app_index.appid = app_categories.appid WHERE released = 1 AND app_index.region = '" + region + "' AND app_index.platform = '" + platform + "' AND price != 'TBD' AND app_index.title NOT LIKE '% Demo' AND app_details.appid IN (SELECT appid FROM questcompat) AND app_details.appid NOT IN (SELECT appid FROM hidden) GROUP BY app_index.appid ORDER BY CAST(price AS integer) DESC LIMIT 1")
    
    return str(math.ceil(cur.fetchone()[0] / 10) * 10)  
    
def format_discount_raw(discount):
    if discount > 1:
        return str(discount)
    else:
        return '0'
    
def format_discount(discount):
    if discount > 1:
        return '<span class="sale">-' + str(discount) + '%</span>'  
    else:
        return '<span></span>'
    
def format_title(title, released, storelink, appID, rdate):
    
    sql = 'SELECT shortname FROM app_shortname WHERE appID = "' + str(appID) + '"'
    cur = conn.cursor()
    cur.execute(sql)
    
    result_row = cur.fetchone()
    
    if result_row:
        title = result_row[0]
    
    return '<a href="' + storelink + '" target="_blank"><img class="lozad" height="35" width="62" alt="' + title + '" data-src="/oculus/images/' + str(appID) + '.jpg"><span>' + title + '</span></a>'

def format_title_json(title, released, storelink, appID, rdate):
    
    sql = 'SELECT shortname FROM app_shortname WHERE appID = "' + str(appID) + '"'
    cur = conn.cursor()
    cur.execute(sql)
    
    result_row = cur.fetchone()
    
    if result_row:
        title = result_row[0]
    
    return '<a href="' + storelink + '" target="_blank"><img height="35" width="62" alt="' + title + '" src="/oculus/images/' + str(appID) + '.jpg"><span>' + title + '</span></a>'
    
def format_genres(genres):
    genreSplit = genres.split(', ')
    
    if len(genreSplit) > 1:
        return genreSplit[0] + ', ' + genreSplit[1]
    else:
        return genres
    
def format_popularity(popularity, released, rdate):
    if released == 0:
        #return '<i class="upcoming"><span>Upcoming</span></i>'
        return '<i class="newrelease"><span>New</span></i>'
    else:
        rdateFormat = datetime.datetime.strptime(rdate, '%Y-%m-%d').date()
        todayFormat = datetime.datetime.now().date()
        newFormat   = (rdateFormat + datetime.timedelta(days=14))
        
        if todayFormat <= newFormat:
            return '<i class="newrelease"><span>New</span></i>'
        else:
            return popularity
    
def format_popularity_raw(popularity, released, rdate):
    if released == 0:
        return '1000'
    else:
        rdateFormat = datetime.datetime.strptime(rdate, '%Y-%m-%d').date()
        todayFormat = datetime.datetime.now().date()
        newFormat   = (rdateFormat + datetime.timedelta(days=14))
        
        if todayFormat <= newFormat:
            return '900'
        else:
            return popularity
        
def format_score(appID, score):
    
    if os.path.isfile('/var/www/html/quest/history/' + str(appID) + '.html') == True:
        return '<a href="https://vrdb.app/quest/history/' + str(appID) + '.html">' + str(score) + '</a>'
    
    else:
        return str(score)
        
def category_select(platform, region):
    
    sql = 'SELECT category, COUNT(*) FROM app_categories WHERE platform = "' + platform + '" AND (region = "' + region + '" OR region IS NULL) AND appid IN (SELECT appid FROM app_index WHERE platform = "' + platform + '" AND region = "' + region + '" AND app_index.title NOT LIKE "% Demo" AND app_index.appid NOT IN (SELECT appid FROM hidden)) GROUP BY category ORDER BY category'
    
    cur = conn.cursor()
    cur.execute(sql)
    
    rows = cur.fetchall()
    
    html = '<select id="section-select">'
    
    html += '<option value="">All sections</option>'
    
    for row in rows:
        if row[0] not in ["Cross-Buy Apps","On Sale Now","On Sale Now + Cheaper Cross-Buy","Mode - Sitting","Mode - Standing","Mode - Roomscale","Players - Singleplayer","Players - Co-op","Players - Multiplayer"]:
            html += '<option value="' + row[0] + '">' + row[0] + ' (' + str(row[1]) + ')</option>'
        
    html += '</select>'
        
    return html

def filter_select(platform, region):
    
    sql = 'SELECT category, COUNT(DISTINCT appid) FROM app_categories WHERE platform = "' + platform + '" AND (region = "' + region + '" OR region IS NULL) AND appid IN (SELECT appid FROM app_index WHERE platform = "' + platform + '" AND region = "' + region + '" AND app_index.title NOT LIKE "% Demo" AND app_index.appid NOT IN (SELECT appid FROM hidden)) GROUP BY category ORDER BY category'
    
    cur = conn.cursor()
    cur.execute(sql)
    
    rows = cur.fetchall()
    
    html = '<select id="filter-select">'
    
    html += '<option value="">No filter</option>'
    
    for row in rows:
        if row[0] in ["Cross-Buy Apps","On Sale Now","On Sale Now + Cheaper Cross-Buy","Mode - Sitting","Mode - Standing","Mode - Roomscale","Players - Singleplayer","Players - Co-op","Players - Multiplayer"]:
            html += '<option value="' + row[0] + '">' + row[0] + ' (' + str(row[1]) + ')</option>'
            
    if 'On Sale Now + Cheaper Cross-Buy' not in html and platform == 'quest':
        html += '<option value="On Sale Now + Cheaper Cross-Buy">On Sale Now + Cheaper Cross-Buy (0)</option>'

    elif 'On Sale Now + Cheaper Cross-Buy' not in html and platform == 'rift':
        html += '<option value="On Sale Now">On Sale Now (0)</option>'
        
    html += '</select>'
        
    return html

def genre_organizer(platform):
    
    sql = 'DELETE FROM app_genres WHERE platform = "' + platform + '"'
    cur = conn.cursor()
    cur.execute(sql)
    conn.commit()
    
    sql = 'SELECT DISTINCT appid, genres FROM app_details WHERE appid IN (SELECT appid FROM app_index WHERE platform = "' + platform + '")'
    cur = conn.cursor()
    cur.execute(sql)
    
    rows = cur.fetchall()
    
    for row in rows:
        appID = row[0]
        genres = row[1].split(',')
        
        for genre in genres:
            gen = [platform, appID, genre.strip()]
            sql = 'INSERT OR REPLACE INTO app_genres(platform,appid,genre) VALUES(?,?,?)'
            cur = conn.cursor()
            cur.execute(sql, gen)
        
    conn.commit()
    
def genre_select(platform, region):
    
    sql = 'SELECT genre, COUNT(*) FROM app_genres WHERE platform = "' + platform + '" AND appid IN (SELECT appid FROM app_index WHERE platform = "' + platform + '" AND region = "' + region + '") GROUP BY genre ORDER BY genre'
    
    cur = conn.cursor()
    cur.execute(sql)
    
    rows = cur.fetchall()
    
    html = '<select id="genre-select">'
    
    html += '<option value="">All genres</option>'
    
    for row in rows:
        if row[0] != "":
            html += '<option value="' + row[0] + '">' + row[0] + ' (' + str(row[1]) + ')</option>'
        
    html += '</select>'
        
    return html
        
def processing_check(conn, region):
    filedate = os.path.getmtime(inputDir + region + '.inputQuest.json')
    
    sql = 'SELECT filedate FROM processing WHERE region = "' + region + '" AND platform = "oculus" ORDER BY pdate DESC LIMIT 1'
    cur = conn.cursor()
    cur.execute(sql)
    
    try:
        result = cur.fetchone()[0]
        
        if(result == filedate):
            return False;
        else:
            return True;
    except:
        return True;
    
def processing_add(conn, region):
    filedate = os.path.getmtime(inputDir + region + '.inputQuest.json')
    procRow = [str(datetime.datetime.now()), region, filedate]
    
    sql = 'INSERT INTO processing(platform,pdate,region,filedate) VALUES("oculus",?,?,?) '
    cur = conn.cursor()
    cur.execute(sql, procRow)
    conn.commit()
    
def copy_images(platform):
    images = os.listdir(mainDir + '/JSON/Oculus/Images/')
    
    for image in images:
        try:
            copyfile(mainDir + '/JSON/Oculus/Images/' + image, imageDir + image)
        except:
            pass
        
def create_path(dir1, dir2):
    return mainDir + slash + dir1 + slash + dir2 + slash

def release_date_fixer(appID):
    sql = 'SELECT rdate FROM app_details_history WHERE appid = ' + appID + ' AND rdate != "TBD" ORDER BY hdate DESC LIMIT 1'
    cur = conn.cursor()
    cur.execute(sql)
    
    if appID == '2941596479246841': return '2020-04-20' # St. Jude Hall of Heroes
    if appID == '2444236425640550': return '2020-06-19'
    if appID == '2009355295817444': return '2020-03-26'
    if appID == '2532035600194083': return '2020-08-28'
    if appID == '2555369754551731': return '2020-08-31'
    
    if appID == '3285668754893704': return '2021-04-15' # Carly and the Reaperman
    if appID == '2202354219893697': return '2020-09-10' # Holopoint
    if appID == '2173576192720129': return '2019-12-19' # TRIPP
    
    try:
        result = cur.fetchone()[0]
        return result;
    except:
        return False;

# Store functions
    
def processSection(conn, region, platform, jsonFile):
    
    inputData = open(jsonFile)
    
    segments = inputData.readlines()
    
    for segment in segments:

        data = json.loads(segment)
        
        items = data['data']['node']['all_items']['edges']
        
        print('Processing ' + str(len(items)) + ' store entries - Indexing...')
        
        for item in items:
            
            appID = item['node']['id']
            titleText = item['node']['display_name']
            priceText = ''
            
            # Price logic - Sales handling
                   
            price = item['node']['current_offer']['price']['formatted']
            
            if price != None:
                priceText = price.replace('€', '').replace('US$', '').replace('CA$', '').replace('A$', '').replace('$', '').replace('£', '').replace('Pre-Order ','')
    
                discount = item['node']['current_offer']['promo_benefit']
                
                if discount is not None:
                    sale = item['node']['current_offer']['promo_benefit'].replace('-','').replace('%','')
                    
                else:
                    sale = 0
                    
            if priceText == 'Free' or priceText == '0':
                priceText = '0.00'
                
            # End price logic
            
            if appID != None and priceText != '' and titleText != None:
                
                unid = region + '-' + appID
                
                appIndex = [region,unid,appID,titleText,priceText,sale]
                update_app_index(conn, platform, appIndex)
                
                currency = "EUR"
                
                if region == "us":
                    currency = "USD"
                    
                appPriceDB = [appID, str(datetime.datetime.now()), priceText, currency, sale]
                update_app_price(conn, appPriceDB)
                
    print(jsonFile.replace(inputDir, '') + ' has been indexed')
            
    conn.commit()
    
    
def processCrossbuy(conn, region, platform, jsonFile):
    
    with open(jsonFile) as json_file:
        data = json.load(json_file)
    
    items = data['data']['node']['all_items']['edges']
    
    print('Processing ' + str(len(items)) + ' Cross-Buy entries - Applying...')
    
    for item in items:
        
        appID = item['node']['id']
        
        if len(appID) > 10:
            set_crossbuy(appID)
            
            
    print(jsonFile.replace(inputDir, '') + ' has been applied to the existing app index')
            
    conn.commit()
    update_crossbuy(conn)
    

def processApps(conn, region, platform, appSourceDir, applab = False):
    #apps = os.listdir(appSourceDir)
    
    apps = glob.glob(appSourceDir + platform + '.' + region + '.*.json')
    
    count = 0
    countMax = len(apps)
    
    for app in apps:
        
        appID = app.replace('.json', '').replace(appSourceDir + platform + '.' + region + '.', '')
        
        titleText  = ''
        ratingText = '0'
        scoreText  = 'N/A'
        genreText  = 'TBD'
        rdateText  = 'TBD'
        popText    = '0'
        cbuyText   = '0'
        gsizeText  = 'TBD'
        versionNr  = ''
        versionTxt = ''
        released   = 1
        modesText  = ''
        gamemodesText  = ''
        
        if applab == True:
            storeLink  = 'https://www.oculus.com/experiences/quest/' + appID + '/'
        else:
            storeLink  = 'https://www.oculus.com/experiences/' + platform + '/' + appID + '/'
            
        with open(app) as json_file:
            data = json.load(json_file)
            
        count += 1
            
        data = data['data']['node']
        concept = data['is_concept']
        
        titleText = data['display_name']
        
        ratingNode = data['quality_rating_histogram_aggregate_all']
        ratingCount = 0
        
        for star in ratingNode:            
            ratingCount = ratingCount + star['count']
            
        ratingText = str(ratingCount)        
        
        rdate = data['release_date']
        if rdate != None:
            rdateText = datetime.datetime.fromtimestamp(rdate).strftime('%Y-%m-%d')
        else:
            if appID == '2941596479246841': # St. Jude Hall of Heroes fix
                released = 1
            else:
                released = 0
            
        if release_date_fixer(appID) != False:
            rdateText = release_date_fixer(appID)
            
        try:
            offertype = data['current_offer']['offer_type']
            
            if offertype == 'APPSTORE_COMINGSOON_OFFER' or offertype == 'APPSTORE_PREORDER_OFFER':
                released = 0
        except:
            pass

        # App Lab entries have no section
            
        if applab == True and concept == True:
            
            sale = 0
            
            try:
                price = data['current_offer']['price']['formatted']
                
                if price != None:
                    priceText = price.replace('€', '').replace('US$', '').replace('CA$', '').replace('A$', '').replace('$', '').replace('£', '').replace('Pre-Order ','')
                    
                    if priceText != 'Free':
                        discount = data['current_offer']['promo_benefit']
                        if discount is not None:
                            sale = data['current_offer']['promo_benefit'].replace('-','').replace('%','')
                    else:
                        sale = 0
                        
                if priceText == 'Free':
                    priceText = '0.00'
            except:
                priceText = '0.00'
                
            currency = "EUR"
            
            if region == "us":
                currency = "USD"

            appPriceDB = [appID, str(datetime.datetime.now()), priceText, currency, sale]
            update_app_price(conn, appPriceDB)
                
        
        # Resume normal functionality here
#            
#        preorderDiv = soup.find('div', {'class': 'app-purchase__preorder-detail'})
#        if preorderDiv != None:
#            released = 0
#            
        genres = data['genre_names']
        genreText = ', '.join(genres)
        
        try:
            gsizeText = format_bytes(int(data['latest_supported_binary']['total_installed_space']))
        except:
            pass
        
        try:
            versionNr = data['latest_supported_binary']['version']            
            versionTxt = data['latest_supported_binary']['change_log']
        except:
            pass

        gamemodes = data['user_interaction_mode_names']
        gamemodesText = ', '.join(gamemodes) 
        
        modes = data['supported_player_modes']
        modesText = ', '.join(modes)
        modesText = modesText.replace('SITTING', 'Sitting').replace('STANDING', 'Standing').replace('ROOM_SCALE', 'Roomscale')
                
        if ratingText != '' and rdateText != 'TBD':
            if datetime.datetime.strptime(rdateText, '%Y-%m-%d').date() == datetime.datetime.today().date():
                popText = ratingText
            else: 
                popText = str(round(int(ratingText) / int((datetime.datetime.today() - datetime.datetime.strptime(rdateText, '%Y-%m-%d')).days)))
                
        scoreText = str(round(data['quality_rating_aggregate'] * 20))
        
        
        if titleText != '':
            print(str(count).zfill(len(str(countMax))) + "/" + str(countMax) + " - Processing store entry " + titleText)
            
            appDetails = [appID,titleText,ratingText,scoreText,popText,genreText,cbuyText,rdateText,gsizeText,storeLink,released,modesText,gamemodesText]
            update_app_details(conn, appDetails)
        
            appHistoryDB = [str(datetime.datetime.now()),appID,titleText,ratingText,scoreText,popText,genreText,cbuyText,rdateText,gsizeText,storeLink,released,modesText,gamemodesText]
            update_app_history(conn, appHistoryDB)
            
            if applab == True and priceText != '' and concept == True:
                unid = region + '-' + appID
                
                appIndex = [region,unid,appID,titleText,priceText,sale]
                update_app_index(conn, platform, appIndex)
            
            if versionNr != '':
                versionDB = [appID + '-' + versionNr, str(datetime.datetime.now()), appID, versionNr, versionTxt]
                update_app_versions(conn, versionDB)
            
        else:
            print(str(count).zfill(len(str(countMax))) + "/" + str(countMax) + " - Skipping badly crawled store entry " + appID)
    
    conn.commit()
    copy_images(platform)
    genre_organizer(platform)

    
    
def processCategories(conn, region, platform, catSourceDir):
    
    sql = 'DELETE FROM app_categories WHERE platform = "' + platform + '" AND region = "' + region + '"'
    cur = conn.cursor()
    cur.execute(sql)
    conn.commit()
    
    if platform in ('quest', 'rift'):
        categories = glob.glob(catSourceDir + platform + '.' + region + '.*.json')
               
        for category in categories:
            
            try:
                catName = category.replace('.json', '').replace(catSourceDir + platform + '.' + region + '.', '')
                
                if 'Coming Soon' not in catName and 'Sale' not in catName and 'New Releases' not in catName:
                    
                    with open(category) as json_file:
                        data = json.load(json_file)
                        
                    items = data['data']['node']['all_items']['edges']
                    
                    print('Processing ' + str(len(items)) + ' entries from category ' + catName)
                    
                    for item in items:
                        
                        appID = item['node']['id']
                        
                        titleText = item['node']['display_name']
                                
                        if len(appID) > 10 and titleText != None:
                            cat = [platform, region, appID, catName]
                            sql = 'INSERT OR REPLACE INTO app_categories(platform,region,appid,category) VALUES(?,?,?,?)'
                            cur = conn.cursor()
                            cur.execute(sql, cat)
            except:
                pass
                        
        conn.commit()
                
    # Cross-Buy category
    
    if platform in ('quest', 'rift'):
        if platform == 'quest':
            sql = 'SELECT appIDquest FROM crossbuy'
            
        else:
            sql = 'SELECT appIDrift FROM crossbuy'
            
        cur = conn.cursor()
        cur.execute(sql)
        
        rows = cur.fetchall()
        
        for row in rows:
            cat = [platform, region, row[0], 'Cross-Buy Apps']
            sql = 'INSERT OR REPLACE INTO app_categories(platform,region,appid,category) VALUES(?,?,?,?)'
            cur = conn.cursor()
            cur.execute(sql, cat)
            
    # Sitting, Standing, Roomscale
    
    if platform in ('quest', 'rift', 'lab'):
        sql = 'SELECT appid, modes FROM app_details WHERE appid IN (SELECT appid FROM app_index WHERE platform = "' + platform + '") AND LENGTH(modes) > 1' 
        
        cur = conn.cursor()
        cur.execute(sql)
        
        rows = cur.fetchall()
        
        for row in rows:
            
            if 'Sitting' in row[1]:
                cat = [platform, region, row[0], 'Mode - Sitting']
                sql = 'INSERT OR REPLACE INTO app_categories(platform,region,appid,category) VALUES(?,?,?,?)'
                cur = conn.cursor()
                cur.execute(sql, cat)
                
            if 'Standing' in row[1]:
                cat = [platform, region, row[0], 'Mode - Standing']
                sql = 'INSERT OR REPLACE INTO app_categories(platform,region,appid,category) VALUES(?,?,?,?)'
                cur = conn.cursor()
                cur.execute(sql, cat)
                
            if 'Roomscale' in row[1]:
                cat = [platform, region, row[0], 'Mode - Roomscale']
                sql = 'INSERT OR REPLACE INTO app_categories(platform,region,appid,category) VALUES(?,?,?,?)'
                cur = conn.cursor()
                cur.execute(sql, cat)
                
    # Singleplayer, Multiplayer, etc
    
    if platform in ('quest', 'rift', 'lab'):
        sql = 'SELECT appid, gamemodes FROM app_details WHERE appid IN (SELECT appid FROM app_index WHERE platform = "' + platform + '") AND LENGTH(gamemodes) > 1' 
        
        cur = conn.cursor()
        cur.execute(sql)
        
        rows = cur.fetchall()
        
        for row in rows:
            
            if 'Single User' in row[1]:
                cat = [platform, region, row[0], 'Players - Singleplayer']
                sql = 'INSERT OR REPLACE INTO app_categories(platform,region,appid,category) VALUES(?,?,?,?)'
                cur = conn.cursor()
                cur.execute(sql, cat)
                
            if 'Multiplayer' in row[1]:
                cat = [platform, region, row[0], 'Players - Multiplayer']
                sql = 'INSERT OR REPLACE INTO app_categories(platform,region,appid,category) VALUES(?,?,?,?)'
                cur = conn.cursor()
                cur.execute(sql, cat)
                
            if 'Co-op' in row[1]:
                cat = [platform, region, row[0], 'Players - Co-op']
                sql = 'INSERT OR REPLACE INTO app_categories(platform,region,appid,category) VALUES(?,?,?,?)'
                cur = conn.cursor()
                cur.execute(sql, cat)
                
    conn.commit()

def saleCategories(conn, platform, region):
    
    # On Sale Now + Cheaper Cross-Buy
    
    if platform in ('quest'):
        sql = 'SELECT DISTINCT appid FROM app_index WHERE platform = "quest" AND (sale > 0 AND region = "' + region + '" AND price != 0) OR appid IN (SELECT appIDquest FROM crossbuy AS cb INNER JOIN app_index AS ai1 ON cb.appIDquest = ai1.appid INNER JOIN app_index AS ai2 ON cb.appIDrift = ai2.appid WHERE ai1.region = "' + region + '" AND ai2.region = "' + region + '" AND ai1.price > ai2.price)'
            
        cur = conn.cursor()
        cur.execute(sql)
        
        rows = cur.fetchall()
        
        for row in rows:
            
            cat = [platform, region, row[0], 'On Sale Now + Cheaper Cross-Buy']
            sql = 'INSERT OR REPLACE INTO app_categories(platform,region,appid,category) VALUES(?,?,?,?)'
            cur = conn.cursor()
            cur.execute(sql, cat)

    if platform in ('rift'):
        sql = 'SELECT DISTINCT appid FROM app_index WHERE platform = "rift" AND (sale > 0 AND region = "' + region + '" AND price != 0) OR appid IN (SELECT appIDrift FROM crossbuy AS cb INNER JOIN app_index AS ai1 ON cb.appIDrift = ai1.appid INNER JOIN app_index AS ai2 ON cb.appIDquest = ai2.appid WHERE ai1.region = "' + region + '" AND ai2.region = "' + region + '" AND ai1.price > ai2.price)'
            
        cur = conn.cursor()
        cur.execute(sql)
        
        rows = cur.fetchall()
        
        for row in rows:
            
            cat = [platform, region, row[0], 'On Sale Now + Cheaper Cross-Buy']
            sql = 'INSERT OR REPLACE INTO app_categories(platform,region,appid,category) VALUES(?,?,?,?)'
            cur = conn.cursor()
            cur.execute(sql, cat)
            
    conn.commit()
            
            
            
    
def dataToJSON(conn,region,platform):
    
    questcompat = False
    
    if platform == 'questcompat':
        platform = 'go'
        questcompat = True
    
    cur = conn.cursor()
    
    if platform == 'lab':
        cur.execute("SELECT DISTINCT app_index.appid,app_index.title,ratings,price,score,popularity,genres,crossbuy,rdate,gamesize,storelink,released,sale,group_concat(category) FROM app_details INNER JOIN app_index ON app_details.appid = app_index.appid LEFT OUTER JOIN app_categories ON app_index.appid = app_categories.appid WHERE app_index.appid NOT IN (SELECT appid FROM app_index WHERE platform = 'quest') AND app_index.region = '" + region + "' AND app_index.platform = '" + platform + "' AND app_details.appid NOT IN (SELECT appid FROM hidden) AND (app_categories.region = '" + region + "' OR app_categories.region IS NULL) GROUP BY app_index.appid ORDER BY app_index.title")
    elif questcompat == False:
        cur.execute("SELECT DISTINCT app_index.appid,app_index.title,ratings,price,score,popularity,genres,crossbuy,rdate,gamesize,storelink,released,sale,group_concat(category) FROM app_details INNER JOIN app_index ON app_details.appid = app_index.appid LEFT OUTER JOIN app_categories ON app_index.appid = app_categories.appid WHERE released = 1 AND app_index.region = '" + region + "' AND app_index.platform = '" + platform + "' AND app_index.title NOT LIKE '% Demo' AND app_details.appid NOT IN (SELECT appid FROM hidden) AND (app_categories.region = '" + region + "' OR app_categories.region IS NULL) GROUP BY app_index.appid ORDER BY app_index.title")
    elif questcompat == True:
        cur.execute("SELECT DISTINCT app_index.appid,app_index.title,ratings,price,score,popularity,genres,crossbuy,rdate,gamesize,storelink,released,sale,group_concat(category) FROM app_details INNER JOIN app_index ON app_details.appid = app_index.appid LEFT OUTER JOIN app_categories ON app_index.appid = app_categories.appid WHERE released = 1 AND app_index.region = '" + region + "' AND app_index.platform = '" + platform + "' AND app_index.title NOT LIKE '% Demo' AND app_details.appid IN (SELECT appid FROM questcompat) AND app_details.appid NOT IN (SELECT appid FROM hidden) AND (app_categories.region = '" + region + "' OR app_categories.region IS NULL) GROUP BY app_index.appid ORDER BY app_index.title")
    
    print('Preparing JSON dataset export')
    
    cbclass = ''
    
    if platform == 'go' or platform == 'lab':
        cbclass = 'never'
    
    rows = cur.fetchall()
    
    json_output = []
    
    for row in rows:
        
        json_row = {}
        
        currency = "€"
        
        if region == "us":
            currency = "$"
            
        if region == "ca":
            currency = "CA$"
            
        if region == "au":
            currency = "A$"
            
        if region == "gb":
            currency = "£"
            
        rdate      = row[8]
        gsize      = row[9]
        released   = row[11]

        if platform == 'lab' and row[0] == 4990640791007528: # Crumb missing release date
            rdate = '2021-03-20'
            released = 1
            
        appID      = row[0]
        title      = format_title_json(row[1], released, row[10], row[0], rdate)
        ratings    = str(row[2])
        priceRaw   = format_price_raw(current_price(platform, region, appID))
        price      = format_price(current_price(platform, region, appID), currency, row[12])
        score      = format_score(row[0], row[4])
        popularity = format_popularity(str(row[5]), released, rdate)
        popularity_raw = format_popularity_raw(str(row[5]), released, rdate)
        genres     = format_genres(row[6])
        sections   = str(row[13] or '')
        genres_raw = str(row[6] or '')
        filters    = str(row[13] or '')
        
        if platform != 'go' and platform != 'lab':
            crossbuy = link_crossbuy(conn, row[7], appID, region, platform)
        else:
            crossbuy = ''
            
        #html += '<thead><tr><th class="all popularity"><span>Popularity</span></th><th class="all">Title</th><th></th><th>Score</th><th>Ratings</th><th>Price (Raw)</th><th>Price</th><th>Discount (Raw)</th><th>Discount</th><th class="' + cbclass + '">Cross-Buy</th><th>Release Date</th><th>Genres</th><th>Size</th></th><th>Popularity (Raw)</th><th>Sections</th><th>Genres (Raw)</th><th>Sections (Duplicate)</th></tr></thead>\n'
        
        json_row = [popularity,title,'',score,ratings,priceRaw,price,format_discount_raw(row[12]),format_discount(row[12]),crossbuy,rdate,genres,gsize,popularity_raw,sections,genres_raw,filters]
        
        json_output.append(json_row)

    if platform == 'lab':
        filename = slash + '/quest/lab/' + slash + 'index_' + region + '.json'
    elif questcompat == False:
        filename = slash + platform + slash + 'index_' + region + '.json'
    else:
        filename = slash + '/quest/compatible/' + slash + 'index_' + region + '.json'
        
    json_output_final = {}
    json_output_final["data"] = json_output
    
    file = open(htmlDir + filename, 'w', encoding='utf8')
    file.write(json.dumps(json_output_final, ensure_ascii=False))
    file.close()
    
    print('JSON dataset succesfully generated - ' + str(len(rows)) + ' titles')
    
    
# Web functions
    
def dataToTable(conn,region,platform):
    
    dataToJSON(conn,region,platform)
    
    questcompat = False
    
    if platform == 'questcompat':
        platform = 'go'
        questcompat = True
    
    cur = conn.cursor()
    
    print('Converting data to HTML table')
    
    euactive = ''
    usactive = ''
    
    if region == 'eu':
        euactive = 'active'
    if region == 'us':
        usactive = 'active'

    if platform == 'lab':
        title = 'Oculus Quest - ' + region.upper() + ' App Lab Overview'
        
        titletop = 'Oculus Quest'
        titlesub = region.upper() + ' App Lab Overview'    
    elif questcompat == True:
        title = 'Oculus Go (Quest 1 Compatible) Store Overview'
        
        titletop = 'Oculus Go (Quest 1 Compatible)'
        titlesub = region.upper() + ' Store Overview'
    else:
        title = 'Oculus ' + platform.capitalize() + ' - ' + region.upper() + ' Store Overview'
        
        titletop = 'Oculus ' + platform.capitalize()
        titlesub = region.upper() + ' Store Overview'
    
    addon = '<p class="addon">'
    addon += '<a class="button ' + usactive + '" href="index_us.html">US</a> '
    addon += '<a class="button ' + euactive + '" href="index_eu.html">EU</a> '
    addon += '</p>'

    if platform in ('go','questcompat'):
        currentdate = '2019-11-26 (ON HOLD)'    
    else:
        currentdate = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")[:-1] + '0 CET'
    
    html = '''
        <!doctype html>
        <html lang="en">
        <head>
          <meta charset="utf-8">
        
          <title>''' + title + '''</title>
          <meta name="description" content="''' + title + '''">
          <meta name="author" content="Gryphe">
          <meta name="viewport" content="width=device-width, initial-scale=1">
          
          <link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">
          <link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png">
          <link rel="icon" type="image/png" sizes="16x16" href="/favicon-16x16.png">
          <link rel="manifest" href="/site.webmanifest">
          <meta name="msapplication-TileColor" content="#da532c">
          <meta name="theme-color" content="#ffffff">
          
          <script type="text/javascript" src="/oculus/js/jquery-3.4.1.min.js"></script>
          <script type="text/javascript" src="/oculus/js/datatables.min.js"></script>
          <script type="text/javascript" src="/oculus/js/stellarnav.min.js"></script>
          <script type="text/javascript" src="/oculus/js/oculus.js?uuid=''' + str(uuid.uuid4()) + '''"></script>
          
          <script async src="https://www.googletagmanager.com/gtag/js?id=UA-154490678-1"></script>
          <script>
            window.dataLayer = window.dataLayer || [];
            function gtag(){dataLayer.push(arguments);}
            gtag('js', new Date());  
            gtag('config', 'UA-154490678-1', { 'optimize_id': 'GTM-NW2BFQH'});
          </script>
          
          <link rel="stylesheet" type="text/css" href="/oculus/js/datatables.min.css"/> 
          <link rel="stylesheet" type="text/css" href="/oculus/css/stellarnav.min.css"/> 
          <link rel="stylesheet" type="text/css" href="/oculus/css/style.css?uuid=''' + str(uuid.uuid4()) + '''"/>
          
          <link rel="icon" href="/favicon.ico" type="image/x-icon"/>
          <link rel="shortcut icon" href="/favicon.ico" type="image/x-icon"/>
        
        </head>
        
        <body>'''
        
    platquest  = ''
    platrift   = ''
    platgo     = ''
    platcompat = ''
    platlab = ''
    
    if platform == 'quest':
        platquest = 'active'
    elif platform == 'rift':
        platrift = 'active'
    elif questcompat == True:
        platquest = 'active'
        platcompat = 'active'
    elif platform == 'go':
        platgo = 'active'
    elif platform == 'lab':
        platlab = 'active'
        
    html += '<div class="stellarnav"><ul>'
    html += '<li><a class="" target="_top" href="/">Home</a></li>'
    
    html += '<li><a class="' + platquest + '" target="_top" href="/quest/">Quest</a>'
    html += '<ul><li><a class="' + platcompat + '" target="_top" href="/quest/compatible/">Q1 Compatible Go apps</a></li>'
    html += '<li><a target="_top" href="/quest/tracker.html">Version Tracker</a></li>'
    html += '</ul></li>'
    
    html += '<li><a class="' + platrift + '" target="_top" href="/rift/">Rift</a>'
    html += '<ul><li><a target="_top" href="/rift/tracker.html">Version Tracker</a></li>'
    html += '</ul></li>'    
    
    html += '<li><a class="' + platlab + '" target="_top" href="/quest/lab/">App Lab</a>'
    html += '<ul><li><a target="_top" href="/quest/lab/tracker.html">Version Tracker</a></li></ul></li>'
    html += '<li><a class="" target="_top" href="/steamvr/">SteamVR</a></li>'
    html += '</ul></div>'
    
    html += '<div class="main-body platform-' + platform + '">'
    
    html += '<div class="warning">All crawling activity is currently paused - Oculus appears to have temporarily blocked this domain from accessing their website.</div>'
    
    #html += '<h1>' + titletop + '</h1>'
    
    if platform == 'lab':
        html += '<h1><img src="/oculus/images/quest.png" height="40" width="183"></h1>'
    elif questcompat == True:
        html += '<h1><span class="subtitle">(Quest 1 Compatible)</span><img src="/oculus/images/' + platform + '.png" height="40" width="183"></h1>'
    else:
        html += '<h1><img src="/oculus/images/' + platform + '.png" height="40" width="183"></h1>'
    
    html += '<h2>' + titlesub + '</h2>'
    html += addon
    html += '<p><b>Last updated on:</b> ' + currentdate + '</p>'
    html += '<p><b>How is popularity calculated?</b> New (last 14 days) releases are listed first, followed by released apps and the number of ratings they receive every day. Upcoming releases can be found on the front page.</p>'
    #html += '<p><b>NOTE:</b> Due to recent Oculus website changes there is currently a noticable delay in update times. New titles may take a while to appear but prices and discounts for existing titles will continue to update.</p>'
    
    if platform == 'quest':
        html += '<p><b>NEW: </b>You can now view historical statistics for Quest apps by clicking on the score. Apps need to be at least one month old before these are generated.'
    
    if (platform == 'go') and questcompat == False:
        html += '<p class="addon"><a class="button" href="/quest/compatible/">Q1 Compatible Go apps</a></p>'
    
    html += '<div class="filters">'
    html += '<div class="filter"><label class="filter-text">Score ≥ <span id="scorevalue">0</span>%</label><input type="range" min="0" max="95" value="0" step="5" id="minscore"></div>'
    
    if platform != 'go':
        html += '<div class="filter"><label class="filter-text">Ratings ≥ <span id="ratingvalue">0</span></label><input type="range" min="0" max="500" value="0" step="10" id="minratings"></div>'
    else:
        html += '<div class="filter"><label class="filter-text">Ratings ≥ <span id="ratingvalue">0</span></label><input type="range" min="0" max="5000" value="0" step="100" id="minratings"></div>'
        
    html += '<div class="filter"><label class="filter-text">Price ≤ <span id="pricevalue">' + format_price_max(region,platform,questcompat) + '</span></label><input type="range" min="0" max="' + format_price_max(region,platform,questcompat) + '" value="' + format_price_max(region,platform,questcompat) + '" step="1" id="maxprice"></div>'
    
    if questcompat == False and platform != 'lab':
        
        if platform != 'go':
            html += '<div class="filter category"><label class="filter-text">Filter</label>' + filter_select(platform, region) + '</div>'
            
        html += '<div class="filter category"><label class="filter-text">Section</label>' + category_select(platform, region) + '</div>'
        html += '<div class="filter genre"><label class="filter-text">Genre</label>' + genre_select(platform, region) + '</div>'
        
    if platform == 'lab':
        
        html += '<div class="filter category"><label class="filter-text">Filter</label>' + filter_select(platform, region) + '</div>'
        html += '<div class="filter genre"><label class="filter-text">Genre</label>' + genre_select(platform, region) + '</div>'

    
    html += '</div>'
    
    cbclass = ''
    
    if platform == 'go' or platform == 'lab':
        cbclass = 'never'
    
    html += '<table id="oculuslist">\n'
    html += '<thead><tr><th class="all popularity"><span>Popularity</span></th><th class="all">Title</th><th></th><th>Score</th><th>Ratings</th><th>Price (Raw)</th><th>Price</th><th>Discount (Raw)</th><th>Discount</th><th class="' + cbclass + '">Cross-Buy</th><th>Release Date</th><th>Genres</th><th>Size</th></th><th>Popularity (Raw)</th><th>Sections</th><th>Genres (Raw)</th><th>Sections (Duplicate)</th></tr></thead>\n'
    html += '</table>\n'

    html += '</div></body></html>' 

    if platform == 'lab':
        filename = slash + 'quest' + slash + platform + slash + 'index_' + region + '.html'    
    elif questcompat == False:
        filename = slash + platform + slash + 'index_' + region + '.html'
    else:
        filename = slash + '/quest/compatible/' + slash + 'index_' + region + '.html'
    
    file = open(htmlDir + filename, 'wb')
    file.write(html.encode('utf-8'))
    file.close()
    
    #print('HTML table succesfully generated - ' + str(len(rows)) + ' titles')
    
    print('HTML table succesfully generated')
    
def regenerateAllTables(platforms = ['quest','rift','go','questcompat','lab']):
    
    #regions = ['us','eu']
    regions = ['us','eu']
    platforms = ['quest','rift','lab']
    #platforms = ['lab']
    #platforms = ['questcompat']
    #platforms = ['rift','quest','lab']
    #platforms = ['quest', 'lab']
    
    for reg in regions:
        for plat in platforms:
            dataToTable(conn,reg,plat)        


region = "eu"

if len(sys.argv) >= 2:
    if sys.argv[1] != None:
        region = sys.argv[1]

mainDir    = "/VRDB"
slash      = "/"
inputDir   = mainDir + "/JSON/Oculus/Sections/"
appDir     = mainDir + "/JSON/Oculus/Apps/"
catDir     = mainDir + "/JSON/Oculus/Categories/"
htmlDir    = "/var/www/html"
imageDir    = "/var/www/html/oculus/images/"

os.chdir(mainDir)

conn = create_connection("vrdb.db") 

#processCategories(conn, 'eu', 'lab', catDir)
#processCategories(conn, 'us', 'lab', catDir)
#dataToTable(conn, 'eu', 'lab')
#dataToTable(conn, 'us', 'lab')

#processCategories(conn, region, 'quest', catDir)
#processCategories(conn, region, 'rift', catDir)
#processCategories(conn, region, 'lab', catDir)

#processCrossbuy(conn, region, 'quest', inputDir + region + '.inputQuestCB.json')

#processApps(conn, 'us', 'quest', appDir)
#processApps(conn, 'eu', 'quest', appDir)
#regenerateAllTables()

#region = "us"

if processing_check(conn, region) == True:
    
    processApps(conn, region, 'lab', appDir, True)
    processApps(conn, region, 'quest', appDir)
    processApps(conn, region, 'rift', appDir)
    
    processCategories(conn, region, 'quest', catDir)
    processCategories(conn, region, 'rift', catDir)
    processCategories(conn, region, 'lab', catDir)
    
    processCrossbuy(conn, region, 'quest', inputDir + region + '.inputQuestCB.json')
    
    processSection(conn, region, 'quest', inputDir + region + '.inputQuest.json')
    processSection(conn, region, 'quest', inputDir + region + '.inputQuestSoon.json')
    
    processSection(conn, region, 'rift', inputDir + region + '.inputRift.json')
    processSection(conn, region, 'rift', inputDir + region + '.inputRiftSoon.json')
        
    saleCategories(conn, 'quest', region)
    saleCategories(conn, 'rift', region)
    
    dataToTable(conn, region, 'quest')
    dataToTable(conn, region, 'rift')
    dataToTable(conn, region, 'lab')
    
    # Database maintenance
    
    delete_app_price_duplicates(conn)
    delete_app_history_duplicates(conn)
    
    processing_add(conn, region)


conn.close()