import urllib.request, urllib.error
from FollowerDataCollection.API import TwitterURL
import json
import ssl
import sqlite3
from scipy import stats

def end_handler():
    if cursor > 0:
        cur.execute('''INSERT OR IGNORE INTO Cursor (cursor) VALUES (?)''', (cursor,))
    conn.commit()
    if not remaining:
        print('\nyou ran out of pulls')
    elif int(remaining) <= 0:
        print('\nyou ran out of pulls')
    else:
        print('\nyou pulled all of the data')
        print('You have this many pulls left from Twitter API: ' + headers['x-rate-limit-remaining'])
    print('# of users pulled: ' + str(total))

conn = sqlite3.connect('followdata.sqlite')
cur = conn.cursor()

# Ignore SSL certificate errors
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

while True:
    acct = input('Enter your twitter account: ')
    confirm = input('Is your account "' + acct + '", yes or no: ')
    if len(acct) > 0 and confirm == 'yes':
        break
    else:
        print('Please enter your actual account')

print('Welcome to my twitter follower management system')
TWITTER_URL = 'https://api.twitter.com/1.1/followers/list.json'
if input('Are you planning on retrieving any data today? ') == 'yes':
    if input('Is this search for the previous user (yes/no): ') == 'no':
       cur.execute('DROP TABLE IF EXISTS FollowerData')
       cur.execute('DROP TABLE IF EXISTS Users')
       cur.execute('DROP TABLE IF EXISTS Location')
       cur.execute('DROP TABLE IF EXISTS Cursor')
       cur.execute('''CREATE TABLE FollowerData
                   (name_id INTEGER, verified INTEGER, followers_count INTEGER, location_id INTEGER)''')
       cur.execute('''CREATE TABLE Users
                    (id INTEGER PRIMARY KEY, name TEXT UNIQUE, username TEXT UNIQUE)''')
       cur.execute('''CREATE TABLE Location
                   (id INTEGER PRIMARY KEY, name TEXT UNIQUE, count INTEGER)''')
       cur.execute('''CREATE TABLE Cursor (cursor INTEGER UNIQUE)''')

    remaining = None
    cur.execute('''SELECT cursor from Cursor''')
    previous_cursors = cur.fetchall()
    print(previous_cursors)
    if str(previous_cursors) == '[]':
        cursor = -1
    else:
        cursor = previous_cursors[-1][0]
    print(cursor)

    total = 0

    while cursor != 0:
        if cursor == -1:
            url = TwitterURL.augment(TWITTER_URL, {'screen_name' : acct, 'count' : '200'})
        else:
            url = TwitterURL.augment(TWITTER_URL, {'screen_name' : acct, 'cursor' : cursor, 'count' : '200'})
        print(url)
        try:
            connection = urllib.request.urlopen(url, context=ctx)
            headers = dict(connection.getheaders())
            data = connection.read().decode()
            remaining = headers['x-rate-limit-remaining']

        except:
            break

        js = json.loads(data)

        cursor = js['next_cursor']
        cur.execute('''INSERT OR IGNORE INTO Cursor (cursor) VALUES (?)''', (cursor,))

        count = 0
        for x in js['users']:
            try:
                count += 1
                if count % 20: conn.commit()

                name = x['name']
                username = x['screen_name']
                location = x['location']
                verified = x['verified']
                followers_count = x['followers_count']

                if verified:
                    verified = 1
                else:
                    verified = 0

                print(name + " | " + username + " | " + location + " | " + str(verified))

                cur.execute('''INSERT OR IGNORE INTO Users (name, username) VALUES (?, ?)''', (name, username))
                cur.execute('''SELECT id FROM Users WHERE name = ?''', (name,))
                name_id = cur.fetchone()[0]

                row = cur.execute('''SELECT count FROM Location WHERE name = ?''', (location,))
                try:
                    count = cur.fetchone()[0]
                    cur.execute('''UPDATE Location SET count = ? WHERE name = ?''', (count + 1, location))
                except TypeError:
                    cur.execute('''INSERT OR IGNORE INTO Location (name, count) VALUES (?, 1)''', (location,))

                cur.execute('''SELECT id FROM Location WHERE name = ?''', (location,))
                location_id = cur.fetchone()[0]

                cur.execute('''INSERT OR REPLACE INTO FollowerData (name_id, verified, followers_count, location_id)
                   VALUES (?, ?, ?, ?)''', (name_id, verified, followers_count, location_id))

                total += 1
            except KeyboardInterrupt:
                cur.execute('''INSERT OR IGNORE INTO Cursor (cursor) VALUES (?)''', (cursor,))
                cursor = 0
                break

    end_handler()

    conn.commit()
    cur.close()

