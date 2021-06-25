import csv
import datetime
import json
import math
import os
import re
import requests
import sqlite3
import sys
import uuid

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


def create_connection(db_file):
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except Error as e:
        print(e)
 
    return None


def processing_check(conn, region):
    filedate = os.path.getmtime(pageDirCurrent + '1.html')
    
    sql = 'SELECT filedate FROM processing WHERE region = "' + region + '" AND platform = "steamvr" ORDER BY pdate DESC LIMIT 1'
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
    filedate = os.path.getmtime(pageDirCurrent + '1.html')
    procRow = [str(datetime.datetime.now()), region, filedate]
    
    sql = 'INSERT INTO processing(platform,pdate,region,filedate) VALUES("steamvr",?,?,?) '
    cur = conn.cursor()
    cur.execute(sql, procRow)
    conn.commit()
    

def copy_images():
    images = os.listdir(imageDir)
    
    for image in images:
        copyfile(imageDir + image, '/var/www/html/steamvr/images/' + image)
        

def format_price(price, discount, currency):
    if 'Free' in price:
        return '<span>Free</span>'
    else:    
        return '<span>' + currency + str(price) + '</span>'
          
def format_price_raw(price):
    if 'Free' in price:
        return "0"
    else:
        return str(price.replace('--','00'))
    
def format_price_max(region,):
    cur = conn.cursor()
    
    cur.execute("SELECT CAST(price AS integer) FROM steam_index LEFT OUTER JOIN steam_filters ON steam_index.appid = steam_filters.appid LEFT OUTER JOIN steam_genres ON steam_index.appid = steam_genres.appid LEFT OUTER JOIN steam_tags ON steam_index.appid = steam_tags.appid WHERE link LIKE '%/app/%' AND reviews != '' AND released = 1 AND region = '" + region + "' AND popularity >= 0 GROUP BY steam_index.appid ORDER BY CAST(price AS integer) DESC LIMIT 1")
    
    return str(math.ceil(cur.fetchone()[0] / 10) * 10)  
    
def format_discount_raw(discount):
    if discount != '':
        return discount.replace('-','').replace('%','')
    else:
        return discount
    
def format_discount(discount):
    if discount != '':
        return '<span class="sale">' + discount + '</span>'  
    else:
        return '<span>' + discount + '</span>'
    
def format_title(title, appID):
    
    storelink = 'https://store.steampowered.com/app/' + str(appID) + '/'
    
    return '<a href="' + storelink + '" target="_blank"><img height="35" width="93" alt="' + title + '" src="/steamvr/images/' + str(appID) + '.jpg"><span>' + title[0:50] + '</span></a>'


def format_vronly(value):
    if value == 1:
        return 'Yes'
    else:
        return ''
        

def update_steam_index(conn, app):
    sql = "INSERT OR REPLACE INTO steam_index(uniqid, region, appid, title, link, rdate, vronly, score, reviews, popularity, discount, price, currency, released) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
    cur = conn.cursor()
    cur.execute(sql, app)

def update_steam_index_history(conn, app):
    sql = "INSERT INTO steam_index_history(hdate,uniqid, region, appid, title, link, rdate, vronly, score, reviews, popularity, discount, price, currency, released) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
    cur = conn.cursor()
    cur.execute(sql, app)

def delete_steam_index_history_duplicates(conn):
    # NOTE TO SELF: This only leaves changes in the DB so we'll have to backtrack through history to find 'em!
    sql = 'DELETE FROM steam_index_history WHERE hdate NOT IN (SELECT MAX(hdate) FROM steam_index_history GROUP BY uniqid, region, appid, title, link, rdate, vronly, score, reviews, popularity, discount, price, currency, released)'
    cur = conn.cursor()
    cur.execute(sql)
    conn.commit()

def update_steam_ranking(conn, ranking, category):
    
    sql = "DELETE FROM steam_ranking WHERE category = '" + category + "'"
    cur = conn.cursor()
    cur.execute(sql)
    conn.commit()

    for rank in ranking:
        sql = "INSERT OR REPLACE INTO steam_ranking(category, rank, appid, title, link) VALUES(?,?,?,?,?)"
        cur = conn.cursor()
        cur.execute(sql, rank)
        
    conn.commit()
    
    
