import time


def recherche(item: str,table: list,value: str):
    response = False
    for i in range(len(table)):
        if item == table[i-1][value]:
            response = True
        break
    return response

def generate_id():
    return int(time.time()*1000)