# Development function, already included in main
import yaml
def create_anno_list():
    newlist = ["clinvar"]
    configIn = {
        "run": { 
            "annotators": [ "clinvar", "go" ],
            "liftover": "hg38" ,
            "endat": "postaggregator",
        }
    }
    configOut = yaml.dump(configIn)
    yamlret = yaml.load(configOut, Loader=yaml.FullLoader)
    yamlret['run']['annotators'] = newlist

