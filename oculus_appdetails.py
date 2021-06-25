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

def appRatingsTotal(appID):
    
    cur = conn.cursor()
    cur.execute("""SELECT SUBSTR(hdate, 0, 11), MAX(ratings)
                FROM app_details_history
                WHERE appid = '""" + str(appID) + """'
                GROUP BY SUBSTR(hdate, 0, 11)
                ORDER BY SUBSTR(hdate, 0, 11)""")
    appRatings = cur.fetchall()
    
    # Calculation time
    
    rowOld = []
    
    rowsValid = []
    
    for row in appRatings:
        if len(rowOld) == 0:
            rowOld = [row[0], row[1]]
            
        if row[0] > rowOld[0]:
            rowsValid.append(row)

    rowLabels = '['
    rowValues = '['
    
    interval = 7
    intervalCurrent = 0
    
    for row in rowsValid:
        intervalCurrent += 1
        
        if intervalCurrent == interval:
            rowLabels += "'" + row[0] + "',"
            rowValues += str(row[1]) + ","
            intervalCurrent = 0

    rowLabels = rowLabels[:-1] + ']'
    rowValues = rowValues[:-1] + ']'
        
    return chartCreator('AppRatings', 'Total ratings', '# Ratings', rowLabels, rowValues, True)
                        

def appRatingsGain(appID):
    
    cur = conn.cursor()
    cur.execute("""SELECT SUBSTR(hdate, 0, 11), MAX(ratings)
                FROM app_details_history
                WHERE appid = '""" + str(appID) + """'
                GROUP BY SUBSTR(hdate, 0, 11)
                ORDER BY SUBSTR(hdate, 0, 11)""")
    appRatings = cur.fetchall()
    
    # Calculation time
    
    rowOld = []
    
    rowsValid = []
    
    for row in appRatings:
        if len(rowOld) == 0:
            rowOld = [row[0], row[1]]
            
        if row[0] > rowOld[0]:
            rowsValid.append(row)
            
    # Now start subtracting
    
    interval = 7
    intervalCurrent = 0
    
    rowOld = []
    rowsValidFinal = []
    rowGain = 0

    for row in rowsValid:
        if len(rowOld) == 0:
            rowOld = [row[0], row[1]]
        else:
            rowGain = rowGain + (row[1] - rowOld[1])
            
        rowOld = [row[0], row[1]]
        
        intervalCurrent += 1
        
        if intervalCurrent == interval:
            rowsValidFinal.append([row[0], rowGain])
            rowGain = 0
            intervalCurrent = 0


    rowLabels = '['
    rowValues = '['
    
    for row in rowsValidFinal:
        rowLabels += "'" + row[0] + "',"
        rowValues += str(row[1]) + ","
            
    rowLabels = rowLabels[:-1] + ']'
    rowValues = rowValues[:-1] + ']'
            
    # Now start substracting
        
    return chartCreator('AppRatingsGain', 'Ratings gained', '# Ratings', rowLabels, rowValues, True)
                        

def appScore(appID):
    
    cur = conn.cursor()
    cur.execute("""SELECT SUBSTR(hdate, 0, 11), MAX(score)
                FROM app_details_history
                WHERE appid = '""" + str(appID) + """'
                GROUP BY SUBSTR(hdate, 0, 11)
                ORDER BY SUBSTR(hdate, 0, 11)""")
    appRatings = cur.fetchall()
    
    rowLabels = '['
    rowValues = '['
    
    interval = 7
    intervalCurrent = 0
    
    for row in appRatings:
        intervalCurrent += 1
        
        if intervalCurrent == interval:
            rowLabels += "'" + row[0] + "',"
            rowValues += str(row[1]) + ","
            intervalCurrent = 0
            
    rowLabels = rowLabels[:-1] + ']'
    rowValues = rowValues[:-1] + ']'
            
    # Now start substracting
        
    return chartCreator('AppScore', 'Score evolution', 'Score (%)', rowLabels, rowValues, True)