def update_steam_genre(conn, genre):
    
    sql = 'INSERT INTO steam_genres(appid,genre) VALUES(?,?)'
    cur = conn.cursor()
    cur.execute(sql, genre)


def update_steam_tag(conn, genre):
    
    sql = 'INSERT INTO steam_tags(appid,tag) VALUES(?,?)'
    cur = conn.cursor()
    cur.execute(sql, genre)
    
    
def category_select():
    
    sql = 'SELECT category, COUNT(*) FROM steam_filters GROUP BY category ORDER BY category'
    
    cur = conn.cursor()
    cur.execute(sql)
    
    rows = cur.fetchall()
    
    html = '<select id="section-select">'
    
    html += '<option value="">No filter</option>'
    
    for row in rows:
        html += '<option value="' + row[0] + '">' + row[0] + ' (' + str(row[1]) + ')</option>'
        
    html += '</select>'
        
    return html


def genre_select():
    
    sql = 'SELECT genre, COUNT(*) FROM steam_genres WHERE appid IN (SELECT appid FROM steam_index WHERE  link LIKE "%/app/%" AND reviews != "" AND released = 1 AND region = "us" AND popularity >= 0) GROUP BY genre ORDER BY genre'
    
    cur = conn.cursor()
    cur.execute(sql)
    
    rows = cur.fetchall()
    
    html = '<select id="genre-select">'
    
    html += '<option value="">All genres</option>'
    
    for row in rows:
        html += '<option value="' + row[0] + '">' + row[0] + ' (' + str(row[1]) + ')</option>'
        
    html += '</select>'
        
    return html


def tag_select():
    
    sql = 'SELECT tag, COUNT(*) FROM steam_tags WHERE appid IN (SELECT appid FROM steam_index WHERE  link LIKE "%/app/%" AND reviews != "" AND released = 1 AND region = "us" AND popularity >= 0) GROUP BY tag HAVING COUNT(*) > 10 ORDER BY tag'
    
    cur = conn.cursor()
    cur.execute(sql)
    
    rows = cur.fetchall()
    
    html = '<select id="tag-select">'
    
    html += '<option value="">All user tags</option>'
    
    for row in rows:
        
        if row[0] not in ["VR", "Free to Play", "Early Access"]:
            html += '<option value="' + row[0] + '">' + row[0] + ' (' + str(row[1]) + ')</option>'
        
    html += '</select>'
        
    return html


def process_custom_filters(conn):
    
    sql = 'DELETE FROM steam_filters'
    cur = conn.cursor()
    cur.execute(sql)
    conn.commit()
    
    # VR Only
    
    sql = 'SELECT appid FROM steam_index WHERE link LIKE "%/app/%" AND reviews != "" AND released = 1 AND region = "us" AND popularity >= 0 AND vronly = 1'
        
    cur = conn.cursor()
    cur.execute(sql)
    
    rows = cur.fetchall()
    
    for row in rows:
        cat = [row[0], 'VR Only']
        sql = 'INSERT OR REPLACE INTO steam_filters(appid,category) VALUES(?,?)'
        cur = conn.cursor()
        cur.execute(sql, cat)
        
    # VR Only
    
    sql = 'SELECT appid FROM steam_index WHERE link LIKE "%/app/%" AND reviews != "" AND released = 1 AND region = "us" AND popularity >= 0 AND vronly != 1'
        
    cur = conn.cursor()
    cur.execute(sql)
    
    rows = cur.fetchall()
    
    for row in rows:
        cat = [row[0], 'VR Supported']
        sql = 'INSERT OR REPLACE INTO steam_filters(appid,category) VALUES(?,?)'
        cur = conn.cursor()
        cur.execute(sql, cat)
            
    # On Sale Now

    sql = 'SELECT appid FROM steam_index WHERE link LIKE "%/app/%" AND reviews != "" AND released = 1 AND region = "us" AND popularity >= 0 AND discount != ""'
        
    cur = conn.cursor()
    cur.execute(sql)
    
    rows = cur.fetchall()
    
    for row in rows:
        cat = [row[0], 'On Sale Now']
        sql = 'INSERT OR REPLACE INTO steam_filters(appid,category) VALUES(?,?)'
        cur = conn.cursor()
        cur.execute(sql, cat)
                
    conn.commit()


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


