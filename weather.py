import collections
import re
import requests
from bs4 import BeautifulSoup

def flatten(dictionary, parent_key=False, separator='.'):
    """
    Turn a nested dictionary into a flattened dictionary
    :param dictionary: The dictionary to flatten
    :param parent_key: The string to prepend to dictionary's keys
    :param separator: The string used to separate flattened keys
    :return: A flattened dictionary
    """

    items = []
    for key, value in dictionary.items():
        new_key = str(parent_key) + separator + key if parent_key else key
        if isinstance(value, collections.MutableMapping):
            items.extend(flatten(value, new_key, separator).items())
        elif isinstance(value, list):
            for k, v in enumerate(value):
                items.extend(flatten({str(k): v}, new_key).items())
        else:
            items.append((new_key, value))
    return dict(items)


fc = requests.get("https://api.openweathermap.org/data/2.5/forecast?lat=49.08&lon=8.48&lang=de&units=metric&appid=3388a895b0152c1380e50ec40fa1e69f").json()
print(flatten(fc['list'][0]))
for entry in fc['list'][:10]:
    print("%s: %s (%s/%s)" % (entry['dt_txt'], entry['clouds'], entry['weather'][0]['main'], entry['weather'][0]['description']))


#####################################
#       W E T T E R . C O M         #
#####################################

wc = requests.get("https://www.wetter.com/deutschland/stutensee/staffort/DE0010286005.html")
soup = BeautifulSoup(wc.text, 'html.parser')
mydiv = soup.find("table", {"class": "weather-overview mb mt"})

wc = []
for idx1, rows in enumerate(mydiv.find_all('tr')):
    print("-"*50)
    wc.append([])
    for idx2, tds in enumerate(rows.find_all('td')):
        row = []
        if tds.find_all(True):
            for idx3, tds_inhalt in enumerate(tds.find_all(True)):
                try:
                    value = tds_inhalt.contents[0].strip()
                    # remove first value if [|/] + strip()
                    if value:
                       value = re.sub(r'^[|/]', '', value).strip()
                    if value:
                        row.append(value)
                    print("%d, %d, %d (2): >>>%s<<<" % (idx1, idx2, idx3, value))
                except:
                    pass
        else:
            value = tds.contents[0].strip()
            if value:
                row.append(value)
            print("%d, %d, %d (1): >>>%s<<<" % (idx1, idx2, idx3, value))
        print(row)
        print("")
        if row:
            wc[idx1].append(row)

# idx1 == 0  # collect date
#
tageesverlauf = mydiv.find_all("div", {"class": "text--bold"})

# Sonnenstunden aus text, vielleicht reicht das auch aus
ssd = soup.find("p", {"class": "mb- no-decoration"})
ssd_text = ssd.text.strip()  # u'Heute werden bis zu 10 Sonnenstunden erwartet'
match = re.search(r"zu (?P<ss>\d{1,2}) Sonnenstunden", ssd_text)
ssd_num = 0
if match and match.group('ss'):
    ssd_num = int(match.group('ss'))
print("Anzahl zu erwartender Sonnenstunden: %r" % ssd_num)


