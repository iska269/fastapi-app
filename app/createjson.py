import json


fichier_json = {
        "arduino":[],
        "developpement web": [],
        "couture":[],
        "3d":[],
        "laser":[],
        "emprunts":[]
}

with open("fichier.json","w") as f:
    json.dump(fichier_json,f,indent=4)