if input('Do you want to analyze your data today? ') == 'yes':

    conn = sqlite3.connect('followdata.sqlite')
    cur = conn.cursor()

    cur.execute('SELECT * from FollowerData')
    if len(cur.fetchall()) > 0:

        NEW_TWITTER_URL = 'https://api.twitter.com/1.1/users/search.json'

        url = TwitterURL.augment(NEW_TWITTER_URL, {'q':acct, 'page': '1'})
        connection = urllib.request.urlopen(url, context=ctx)
        headers = dict(connection.getheaders())
        data = connection.read().decode()

        js = json.loads(data)

        cur.execute('''SELECT Users.name, FollowerData.verified, FollowerData.followers_count, Location.name, Location.count
        FROM Users JOIN FollowerData JOIN Location 
        ON FollowerData.name_id = Users.id AND FollowerData.location_id = Location.id
        ORDER BY FollowerData.followers_count DESC''')
        by_follower_list = cur.fetchall()

        max_followers_name = by_follower_list[0][0]
        max_followers_num = by_follower_list[0][2]
        min_followers_num = by_follower_list[-1][2]


        cur.execute('''SELECT Users.name, FollowerData.verified, FollowerData.followers_count, Location.name, Location.count
        FROM Users JOIN FollowerData JOIN Location 
        ON FollowerData.name_id = Users.id AND FollowerData.location_id = Location.id
        ORDER BY Location.name ASC''')

        by_location_name = {}
        by_location_name_short = {}
        location_data = cur.fetchall()
        for x in location_data:
            if x[3] not in by_location_name.keys() and x[3].isalpha():
                by_location_name[x[3]] = x[4]
        for x,y in by_location_name.items():
            if len(by_location_name_short) >= 20:
                break
            by_location_name_short[x] = y


        by_location_count = {}
        by_location_count_short = {}

        cur.execute('''SELECT Users.name, FollowerData.verified, FollowerData.followers_count, Location.name, Location.count
        FROM Users JOIN FollowerData JOIN Location 
        ON FollowerData.name_id = Users.id AND FollowerData.location_id = Location.id
        ORDER BY Location.count DESC''')

        location_data = cur.fetchall()
        for x in location_data:
            if x[3] not in by_location_count.keys():
                by_location_count[x[3]] = x[4]
        for x,y in by_location_count.items():
            if len(by_location_count_short) >= 20:
                break
            by_location_count_short[x] = y


        location = js[0]['location']
        if location in by_location_count.keys():
            comparison = [location, by_location_count[location]]
        else:
            comparison = [location, ""]

        if comparison[0] == '':
            comparison[0] = "Not Specified"

        verified = len([x for x in location_data if x[1] == 1])

        num_of_followers = js[0]['followers_count']

        cur.execute('''SELECT Users.name, FollowerData.verified, FollowerData.followers_count, Location.name, Location.count
        FROM Users JOIN FollowerData JOIN Location 
        ON FollowerData.name_id = Users.id AND FollowerData.location_id = Location.id
        ORDER BY FollowerData.followers_count DESC''')

        by_follower_count = [x[2] for x in cur]

        percentile = stats.percentileofscore(by_follower_count, num_of_followers, kind='weak')

        rank = 1
        counter = 0
        while num_of_followers < by_follower_count[counter]:
            rank += 1

        fhand = open('analyze.js', 'w')
        fhand.write('analysis = {\n"account_searched":' + str(acct) + ',\n"followers":' + str(num_of_followers))
        fhand.write(',\n"location_count":' + str(comparison) + '\n"percentile_ranking":' + str(percentile) + '\n"numerical_ranking":' + str(rank))
        fhand.write(',\n"most_popular_location":' + str([list(by_location_count.keys())[1], by_location_count[list(by_location_count.keys())[1]]]) + ',\n"verified_count":' + str(verified))
        fhand.write(',\n"location_data_by_count_full":' + str(json.dumps(by_location_count, indent = 4)) + ',\n"location_data_by_count_short":' + str(json.dumps(by_location_count_short, indent = 4)))
        fhand.write(',\n"location_data_by_name_full":' + str(json.dumps(by_location_name, indent = 4)) + ',\n"location_data_by_name_short":' + str(json.dumps(by_location_name_short, indent = 4)) + '}')
        fhand.close()

        print("""USER DATA:
        
Account name: """ + str(acct) + """
Followers: """ + str(num_of_followers) + """
Region: """ + str(comparison[0]) + """
Followers in region: """ + str(comparison[1]) + """
# of verified: """ + str(verified) + """
Most popular follower and number of followers: """ + str(max_followers_name) + " with " + str(max_followers_num) + """ followers.

You are ranked """ + str(rank) + """ out of all your followers 
and are in the """ + str(percentile) + """ percentile.
        
Most influenced location: """ + str(list(by_location_count.keys())[1]) + """  |  location count: """ + str(by_location_count[list(by_location_count.keys())[1]]) + """
Top 20 locations based on count: """)
        for x,y  in by_location_count_short.items():
            if x != '':
                print(str(x) + "  |  " + str(y))
        print('\nTop 20 locations based on alphabetical order: ')
        for x, y in by_location_name_short.items():
            if x != '':
                print(str(x) + "  |  " + str(y))
    else:
        print('can\'t analyse this database')