def parse_vr_ranking(conn, inputDir, category):

    # Now start parsing the VR listing pages
    
    print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + 'Parsing ranking directory ' + inputDir)
    
    pages = os.listdir(inputDir)
    sort_nicely(pages)
    
    appCount  = 0
    pageCount = 1
    
    appRanks = []
    
    for page in pages:
        
        if pageCount <= 3:
            print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + 'Parsing VR ranking page ' + page)
            soup = BeautifulSoup(open(inputDir + page, 'rb'), 'html.parser')
            
            apps = soup.findAll('a', {'class', 'search_result_row'})
            
            for app in apps:
                
                try: 
                    appLink = app['href']
                    
                    appID = appLink.split('/')[4]                
                    title = extract_field(app, 'span', 'title', 'text')
                    
                    appCount  += 1
                    appRanked = [category, appCount, appID, title, appLink]
                    
                    appDuplicate = False
                    
                    for appRank in appRanks:
                        if appRank[3] == appRanked[3]:
                            appDuplicate = True
                            appCount -= 1
                            
                    if 'Demo' in appRanked[3]:
                        appDuplicate = True
                        appCount -= 1
                            
                    if appDuplicate == False:
                        appRanks.append(appRanked)

                except Exception as ex:
                    print('Error processing app.')
                    print(ex)
                
        pageCount += 1
        
    update_steam_ranking(conn, appRanks, category)
    
    print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + str(appCount) + ' games were succesfully ranked.')
    
    
def parse_vr_genres(conn):
    
    sql = 'SELECT DISTINCT appid FROM steam_genres'
    cur = conn.cursor()
    cur.execute(sql)
    appIDList = cur.fetchall()
    appIDList = [item for sublist in appIDList for item in sublist]
    
    print(datetime.datetime.now().strftime('%H:%M:%S') + ' - Scanning for new genres...')
    
    apps = os.listdir(appsDir)
    
    appCount  = 0
    
    print(appIDList)
    
    for app in apps:
        
        appID = int(app.replace('.html',''))
        
        if appID not in appIDList:
            
            if appCount % 10 == 0:
                print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + str(appCount) + ' apps processed.')
                conn.commit()
            
            try:
                soup = BeautifulSoup(open(appsDir + app, 'rb'), 'html.parser')
                game_details = soup.find('div', {'class', 'game_details'})
                
                links = game_details.findAll('a')
                
                for link in links:
                    
                    try:
                        linkHref = str(link['href'] or '')
                        linkText = link.text
                        
                        if '/genre/' in linkHref and len(linkText) > 1:
                            genre = [appID, linkText]
                            update_steam_genre(conn, genre)
                    except:
                        pass
                        
                appCount += 1
            except Exception as e:
                pass
        
    conn.commit()
    
    # Clean genre duplicates
    
    sql = 'DELETE FROM steam_genres WHERE genreid NOT IN (SELECT MAX(genreid) FROM steam_genres GROUP BY appid, genre)'
    cur = conn.cursor()
    cur.execute(sql)
    conn.commit()
        
    print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + str(appCount) + ' new apps were succesfully scanned.')
    
    
def parse_vr_tags(conn):
    
    sql = 'SELECT DISTINCT appid FROM steam_tags'
    cur = conn.cursor()
    cur.execute(sql)
    appIDList = cur.fetchall()
    appIDList = [item for sublist in appIDList for item in sublist]
    
    print(datetime.datetime.now().strftime('%H:%M:%S') + ' - Scanning for new user tags...')
    
    apps = os.listdir(appsDir)
    
    appCount  = 0
    
    print(appIDList)
    
    for app in apps:
        
        appID = int(app.replace('.html',''))
        
        if appID not in appIDList:
            
            print(appID)
            
            if appCount % 10 == 0:
                print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + str(appCount) + ' apps processed.')
                conn.commit()
            
            try:
                soup = BeautifulSoup(open(appsDir + app, 'rb'), 'html.parser')
                popular_tags = soup.find('div', {'class', 'popular_tags'})
                
                links = popular_tags.findAll('a')
                
                for link in links:
                    
                    try:
                        linkHref = str(link['href'] or '')
                        linkText = link.text.strip()
                        
                        if '/tags/' in linkHref and len(linkText) > 1:
                            tag = [appID, linkText]
                            update_steam_tag(conn, tag)
                    except:
                        pass
                        
                appCount += 1
            except Exception as e:
                pass
        
    conn.commit()
    
    # Clean genre duplicates
    
    sql = 'DELETE FROM steam_tags WHERE tagid NOT IN (SELECT MAX(tagid) FROM steam_tags GROUP BY appid, tag)'
    cur = conn.cursor()
    cur.execute(sql)
    conn.commit()
        
    print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + str(appCount) + ' new apps were succesfully scanned.')
    
    
