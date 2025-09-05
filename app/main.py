from fastapi import FastAPI,Depends,HTTPException
from fastapi.security import OAuth2PasswordBearer
import os
from pydantic import BaseModel,Field,EmailStr
from fastapi.middleware.cors import CORSMiddleware
from app.recherche import recherche,generate_id
from datetime import datetime, timedelta, timezone
import jwt
from jwt.exceptions import InvalidTokenError
from contextlib import asynccontextmanager
from app.db import pool,create_table,add_new_administrator,login_administrator,save_json_file,call_content,update_content,call_administrator,delete_admin,verify_email
from app.encrypt import hashing_password,verify_password
from app.createjson import fichier_json


@asynccontextmanager
async def lifespan(app: FastAPI):
    await pool.open(wait=True)
    await create_table()
    await save_json_file(fichier_json)
    yield
    await pool.close()

app = FastAPI(lifespan=lifespan)

origins = [
    "https://fablab-1.onrender.com", 
    "https://fablabadmin.onrender.com",

]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,          # ou ["*"] pour tout autoriser
    allow_credentials=True,
    allow_methods=["*"],            # ["GET", "POST", "DELETE"] si tu veux limiter
    allow_headers=["*"],            # autorise tous les headers
)
SECRET_KEY = os.getenv("MY_SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHME")
oauth2_sheme = OAuth2PasswordBearer(tokenUrl="login")


class Materiaux(BaseModel):
    materiaux: str
    atelier: str
    nombre: int = Field(default=1, ge=1)
class Emprunts(BaseModel):
    id: int = Field(default_factory=generate_id)
    nom: str
    numero: int
    materiaux: list[dict]
class Token(BaseModel):
    acces_token: str
    type_token: str
class UserSign(BaseModel):
    email: EmailStr
    name: str
    password: str
    is_super_admin: bool=Field(default=False)
class UserLog(BaseModel):
    email: EmailStr
    password: str




def create_token(data: dict,expire_delta: timedelta | None = None):
    to_encode = data.copy()
    if expire_delta:
        expire = datetime.now(timezone.utc) + expire_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=30)
    to_encode.update({"exp":expire})
    encoded_jwt = jwt.encode(to_encode,SECRET_KEY,algorithm=ALGORITHM)
    return encoded_jwt
def verify_token(token):
    try:
        payload = jwt.decode(token,SECRET_KEY,algorithms=[ALGORITHM])
        return payload
    except InvalidTokenError:
        raise HTTPException(status_code=401,detail="Le token est invalid ou expiré")
def get_current_user(token: str = Depends(oauth2_sheme)):
    payload = verify_token(token)
    return payload





@app.get("/")
async def bienvenue():
    return {"message":"Bonjour depuis le backend ! "}

@app.get("/front")
async def get_front_end():
    data = await call_content()
    return data    

@app.post("/ajoutermateriaux")
async def add_materials(
    materiaux: Materiaux,
    current_user: dict = Depends(get_current_user)
):
    data = await call_content()
    atelier = materiaux.atelier
    nom = materiaux.materiaux.strip().lower()
    nombre = materiaux.nombre

    if atelier not in data:
        data[atelier] = []

    found = False
    for item in data[atelier]:
        if item["materiaux"].strip().lower() == nom:
            item["nombre"] += nombre
            found = True
            break

    if not found:
        data[atelier].append({
            "materiaux": materiaux.materiaux.strip(),
            "nombre": nombre
        })

    await update_content(data)

    return {
        "message": "Matériau incrémenté" if found else "Nouveau matériau ajouté",
        "atelier": atelier,
        "materiaux": materiaux.materiaux,
        "nombre": nombre
    }
 
        
@app.post("/ajouteremprunts")
async def add_emprunts(emprunts: Emprunts,current_user:dict = Depends(get_current_user) ):
    data = await call_content()
    data["emprunts"].append({"id":emprunts.id,"nom":emprunts.nom,"numero":emprunts.numero,"materiaux":emprunts.materiaux})
    await update_content(data)
    return {"message": "Emprunt ajouté !"}

@app.delete("/supprimermateriaux/{atelier}/{materiaux}")
async def delete_materiaux(
    atelier: str, 
    materiaux: str,
    current_user: dict = Depends(get_current_user)
):
    data = await call_content()
    found = False

    # On crée une nouvelle liste pour éviter les problèmes d'itération
    nouvelle_liste = []
    for item in data.get(atelier, []):
        if item["materiaux"].strip().lower() == materiaux.strip().lower():
            found = True
            if item["nombre"] > 1:
                item["nombre"] -= 1
                nouvelle_liste.append(item)
            # sinon on ne remet pas l’item (il est supprimé complètement)
        else:
            nouvelle_liste.append(item)

    data[atelier] = nouvelle_liste
    await update_content(data)

    if found:
        return {"message": "Matériau supprimé ou décrémenté"}
    else:
        return {"message": "Aucun matériau trouvé"}


@app.delete("/supprimeremprunts/{id_emprunts}")
async def delete_emprunts(id_emprunts: int,current_user:dict = Depends(get_current_user) ):
    data = await call_content()
    for i, num in enumerate(data["emprunts"]):
        if num["id"] == id_emprunts:
            del data["emprunts"][i]
            break
    await update_content(data)
    return {"message": "Suppression effectué !"}


# Routes pour l'authentification

@app.post("/signin")
async def sign_in(user: UserSign, current_user:dict = Depends(get_current_user)):
    if current_user["role"] != "super admin":
       raise HTTPException(status_code=403,detail="Vous n'êtes pas autorisé á faire cette requete")
    email = user.email
    name = user.name
    is_super_admin = user.is_super_admin
    hashed_password = hashing_password(user.password)
    verify = await verify_email(email)
    if verify:
        return {"message":"Cette email existe deja"}
    result = await add_new_administrator(email,name,hashed_password,is_super_admin)
    # what do with the id admin
    return {"message": "Admintrateur ajouté !"}

@app.post("/login")
async def login(user: UserLog):
    email = user.email
    password = user.password
    data = await login_administrator(email)
    if data:
        if verify_password(password,data[0][3]):
            if data[0][4]:
                role = "super admin"
            else:
                role = "admin"
            token = create_token({"id":data[0][0],"nom":data[0][2],"role":role})
            return{"message": "Connection réussi !","token":token}
        else:
            return {HTTPException(status_code=401,detail="Identifiants non reconnu")}
    else:
        return {HTTPException(status_code=401,detail="Identifiants non reconnu")}
    
# Routes de gestion du super admin

@app.get("/administrator/read")
async def get_administrator(current_user:dict = Depends(get_current_user)):
    if current_user["role"] != "super admin":
       raise HTTPException(status_code=403,detail="Vous n'êtes pas autorisé á faire cette requete")
    liste = await call_administrator()
    return {"liste": liste}

@app.delete("/administrator/delete/{id_admin}")
async def del_administrator(id_admin: int,current_user:dict = Depends(get_current_user)):
    if current_user["role"] != "super admin":
       raise HTTPException(status_code=403,detail="Vous n'êtes pas autorisé á faire cette requete")
    await delete_admin(id_admin)
    return {"message":True}



