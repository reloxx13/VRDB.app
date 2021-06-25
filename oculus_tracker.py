# -*- coding: utf-8 -*-

import csv
import datetime
import json
import math
import os
import re
import sqlite3
import sys
import uuid

from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from shutil import copyfile
from sqlite3 import Error

sleeptime = 5

# DB functions

def create_connection(db_file):
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except Error as e:
        print(e)
 
    return None
    
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
        return '<span>' + currency + str(price) + '</span>'
          
def format_price_raw(price):
    if price == 'TBD':
        return '0'
    else:
        return str(price)
    
def format_price_max(region,platform,questcompat):
    cur = conn.cursor()
    
    if questcompat == False:
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
    
def format_title(appID, title, platform):
    
    storelink = ''
    
    if platform == "quest":
        storelink = 'https://www.oculus.com/experiences/quest/' + str(appID)
    if platform == "rift":
        storelink = 'https://www.oculus.com/experiences/rift/' + str(appID)
    
    sql = 'SELECT shortname FROM app_shortname WHERE appID = "' + str(appID) + '"'
    cur = conn.cursor()
    cur.execute(sql)
    
    result_row = cur.fetchone()
    
    if result_row:
        title = result_row[0]
    
    #return '<a href="' + storelink + '" target="_blank"><img height="35" width="62" alt="' + title + '" src="/oculus/images/' + str(appID) + '.jpg"><span>' + title + '</span></a>'
    return '<img height="35" width="62" alt="' + title + '" src="/oculus/images/' + str(appID) + '.jpg"><span>' + title + '</span></a>'
    
def format_genres(genres):
    genreSplit = genres.split(', ')
    
    if len(genreSplit) > 1:
        return genreSplit[0] + ', ' + genreSplit[1]
    else:
        return genres
    
def format_popularity(popularity, released, rdate):
    if released == 0:
        return '<i class="upcoming"><span>Upcoming</span></i>'
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
        
        
def create_path(dir1, dir2, platform, region):
    return mainDir + slash + dir1 + slash + dir2 + slash + platform + slash + region + slash

# Store functions 
    
def dataToJSON(conn,platform, appLab = False):
    
    cur = conn.cursor()
    
    if appLab == True:
        platformQuery = 'lab'
    else:
        platformQuery = platform
        
    cur.execute("SELECT ai.appid, MAX(ai.title), SUBSTR(av.udate, 0, 11), version, notes FROM app_index AS ai INNER JOIN app_versions AS av ON ai.appid = av.appid WHERE platform = '" + platformQuery + "' AND region = 'us' /*AND SUBSTR(av.udate, 0, 11) != '2019-12-02'*/ GROUP BY ai.appid, SUBSTR(av.udate, 0, 11), version, notes ORDER BY udate DESC")
    
    print('Preparing JSON dataset export')
    
    rows = cur.fetchall()
    
    json_output = []
    
    for row in rows:
        
        json_row = {}
        
        title   = format_title(row[0], row[1], platform)
        udate   = row[2]
        version = row[3]
        
        if len(row[4]) > 1:
            notes = row[4].replace('\n','<br>')
        else:
            notes = 'No patch notes available.'
        
        json_row = ['', title, udate, version, notes]
        
        if len(row[4]) > 1:
            json_output.append(json_row)
            
    if appLab == True:
        filename = '/quest/lab/tracker.json'
    else:
        filename = slash + platform + slash + 'tracker.json'
        
    json_output_final = {}
    json_output_final["data"] = json_output
    
    file = open(htmlDir + filename, 'w', encoding='utf8')
    file.write(json.dumps(json_output_final, ensure_ascii=False))
    file.close()
    
    print('JSON dataset succesfully generated - ' + str(len(rows)) + ' titles')
    
    
