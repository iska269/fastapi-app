from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"],deprecated="auto")

# Hacher le mot de passe

def hashing_password(password):
    return pwd_context.hash(password)

# Verify password

def verify_password(password,hashed_password):
    return pwd_context.verify(password,hashed_password)