def parse_vr_headsets(conn):
    
    sql = 'SELECT DISTINCT appid FROM steam_headsets'
    cur = conn.cursor()
    cur.execute(sql)
    appIDList = cur.fetchall()
    appIDList = [item for sublist in appIDList for item in sublist]
    
    print(datetime.datetime.now().strftime('%H:%M:%S') + ' - Scanning for supported headsets...')
    
    apps = os.listdir(appsDir)
    
    appCount  = 0
    
    print(appIDList)
    
    for app in apps:
        
        appID = int(app.replace('.html',''))
        
        if appID not in appIDList:
            
            print(appID)
            
            if appCount % 10 == 0:
                print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + str(appCount) + ' apps processed.')
                conn.commit()
            
            try:
                soup = BeautifulSoup(open(appsDir + app, 'rb'), 'html.parser')
                specs = soup.findAll('div', {'class', 'game_area_details_specs'})
                
                for spec in specs:
                    links = spec.findAll('a')
                    
                    for link in links:
                        
                        try:
                            linkHref = str(link['href'] or '')
                            linkText = link.text.strip()
                            
                            if 'vrsupport' in linkHref and len(linkText) > 1:
                                headset = [appID, linkText]
                                update_steam_headset(conn, headset)
                        except:
                            pass
                            
                    appCount += 1
            except Exception as e:
                pass
        
    conn.commit()
    
    # Clean genre duplicates
    
    sql = 'DELETE FROM steam_tags WHERE tagid NOT IN (SELECT MAX(tagid) FROM steam_tags GROUP BY appid, tag)'
    cur = conn.cursor()
    cur.execute(sql)
    conn.commit()
        
    print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + str(appCount) + ' new apps were succesfully scanned.')
        