def dataToRSS(conn,platform, appLab = False):
    
    cur = conn.cursor()
    
    if appLab == True:
        platformQuery = 'lab'
    else:
        platformQuery = platform
    
    cur.execute("SELECT ai.appid, MAX(ai.title), SUBSTR(av.udate, 0, 11), version, notes FROM app_index AS ai INNER JOIN app_versions AS av ON ai.appid = av.appid WHERE platform = '" + platformQuery + "' AND region = 'us' GROUP BY ai.appid, SUBSTR(av.udate, 0, 11), version, notes ORDER BY udate ASC")
    
    fg = FeedGenerator()
    fg.title(platform.capitalize() + ' Version Tracker')
    fg.subtitle('Generated by VRDB.app')
    fg.link( href='https://vrdb.app', rel='alternate' )
    fg.link( href='https://vrdb.app' + slash + platform + slash + 'tracker.rss' , rel='self' )
    fg.language('en')
    
    print('Preparing RSS feed export')
    
    rows = cur.fetchall()
    
    json_output = []
    
    for row in rows:
        
        json_row = {}
        
        title   = format_title(row[0], row[1], platform)
        udate   = row[2]
        version = row[3]
        
        if len(row[4]) > 1:
            notes = row[4].replace('\n','<br>')
        else:
            notes = 'No patch notes available.'
        
        if platform == "quest" or appLab == True:
            storelink = 'https://www.oculus.com/experiences/quest/' + str(row[0])
        if platform == "rift":
            storelink = 'https://www.oculus.com/experiences/rift/' + str(row[0])
            
        json_row = [storelink, udate + ' - ' + row[1] + ' - Version ' + version, notes]
        
        json_output.append(json_row)
        
    json_output = json_output[-100:]
        
    for json_row in json_output:
        fe = fg.add_entry()
        fe.id(json_row[0])
        fe.title(json_row[1])
        fe.author({'name':'VRDB.app'})
        fe.description(json_row[2])
        fe.link(href='https://vrdb.app' + slash + platform + slash + 'tracker.html')

    if appLab == True:
        filename = '/quest/lab/tracker.rss'
    else:
        filename = slash + platform + slash + 'tracker.rss'
    
    fg.rss_str(pretty=True)
    fg.rss_file(htmlDir + filename)
    
    
# Web functions
    