def appPopularity(appID):
    
    cur = conn.cursor()
    cur.execute("""SELECT SUBSTR(hdate, 0, 11), MAX(popularity)
                FROM app_details_history
                WHERE appid = '""" + str(appID) + """'
                GROUP BY SUBSTR(hdate, 0, 11)
                ORDER BY SUBSTR(hdate, 0, 11)""")
    appRatings = cur.fetchall()
    
    rowLabels = '['
    rowValues = '['
    
    interval = 7
    intervalCurrent = 0
    
    for row in appRatings:
        intervalCurrent += 1
        
        if intervalCurrent == interval:
            rowLabels += "'" + row[0] + "',"
            rowValues += str(row[1]) + ","
            intervalCurrent = 0
            
    rowLabels = rowLabels[:-1] + ']'
    rowValues = rowValues[:-1] + ']'
            
    # Now start substracting
        
    return chartCreator('AppPopularity', 'Popularity (Average # ratings received since release)', 'Popularity', rowLabels, rowValues, True)
        

def chartCreator(chartName, chartTitle, labelDesc, labels, values, beginatzero):
    
    if beginatzero == True:
        bgz = 'true'
    else:
        bgz = 'false'
    
    html = """<canvas id='""" + chartName + """' style=""></canvas>
                <script>
                var """ + chartName + """ctx = document.getElementById('""" + chartName + """').getContext('2d');
                
                Chart.defaults.color = 'rgba(255, 255, 255, 0.75)'
                Chart.defaults.font.family = 'Segoe UI Regular'
                
                var """ + chartName + """ = new Chart(""" + chartName + """ctx, {
                    type: 'bar',
                    color: '#ffffff',
                    data: {
                        labels: """ + labels + """,
                        datasets: [{
                            label: '""" + labelDesc + """',
                            data: """ + values + """,
                            borderWidth: 1,
                            normalized: true,
                            backgroundColor: [ 'rgb(65, 138, 247)' ],
                            borderColor: 'rgb(65, 138, 247)',
                        }]
                    },
                    options: {
                        scales: {
                            y: {
                                beginAtZero: """ + bgz + """
                            }
                        },
                        layout: {
                            padding: 10
                        },
                        plugins: {
                            datalabels: {
                                color: '#ffffff'
                            },
                            title: {
                              display: true,
                              text: '""" + chartTitle + """',
                              color: '#ffffff',
                              font: {
                                size: 20,
                                weight: 'normal'
                              }
                            }
                        }
                    }
                });
                </script>"""
                
    return html

# Web functions
    
def dataToStatistics(conn, appTitle, appID):
    
    print("Generating statistics for " + appTitle + " (" + str(appID) + ")")
    
    title = 'Oculus Quest - App history'
    
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
          <script type="text/javascript" src="https://cdn.jsdelivr.net/npm/chart.js@3.2.1/dist/chart.min.js"</script>
          
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

    html += '<h1><img src="/oculus/images/quest.png" height="40" width="183"></h1>'
    html += '<h2>App History</h2>'
    html += '<p style="font-size: 20px;">Historical statistics for <b>' + appTitle + '</b>'
    html += '<p>Charts are summarized on a weekly basis. Occasional gaps may be present due to crawler outage.</p>'
    
    html += '<div class="statistics-container" style="grid-template-columns: repeat(auto-fit, minmax(600px, 1fr));">'
    
    html += '<div class="statistics-table">' + appRatingsTotal(appID) + '</div>'
    html += '<div class="statistics-table">' + appRatingsGain(appID) + '</div>'
    html += '<div class="statistics-table">' + appScore(appID) + '</div>'
    html += '<div class="statistics-table">' + appPopularity(appID) + '</div>'

    html += '</div>'
    
    html += '</div></body></html>' 
    
    filename = str(appID) + '.html'
    
    file = open(htmlDir + filename, 'wb')
    file.write(html.encode('utf-8'))
    file.close()


mainDir    = "/VRDB"
htmlDir    = "/var/www/html/quest/history/"
imageDir    = "/var/www/html/oculus/images/"

os.chdir(mainDir)

conn = create_connection("vrdb.db")

cur = conn.cursor()
cur.execute("""SELECT ad.title, ad.appid FROM app_details AS ad
            INNER JOIN app_index AS AI on ad.appid = AI.appid WHERE region = 'us' AND platform IN ('quest','lab')
            AND ad.appid IN (SELECT appid FROM app_details_history)
            AND rdate < DATE('now', '-1 month')""")
apps = cur.fetchall()

for app in apps:
    dataToStatistics(conn, app[0], app[1])

conn.close()
        
        
        





