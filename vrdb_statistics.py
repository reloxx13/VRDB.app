# -*- coding: utf-8 -*-

import csv
import datetime
import os
import re
import sqlite3
import sys
import uuid

from bs4 import BeautifulSoup
from shutil import copyfile
from sqlite3 import Error

from PIL import Image
from resizeimage import resizeimage

# DB functions

def create_connection(db_file):
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except Error as e:
        print(e)
 
    return None
    
def link_crossbuy(conn, value, appID, platform):
    
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
        
        return '<a href="https://www.oculus.com/experiences/' + plat2 + '/' + str(result) + '" target="_blank">Yes</a>'
        
    else:
        return ''
    
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
        if sale == 1:
            return '<span class="sale">' + currency + str(price) + '</span>'
        else:
            return '<span>' + currency + str(price) + '</span>'
          
def format_price_raw(price):
    if price == 'TBD':
        return '0'
    else:
        return str(price)
    
def format_title(platform, title, appID):
    
    sql = 'SELECT shortname FROM app_shortname WHERE appID = "' + str(appID) + '"'
    cur = conn.cursor()
    cur.execute(sql)
    
    result_row = cur.fetchone()
    
    title = title[:52]
    
    if result_row:
        title = result_row[0][:52]
        
    storelink = 'https://www.oculus.com/experiences/' + platform + '/' + str(appID) + '/'
    
    return '<div class="title"><a href="' + storelink + '" target="_blank"><img height="35" width="62" alt="' + title + '" src="/oculus/images/' + str(appID) + '.jpg"><span>' + title + '</span></a></div>'

def format_title_steam(appID, title, appLink):
    
    sql = 'SELECT shortname FROM app_shortname WHERE appID = "' + str(appID) + '"'
    cur = conn.cursor()
    cur.execute(sql)
    
    result_row = cur.fetchone()
    
    title = title[:52]
    
    if result_row:
        title = result_row[0][:52]
    
    return '<div class="title"><a href="' + appLink + '" target="_blank"><img height="35" width="93" alt="' + title + '" src="/steamvr/images/' + str(appID) + '.jpg"><span style="padding-left: 103px;">' + title + '</span></a></div>'
    
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
        
def format_column(value, customclass):
    return '<span class="' + customclass + '">' + str(value) + '</span>'
        
def statistics_popular_month(conn, platform):
    
    # Month ago
    
    cur = conn.cursor()
    cur.execute("SELECT appid, title, MIN(hdate), ratings, score, crossbuy FROM app_details_history WHERE hdate >= date('now', '-1 month') AND appid IN (SELECT appid FROM app_index WHERE platform = '" + platform + "') AND title NOT LIKE '% Demo' AND score != 'N/A' AND released = 1 AND title IN (SELECT title FROM app_index WHERE platform = '" + platform + "') GROUP BY appid, title ORDER BY title")
    rowsOld = cur.fetchall()
    
    # Current
    
    cur = conn.cursor()
    cur.execute("SELECT appid, title, MAX(hdate), ratings, score, crossbuy FROM app_details_history WHERE hdate >= date('now', '-1 month') AND appid IN (SELECT appid FROM app_index WHERE platform = '" + platform + "') AND title NOT LIKE '% Demo' AND score != 'N/A' AND released = 1 AND title IN (SELECT title FROM app_index WHERE platform = '" + platform + "') GROUP BY appid, title ORDER BY title")
    rowsCur = cur.fetchall()
    
    # Apps released this month
    
    cur = conn.cursor()
    cur.execute("SELECT appid FROM app_details WHERE rdate >= date('now', '-1 month') AND appid IN (SELECT appid FROM app_index WHERE platform = '" + platform + "') AND title NOT LIKE '% Demo' AND score != 'N/A' AND released = 1 AND title IN (SELECT title FROM app_index WHERE platform = '" + platform + "')")
    recentApps = cur.fetchall()
    
    # Calculation time
    
    result = []
    
    rowCount = len(rowsOld)
    
    for x in range(rowCount):
        
        ratingDiff = rowsCur[x][3] - rowsOld[x][3]
        
        for app in recentApps:
            if rowsCur[x][0] == app[0]:
                ratingDiff = rowsCur[x][3]
                
        title = format_title(platform, rowsCur[x][1], rowsCur[x][0])
            
        result.append([title, ratingDiff])
    
    result = sorted(result, key=lambda x: x[1], reverse=True)
    
    return result[0:10]