def dataToTable(conn,platform, appLab = False):
    
    dataToJSON(conn,platform, appLab)
    dataToRSS(conn,platform, appLab)
    
    print('Converting data to HTML table')
    
    if appLab == True:
        title = 'Oculus Quest App Lab - Version Tracker'
        titlesub = 'App Lab Version Tracker'
    else:
        title = 'Oculus ' + platform.capitalize() + ' - Version Tracker'
        titlesub = 'Version Tracker'
    
    currentdate = datetime.datetime.now().strftime("%Y-%m-%d")
    
    html = '''
        <!doctype html>
        <html lang="en">
        <head>
          <meta charset="utf-8">
        
          <title>''' + title + '''</title>
          <meta name="description" content="''' + title + '''">
          <meta name="author" content="Gryphe">
          <meta name="viewport" content="width=device-width, initial-scale=1">
          
          <script type="text/javascript" src="/oculus/js/jquery-3.4.1.min.js"></script>
          <script type="text/javascript" src="/oculus/js/datatables.min.js"></script>
          <script type="text/javascript" src="/oculus/js/stellarnav.min.js"></script>
          <script type="text/javascript" src="/oculus/js/oculus_subpage.js?uuid=''' + str(uuid.uuid4()) + '''"></script>
          
          <link rel="stylesheet" type="text/css" href="/oculus/js/datatables.min.css"/> 
          <link rel="stylesheet" type="text/css" href="/oculus/css/stellarnav.min.css"/> 
          <link rel="stylesheet" type="text/css" href="/oculus/css/style.css?uuid=''' + str(uuid.uuid4()) + '''"/>
          
          <link rel="icon" href="/favicon.ico" type="image/x-icon"/>
          <link rel="shortcut icon" href="/favicon.ico" type="image/x-icon"/>
        
        </head>
        
        <body>'''
        
    platquest  = ''
    platrift   = ''
    platlab    = ''
    
    if platform == 'quest':
        platquest = 'active'
    elif platform == 'rift':
        platrift = 'active'
    elif platform == 'quest/lab':
        platlab = 'active'
        
    html += '<div class="stellarnav"><ul>'
    html += '<li><a class="" target="_top" href="/">Home</a></li>'
    
    html += '<li><a class="' + platquest + '" target="_top" href="/quest/">Quest</a>'
    html += '<ul>'
    html += '<li><a class="" target="_top" href="/quest/compatible/">Q1 Compatible Go apps</a></li>'
    html += '<li><a class="' + platquest + '" target="_top" href="/quest/tracker.html">Version Tracker</a></li>'
    html += '</ul></li>'
    
    html += '<li><a class="' + platrift + '" target="_top" href="/rift/">Rift</a>'
    html += '<ul><li><a class="' + platrift + '" target="_top" href="/rift/tracker.html">Version Tracker</a></li>'
    html += '</ul></li>'
    
    html += '<li><a class="' + platlab + '" target="_top" href="/quest/lab/">App Lab</a>'
    html += '<ul><li><a class="' + platlab + '" target="_top" href="/quest/lab/tracker.html">Version Tracker</a></ul></li>'
    
    html += '<li><a target="_top" href="/steamvr/">SteamVR</a></li>'
    html += '</ul></div>'
    
    html += '<div class="main-body versiontracker platform-' + platform + '">'
    
    #html += '<div class="warning">As of 2021-04-03 Oculus has blocked the ability to refresh VRDB data. Only Steam data will be refreshed for now. I apologize sincerely for the inconvenience.</div>'
    #html += '<div class="warning">As of 2021-04-03 Oculus has blocked the ability to crawl their storefront. Only Steam data will be refreshed for now. I apologize sincerely for the inconvenience.</div>'
    
    if appLab == True:
        platformImage = 'quest'
    else:
        platformImage = platform
    
    #html += '<h1>' + titletop + '</h1>'
    html += '<h1><img src="/oculus/images/' + platformImage + '.png" height="40" width="183"></h1>'
    html += '<h2>' + titlesub + ' <a href="' + 'https://vrdb.app' + slash + platform + slash + 'tracker.rss' + '" target="_blank"><img alt="RSS Feed" style="height: 20px; width:20px;" src="/oculus/images/rss.png"></a>' + '</h2>'
    html += '<p><b>Last updated on:</b> ' + currentdate + '</p>'
    html += '<p>This page lists all app version updates tracked since 2019-12-02 - Entries from this specific date do not represent the real update date.</p><p>Expand the row to view the full patch notes.</p>'
    html += '<p><b>IMPORTANT:</b> Due to a crawling source change all updates had to be recrawled on 2021-04-05. All apps are now tracked but only those containing actual notes are listed here. The RSS feed is unfiltered.</p>'
    
    html += '<table id="oculuslist">\n'
    html += '<thead><tr><th></th><th class="all">Title</th><th class="all">Updated</th><th>Version</th><th>Patch Notes</th></tr></thead>\n'
    html += '</table>\n'
    
    html += '</div></body></html>' 
    
    if appLab == True:
        filename = '/quest/lab/tracker.html'
    else:
        filename = slash + platform + slash + 'tracker.html'
    
    file = open(htmlDir + filename, 'wb')
    file.write(html.encode('utf-8'))
    file.close()
    
    #print('HTML table succesfully generated - ' + str(len(rows)) + ' titles')
    
    print('HTML table succesfully generated')    
    
    

mainDir    = "/VRDB"
slash      = "/"
htmlDir    = "/var/www/html"
imageDir    = "/var/www/html/oculus/images/"

os.chdir(mainDir)

conn = create_connection("vrdb.db")

# Stuff happens here

dataToTable(conn,'quest', False)
dataToTable(conn,'rift', False)
dataToTable(conn,'quest/lab', True)

conn.close()         
        
        
        





