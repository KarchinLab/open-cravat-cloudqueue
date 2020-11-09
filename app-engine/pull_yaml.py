# Development function, already included in main
import requests
import yaml

url = 'https://karchinlab.org/cravatstore/manifest.yml'
data = requests.get(url)
out = data.content
currentvals = yaml.load(out, Loader=yaml.FullLoader)

annolist = list()
agglist = list()
postagglist = list()

for i in currentvals.keys():
    if currentvals[i]['type'] == 'annotator':
        annolist.append(i)
    elif currentvals[i]['type'] == 'aggregator':
        agglist.append(i)
    elif currentvals[i]['type'] == 'postaggregator':
        postagglist.append(i)
    else:
        pass

print(annolist)
print(agglist)
print(postagglist)

    

