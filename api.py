from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict  # Added import

app = FastAPI(title="Form Autofiller API")

class UserRegistration(BaseModel):
    username: str
    email: str
    password: str

@app.post("/register/")
async def register_user(user: UserRegistration):
    try:
        # Check if user already exists (pseudo-code)
        # existing_user = await get_user_by_email(user.email)
        # if existing_user:
        #     raise HTTPException(status_code=400, detail="User already exists")

        # Hash the password (pseudo-code)
        # hashed_password = hash_password(user.password)

        # Save user to the database (pseudo-code)
        # await save_user_to_db(username=user.username, email=user.email, password=hashed_password)

        return {"message": "User registered successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