def parse_vr_pages(conn, region, inputDir, released, pageMax, curSymbol, currency):
        
    # Now start parsing the VR listing pages
    
    print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + 'Parsing directory ' + inputDir)
    
    pages = os.listdir(inputDir)
    sort_nicely(pages)
    
    appCount  = 0
    pageCount = 1
    
    for page in pages:
        
        if pageCount <= pageMax:
            print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + 'Parsing VR page ' + page)
            soup = BeautifulSoup(open(inputDir + page, 'rb'), 'html.parser')
            
            apps = soup.findAll('a', {'class', 'search_result_row'})
            
            for app in apps:
                
                try:
                    appLink = app['href']
                    appID = appLink.split('/')[4]
                    
                    title = extract_field(app, 'span', 'title', 'text')
                    rdate = extract_field(app, 'div', 'search_released', 'text')
                    
                    if region == "us":
                        try:
                            rdate = datetime.datetime.strptime(rdate, '%b %d, %Y').strftime('%Y-%m-%d')
                        except:
                            try:
                                rdate = datetime.datetime.strptime(rdate, '%B %d, %Y').strftime('%Y-%m-%d')
                            except:
                                try:
                                    rdate = datetime.datetime.strptime(rdate, '%B %d %Y').strftime('%Y-%m-%d')
                                except:
                                    try:
                                        rdate = datetime.datetime.strptime(rdate, '%b %Y').strftime('%Y-%m')
                                    except:
                                        try:
                                            rdate = datetime.datetime.strptime(rdate, '%B %Y').strftime('%Y-%m')
                                        except:
                                            try:
                                                rdate = datetime.datetime.strptime(rdate, '%d %b, %Y').strftime('%Y-%m-%d')
                                            except:
                                                try:
                                                    rdate = datetime.datetime.strptime(rdate, '%d %B, %Y').strftime('%Y-%m-%d')
                                                except:
                                                    try:
                                                        rdate = datetime.datetime.strptime(rdate, '%d %B %Y').strftime('%Y-%m-%d')
                                                    except:
                                                        pass 
                                    
                    else:
                        try:
                            rdate = datetime.datetime.strptime(rdate, '%d %b, %Y').strftime('%Y-%m-%d')
                        except:
                            try:
                                rdate = datetime.datetime.strptime(rdate, '%d %B, %Y').strftime('%Y-%m-%d')
                            except:
                                try:
                                    rdate = datetime.datetime.strptime(rdate, '%d %B %Y').strftime('%Y-%m-%d')
                                except:
                                    try:
                                        rdate = datetime.datetime.strptime(rdate, '%b %Y').strftime('%Y-%m')
                                    except:
                                        try:
                                            rdate = datetime.datetime.strptime(rdate, '%B %Y').strftime('%Y-%m')
                                        except:
                                            pass                   
                    
                    reviews  = extract_field(app, 'span', 'search_review_summary', 'data-tooltip-html')
                    discount = extract_field(app, 'div', 'search_discount', 'text').replace('\n', '')
                    price    = extract_field(app, 'div', 'search_price', 'text').strip()
                    
                    score = ''
                    reviewCount= ''
                    vrOnly = 0
                    popularity = 0
                    
                    if 'VR Only' in app.text:
                        vrOnly = 1
                    
                    if len(reviews) > 1:
                        score = reviews.split('<br>')[1].split('% of')[0]
                        reviewCount = reviews.split('of the ')[1].split(' user reviews')[0].replace(',','').replace('.','')
                        
                        try:
                            popularity = str(round(int(reviewCount) / int((datetime.datetime.today() - datetime.datetime.strptime(rdate, '%Y-%m-%d')).days)))
                        except:
                            pass
                    
                    if len(price.split(curSymbol)) > 2:
                        
                        if currency == 'EUR':
                            price = price.split(curSymbol)[1].strip()
                        else:
                            price = price.split(curSymbol)[2].strip()
                        
                    price = price.replace(curSymbol, '').replace(',','.').replace('--','00')
                    
                    if len(price) <= 1 and released == 1:
                        releasedFinal = 0
                    else:
                        releasedFinal = released
                        
                    uniqID = region + '-' + appID
                    
                    if title.endswith(' Demo') == False:
                        appDB = [uniqID, region, appID, title, appLink, rdate, vrOnly, score, reviewCount, popularity, discount, price, currency, releasedFinal]
                        appCount  += 1
                        update_steam_index(conn, appDB)
                        
                        #appHistoryDB = [str(datetime.datetime.now()), uniqID, region, appID, title, appLink, rdate, vrOnly, score, reviewCount, popularity, discount, price, currency, releasedFinal]
                        #update_steam_index_history(conn, appHistoryDB)
                        
                except Exception as ex:
                    print('Error processing app.')
                    print(ex)
                
        pageCount += 1
            
    #delete_steam_index_history_duplicates(conn)
    conn.commit()
    
    print(datetime.datetime.now().strftime('%H:%M:%S') + ' - ' + str(appCount) + ' games were succesfully processed.')
    

def dataToJSON(conn,region):
    
    cur = conn.cursor()
    
    cur.execute("SELECT steam_index.appid, title, rdate, score, reviews, popularity, discount, price, vronly,group_concat(DISTINCT category),group_concat(DISTINCT genre),group_concat(DISTINCT tag) FROM steam_index LEFT OUTER JOIN steam_filters ON steam_index.appid = steam_filters.appid LEFT OUTER JOIN steam_genres ON steam_index.appid = steam_genres.appid LEFT OUTER JOIN steam_tags ON steam_index.appid = steam_tags.appid WHERE link LIKE '%/app/%' AND reviews != '' AND released = 1 AND region = '" + region + "' AND popularity >= 0 GROUP BY steam_index.appid ORDER BY popularity DESC")
    
    print('Preparing JSON dataset export')
    
    currentdate = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")[:-1] + '0 CET'
        
    rows = cur.fetchall()
    
    json_output = []
    
    for row in rows:
        
        currency = "€"
        
        if region == "us":
            currency = "$"
            
        if region == "ca":
            currency = "CA$"
            
        if region == "au":
            currency = "A$"
            
        if region == "gb":
            currency = "£"
            
        title      = format_title(row[1], row[0])
        rdate      = row[2]
        score      = str(row[3])
        reviews    = str(row[4])
        popularity = str(row[5])
        priceRaw   = format_price_raw(row[7])
        price      = format_price(row[7], row[6], currency)
        discount   = format_discount(row[6])
        vronly     = format_vronly(row[8])
        filters    = str(row[9] or '')
        genres     = str(row[10] or '')
        tags       = str(row[11] or '')
        
        json_row = [popularity,title,'',score,reviews,priceRaw,price,format_discount_raw(row[6]),discount,vronly,rdate,filters,genres,tags]
        
        json_output.append(json_row)
    
    filename = '/var/www/html/steamvr/' + 'index_' + region + '.json'
    
    json_output_final = {}
    json_output_final["data"] = json_output
    
    file = open(filename, 'w')
    file.write(json.dumps(json_output_final, ensure_ascii=False))
    file.close()
    
    print('JSON dataset succesfully generated - ' + str(len(rows)) + ' titles')
    