def statistics_latest_releases(conn, platform):
    
    cur = conn.cursor()
    cur.execute("SELECT appid, title, rdate FROM app_details WHERE appid IN (SELECT appid FROM app_index WHERE platform = '" + platform + "') AND title NOT LIKE '% Demo' AND released = 1 AND title IN (SELECT title FROM app_index WHERE platform = '" + platform + "') ORDER BY rdate DESC, title ASC LIMIT 10")
    rows = cur.fetchall()
    
    result = []
    
    for row in rows:
        title = format_title(platform, row[1], row[0])
        result.append([title, row[2]])
        
    return result


def statistics_upcoming_releases(conn, platform):
    
    cur = conn.cursor()
    cur.execute("SELECT appid, title, rdate FROM app_details WHERE appid IN (SELECT appid FROM app_index WHERE platform = '" + platform + "') AND title NOT LIKE '% Demo' AND released = 0 AND title IN (SELECT title FROM app_index WHERE platform = '" + platform + "') ORDER BY rdate ASC, title ASC LIMIT 10")
    rows = cur.fetchall()
    
    result = []
    
    for row in rows:
        title = format_title(platform, row[1], row[0])        
        result.append([title, row[2]])
        
    return result
        
        
def sqlite_to_table(title, columns, query, rows, ranked, classes):
    
    if query != False:
        cur = conn.cursor()
        cur.execute(query)
        
        rows = cur.fetchall()
    
    html = '<div class="statistics-table"><h2 class="oculus-statistics-title">' + title + '</h2>\n'
    html += '<table id="oculus-statistics">\n'
    
    rowCount = len(rows) + 1
    colCount = len(columns)
    
    for x in range(rowCount):
        
        if x == 0:
            html += '<thead><tr>'
            
            if ranked == True:
                html += '<th>Rank</th>'
                
        elif x == 1:
            html += '</tr></thead>\n<tbody>\n<tr>'
        else:
            html += '<tr>'
            
        if ranked == True and x >= 1:
            html += '<td class="center">' + str(x) + '</td>'
        
        for y in range(colCount):
            
            if x == 0:
                html += '<th>' + columns[y] + '</th>'
            else:
                html += '<td class="' + classes[y] + '">' + str(rows[x-1][y]) + '</td>'
        
        if x >= 1:
            html += '</tr>\n'
    
    html += '</tbody>\n'
    html += '</table></div>\n'
    
    return html


def sqlite_to_table_steam(title, query):
    
    if query != False:
        cur = conn.cursor()
        cur.execute(query)
        
        rows = cur.fetchall()
    
    html = '<div class="statistics-table"><h2 class="oculus-statistics-title steam-statistics-title">' + title + '</h2>\n'
    html += '<table id="oculus-statistics">\n'
    
    rowCount = len(rows) + 1
    colCount = 2
    
    rowsFinal = []
    
    for row in rows:
        rowsFinal.append([format_title_steam(row[0], row[1], row[2]), row[3]])

    rows = rowsFinal
    
    for x in range(rowCount):
        
        if x == 0:
            html += '<thead><tr>'
                
        elif x == 1:
            html += '</tr></thead>\n<tbody>\n<tr>'
        else:
            html += '<tr>'
        
        for y in range(colCount):
            
            if x == 0:
                if y == 0:
                    html += '<th>Title</th>'
                if y == 1:
                    html += '<th>Release Date</th>'
            else:
                if y == 0:
                    html += '<td>' + str(rows[x-1][y]) + '</td>'
                if y == 1:
                    html += '<td class="center">' + str(rows[x-1][y]) + '</td>'
        
        if x >= 1:
            html += '</tr>\n'
    
    html += '</tbody>\n'
    html += '</table></div>\n'
    
    return html

# Web functions
    
