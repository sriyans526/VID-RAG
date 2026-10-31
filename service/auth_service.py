import os, hashlib, hmac, secrets
from datetime import datetime, timedelta, timezone
import jwt

def _secret():
    secret=os.getenv("JWT_SECRET","")
    if len(secret)<32 or secret.startswith("replace-with"):
        raise RuntimeError("Set JWT_SECRET to a random value of at least 32 characters in .env.")
    return secret

def hash_password(password):
    salt=secrets.token_bytes(16)
    digest=hashlib.scrypt(password.encode(),salt=salt,n=2**14,r=8,p=1)
    return salt.hex()+"$"+digest.hex()

def verify_password(password, encoded):
    try:
        salt,digest=encoded.split("$",1)
        check=hashlib.scrypt(password.encode(),salt=bytes.fromhex(salt),n=2**14,r=8,p=1).hex()
        return hmac.compare_digest(check,digest)
    except (ValueError,TypeError):
        return False

def create_access_token(user_id,email):
    exp=datetime.now(timezone.utc)+timedelta(minutes=int(os.getenv("JWT_EXPIRE_MINUTES","1440")))
    return jwt.encode({"sub":str(user_id),"email":email,"exp":exp},_secret(),algorithm="HS256")

def decode_access_token(token):
    return jwt.decode(token,_secret(),algorithms=["HS256"])