# Web functions
    
def dataToTable(conn,region):
    
    dataToJSON(conn,region)
    
#    cur = conn.cursor()
#    
#    cur.execute("SELECT steam_index.appid, title, rdate, score, reviews, popularity, discount, price, vronly,group_concat(DISTINCT category),group_concat(DISTINCT genre),group_concat(DISTINCT tag) FROM steam_index LEFT OUTER JOIN steam_filters ON steam_index.appid = steam_filters.appid LEFT OUTER JOIN steam_genres ON steam_index.appid = steam_genres.appid LEFT OUTER JOIN steam_tags ON steam_index.appid = steam_tags.appid WHERE link LIKE '%/app/%' AND reviews != '' AND released = 1 AND region = '" + region + "' AND popularity >= 0 GROUP BY steam_index.appid ORDER BY popularity DESC")
    
    print('Converting data to HTML table')
    
    euactive = ''
    usactive = ''
#    auactive = ''
#    caactive = ''
#    gbactive = ''
    
    if region == 'eu':
        euactive = 'active'
    if region == 'us':
        usactive = 'active'
#    if region == 'au':
#        auactive = 'active'
#    if region == 'ca':
#        caactive = 'active'
#    if region == 'gb':
#        gbactive = 'active'
    
    title = 'SteamVR - ' + region.upper() + ' Store Overview'
    
    titletop = 'SteamVR'
    titlesub = region.upper() + ' Store Overview'
    
    addon = '<p class="addon">'
    addon += '<a class="button ' + usactive + '" href="index_us.html">US</a> '
    addon += '<a class="button ' + euactive + '" href="index_eu.html">EU</a> '