def dataToStatistics(conn):
    
    currentdate = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")[:-1] + '0 CET'
    
    print('Converting data to HTML table')
        
    title = 'VRDB.app - VR Store Statistics'
    
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
          <script type="text/javascript" src="/oculus/js/lozad.min.js"></script>
          <script type="text/javascript" src="/oculus/js/oculus.js?uuid=''' + str(uuid.uuid4()) + '''"></script>
                    
          <link rel="stylesheet" type="text/css" href="/oculus/js/datatables.min.css"/> 
          <link rel="stylesheet" type="text/css" href="/oculus/css/stellarnav.min.css"/> 
          <link rel="stylesheet" type="text/css" href="/oculus/css/style.css?uuid=''' + str(uuid.uuid4()) + '''"/>
          
          <link rel="icon" href="/favicon.ico" type="image/x-icon"/>
          <link rel="shortcut icon" href="/favicon.ico" type="image/x-icon"/>
        
        </head>
        
        <body>'''
        
    html += '<div class="stellarnav statistics"><ul>'
    html += '<li><a target="_top" href="/">Home</a></li>'
    html += '<li><a class="active" target="_top" href="/quest/">Quest</a>'
    html += '<ul><li><a target="_top" href="/quest/compatible/">Q1 Compatible Go apps</a></li>'
    html += '<li><a target="_top" href="/quest/tracker.html">Version Tracker</a></li>'
    html += '</ul></li>'    
    html += '<li><a target="_top" href="/rift/">Rift</a>'
    html += '<ul><li><a target="_top" href="/rift/tracker.html">Version Tracker</a></li>'
    html += '</ul></li>'
    html += '<li><a target="_top" href="/quest/lab/">App Lab</a>'
    html += '<ul><li><a target="_top" href="/quest/lab/tracker.html">Version Tracker</a></li></ul></li>'
    html += '<li><a target="_top" href="/steamvr/">SteamVR</a></li>'
    html += '</ul></div>'
    
    
    
    html += '<div class="main-body statistics">'    
    
    #html += '<div class="warning">As of 2021-04-03 Oculus has blocked the ability to refresh VRDB data. Only Steam data will be refreshed for now. I apologize sincerely for the inconvenience.</div>'
    #html += '<div class="warning">As of 2021-04-03 Oculus has blocked the ability to crawl their storefront. Only Steam data will be refreshed for now. I apologize sincerely for the inconvenience.</div>'
    
    html += '<h1>' + title + '</h1>'
    html += '<p><b>Last updated on:</b> ' + currentdate + '</p>'
    
    # Tables go here
    
    html += '<div class="statistics-container">'
    
    html += sqlite_to_table('<a href="/quest/">Quest</a> - Popular This Month', ['Title', 'Ratings (Gained)'], False, statistics_popular_month(conn, 'quest'), False, ['', 'center'])
    html += sqlite_to_table('<a href="/quest/">Quest</a> - Latest Releases', ['Title', 'Release Date'], False, statistics_latest_releases(conn, 'quest'), False, ['', 'center', 'center'])
    html += sqlite_to_table('<a href="/quest/">Quest</a> - Upcoming Releases', ['Title', 'Release Date'], False, statistics_upcoming_releases(conn, 'quest'), False, ['', 'center', 'center'])
    
    html += sqlite_to_table('<a href="/rift/">Rift</a> - Popular This Month', ['Title', 'Ratings (Gained)'], False, statistics_popular_month(conn, 'rift'), False, ['', 'center'])
    html += sqlite_to_table('<a href="/rift/">Rift</a> - Latest Releases', ['Title', 'Release Date'], False, statistics_latest_releases(conn, 'rift'), False, ['', 'center', 'center'])
    html += sqlite_to_table('<a href="/rift/">Rift</a> - Upcoming Releases', ['Title', 'Release Date'], False, statistics_upcoming_releases(conn, 'rift'), False, ['', 'center', 'center'])
    
    html += sqlite_to_table_steam('<a href="/steamvr/">SteamVR</a> - Top Selling', "SELECT appid, title, link, (SELECT rdate FROM steam_index WHERE appid = sr.appid LIMIT 1) FROM steam_ranking AS sr WHERE category = 'Top Selling' ORDER BY rank LIMIT 10")
    html += sqlite_to_table_steam('<a href="/steamvr/">SteamVR</a> - Latest Releases', "SELECT appid, title, link, (SELECT rdate FROM steam_index WHERE appid = sr.appid LIMIT 1) FROM steam_ranking AS sr WHERE category = 'Latest' AND appid IN (SELECT appid FROM steam_index WHERE released = 1) ORDER BY rank LIMIT 10")
    html += sqlite_to_table_steam('<a href="/steamvr/">SteamVR</a> - Upcoming Releases', "SELECT appid, title, link, (SELECT rdate FROM steam_index WHERE appid = sr.appid LIMIT 1) FROM steam_ranking AS sr WHERE category = 'Upcoming' ORDER BY rank LIMIT 10")

    html += '</div>'
    html += '</body></html>' 
    
    filename = 'index.html'
    
    file = open(htmlDir + filename, 'wb')
    file.write(html.encode('utf-8'))
    file.close()
    
    print('HTML statistics succesfully generated')


mainDir    = "/VRDB"
htmlDir    = "/var/www/html/"
imageDir    = "/var/www/html/oculus/images/"

os.chdir(mainDir)

conn = create_connection("vrdb.db")

dataToStatistics(conn)

conn.close()
        
        
        