#    addon += '<a class="button ' + auactive + '" href="index_au.html">AU</a> '
#    addon += '<a class="button ' + caactive + '" href="index_ca.html">CA</a> '
#    addon += '<a class="button ' + gbactive + '" href="index_gb.html">GB</a> '
    addon += '</p>'
    
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
          
          <script type="text/javascript" src="/steamvr/js/jquery-3.4.1.min.js"></script>
          <script type="text/javascript" src="/steamvr/js/datatables.min.js"></script>
          <script type="text/javascript" src="/steamvr/js/stellarnav.min.js"></script>
          <script type="text/javascript" src="/steamvr/js/lozad.min.js"></script>
          <script type="text/javascript" src="/steamvr/js/steamvr.js?uuid=''' + str(uuid.uuid4()) + '''"></script>
          
          <script async src="https://www.googletagmanager.com/gtag/js?id=UA-154490678-1"></script>
          <script>
            window.dataLayer = window.dataLayer || [];
            function gtag(){dataLayer.push(arguments);}
            gtag('js', new Date());  
            gtag('config', 'UA-154490678-1', { 'optimize_id': 'GTM-NW2BFQH'});
          </script>
          
          <link rel="stylesheet" type="text/css" href="/steamvr/js/datatables.min.css"/> 
          <link rel="stylesheet" type="text/css" href="/steamvr/css/stellarnav.min.css"/> 
          <link rel="stylesheet" type="text/css" href="/steamvr/css/style.css?uuid=''' + str(uuid.uuid4()) + '''"/>
          
          <link rel="icon" href="/favicon.ico" type="image/x-icon"/>
          <link rel="shortcut icon" href="/favicon.ico" type="image/x-icon"/>
        
        </head>
        
        <body>'''

#    html += '<div class="main-header platform-steamvr">'
#    html += '<a class="home" target="_top" href="/">Home</a>'
#    html += '<a class="platform" target="_top" href="/quest/">Quest</a>'
#    html += '<a class="platform" target="_top" href="/rift/">Rift</a>'
#    html += '<a class="platform" target="_top" href="/go/">Go</a>'
#    html += '<a class="platform active" target="_top" href="/steamvr/">SteamVR</a>'
#    html += '</div>'
        
    html += '<div class="stellarnav"><ul>'
    html += '<li><a target="_top" href="/">Home</a></li>'
    html += '<li><a target="_top" href="/quest/">Quest</a>'
    html += '<ul><li><a target="_top" href="/quest/lab/">App Lab</a></li>'
    html += '<li><a target="_top" href="/quest/compatible/">Q1 Compatible Go apps</a></li>'
    html += '<li><a target="_top" href="/quest/tracker.html">Version Tracker</a></li>'
    html += '</ul></li>'    
    html += '<li><a target="_top" href="/rift/">Rift</a>'
    html += '<ul><li><a target="_top" href="/rift/tracker.html">Version Tracker</a></li>'
    html += '</ul></li>'
    html += '<li><a target="_top" href="/go/">Go</a></li>'
    html += '<li><a class="active" target="_top" href="/steamvr/">SteamVR</a></li>'
    html += '</ul></div>'
    
    html += '<div class="main-body platform-steamvr">'
    
    #html += '<div class="warning">Due to technical issues it is currently impossible to refresh non-EU currencies. A solution is being worked on and functionality should be restored in a few days.</div>'
    
    #html += '<h1>' + titletop + '</h1>'
    html += '<h1><img src="/steamvr/images/steamvr.png" height="40" width="183"></h1>'
    html += '<h2>' + titlesub + '</h2>'
    html += addon
    html += '<p><b>Last updated on:</b> ' + currentdate + '</p>'
    html += '<p><b>How is popularity calculated?</b> This number is based on the amount of reviews received on a daily basis since release.</p>'
    html += '<p><b>IMPORTANT:</b> Unlike the other overviews only apps with at least 10 reviews are listed. The SteamVR store has a lot of junk.</p>'
    
    html += '<div class="filters">'
    html += '<div class="filter"><label class="filter-text">Score ≥ <span id="scorevalue">0</span>%</label><input type="range" min="0" max="95" value="0" step="5" id="minscore"></div>'
    
    html += '<div class="filter"><label class="filter-text">Reviews ≥ <span id="ratingvalue">0</span></label><input type="range" min="0" max="1000" value="0" step="50" id="minratings"></div>'
        
    html += '<div class="filter"><label class="filter-text">Price ≤ <span id="pricevalue">' + format_price_max(region) + '</span></label><input type="range" min="0" max="' + format_price_max(region) + '" value="' + format_price_max(region) + '" step="1" id="maxprice"></div>'
    
    html += '<div class="filter category"><label class="filter-text">Filter</label>' + category_select() + '</div>'
    html += '<div class="filter genre"><label class="filter-text">Genre</label>' + genre_select() + '</div>'
    html += '<div class="filter tag"><label class="filter-text">User Tag</label>' + tag_select() + '</div>'
    
    html += '</div>'
    
    html += '<table id="steamlist">\n'
    html += '<thead><tr><th class="all popularity"><span>Popularity</span></th><th class="all">Title</th><th></th><th>Score</th><th>Reviews</th><th>Price (Raw)</th><th>Price</th><th>Discount (Raw)</th><th>Discount</th><th>VR Only</th><th>Release Date</th><th>Filters</th><th>Genres</th><th>User Tags</th></thead>\n'
#    html += '<tbody>'
#    
#    rows = cur.fetchall()
#    
#    for row in rows:
#        
#        html += '<tr>'
#        
#        currency = "€"
#        
#        if region == "us":
#            currency = "$"
#            
#        if region == "ca":
#            currency = "CA$"
#            
#        if region == "au":
#            currency = "A$"
#            
#        if region == "gb":
#            currency = "£"
#            
#        title      = format_title(row[1], row[0])
#        rdate      = row[2]
#        score      = str(row[3])
#        reviews    = str(row[4])
#        popularity = str(row[5])
#        priceRaw   = format_price_raw(row[7])
#        price      = format_price(row[7], row[6], currency)
#        discount   = format_discount(row[6])
#        vronly     = format_vronly(row[8])
#        filters    = str(row[9] or '')
#        genres     = str(row[10] or '')
#        tags       = str(row[11] or '')
#        
#        html += '<td>' + popularity + '</td>' #0
#        html += '<td><div class="title">' + title + '</div></td>' #1
#        html += '<td class="control"></td>' #2
#        html += '<td>' + score + '</td>' #3
#        html += '<td>' + reviews + '</td>' #4
#        html += '<td>' + priceRaw + '</td>' #5
#        html += '<td>' + price + '</td>' #6
#        html += '<td>' + format_discount_raw(row[6]) + '</td>' #7
#        html += '<td>' + discount + '</td>' #8
#        html += '<td>' + vronly + '</td>' #9
#        html += '<td>' + rdate + '</td>' #10
#        html += '<td>' + filters + '</td>' #11
#        html += '<td>' + genres + '</td>' #12
#        html += '<td>' + tags + '</td>' #13
#            
#        html += '</tr>\n'
#    
#    html += '</tbody>'
    html += '</table>\n'
    html += '</div></body></html>' 
    
    filename = '/var/www/html/steamvr/' + 'index_' + region + '.html'
    
    file = open(filename, 'wb')
    file.write(html.encode('utf-8'))
    file.close()
    
    print('HTML table succesfully generated')
    
    
def process_region(region):
    
    parse_vr_pages(conn, region, pageDirTopSelling, 1, 999, curSymbol, currency)
    parse_vr_pages(conn, region, pageDirUpcoming, 0, 999, curSymbol, currency)
    parse_vr_pages(conn, region, pageDirCurrent, 1, 999, curSymbol, currency)
    
    if region == "us":
        parse_vr_ranking(conn, pageDirCurrent, 'Latest')
        parse_vr_ranking(conn, pageDirUpcoming, 'Upcoming')
        parse_vr_ranking(conn, pageDirTopSelling, 'Top Selling')
        parse_vr_genres(conn)
        process_custom_filters(conn)
        copy_images()
        
    dataToTable(conn,region)
    

def regenerateAllTables():
    
    regions = ['us','eu']
    
    for reg in regions:
        dataToTable(conn,reg)
    
    
# End functions

region = "us"

if len(sys.argv) >= 2:
    if sys.argv[1] != None:
        region = sys.argv[1]

if region == "us":
    curSymbol = '$'
    currency = 'USD'
    
if region == "eu":
    curSymbol = '€'
    currency = 'EUR'
    
if region == "au":
    curSymbol = 'A$'
    currency = 'AUD'

if region == "gb":
    curSymbol = '£'
    currency = 'GBP'
    
if region == "ca":
    curSymbol = 'CDN$'
    currency = 'CAD'
    
mainDir = "/VRDB/"
imageDir = "/VRDB/HTML/SteamVR/Images/"
appsDir = "/VRDB/HTML/SteamVR/Apps/" + region + "/"

pageDirCurrent  = "/VRDB/HTML/SteamVR/Pages/Current/" + region + "/"
vrURLCurrent    = "https://store.steampowered.com/search/?sort_by=Released_DESC&vrsupport=402&page="

pageDirUpcoming = "/VRDB/HTML/SteamVR/Pages/Upcoming/" + region + "/"
vrURLUpcoming   = "https://store.steampowered.com/search/?filter=comingsoon&vrsupport=402&page="

pageDirTopSelling = "/VRDB/HTML/SteamVR/Pages/Top Selling/" + region + "/"
vrURLTopSelling   = "https://store.steampowered.com/search/?filter=topsellers&vrsupport=402&page="

os.chdir(mainDir)
    
conn = create_connection("vrdb.db")

#regenerateAllTables()
#parse_vr_pages(conn, 'us', pageDirUpcoming, 0, 999, curSymbol, currency)

#for region in ['us','eu','gb','ca','au']:
#    parse_vr_pages(conn, region, pageDirTopSelling, 1, 999, curSymbol, currency)
#    parse_vr_pages(conn, region, pageDirUpcoming, 0, 999, curSymbol, currency)
#    parse_vr_pages(conn, region, pageDirCurrent, 1, 999, curSymbol, currency)

if processing_check(conn, region) == True:
    process_region(region)
    processing_add(conn, region)

conn.close() 
























