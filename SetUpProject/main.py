from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional
import uuid
import datetime

app = FastAPI(
    title="User Management Service",
    description="API for managing users with CRUD operations",
    version="1.0.0"
)

# In-memory storage for users
users_db = {}


class UserBase(BaseModel):
    name: str
    email: EmailStr
    age: Optional[int] = None


class UserCreate(UserBase):
    pass


class UserInResponse(UserBase):
    id: str
    created_at: datetime.datetime
    updated_at: datetime.datetime


@app.get("/")
async def root():
    return {"message": "User Management Service API", "version": "1.0.0"}


@app.get("/users", response_model=list[UserInResponse], tags=["users"])
async def get_users(skip: int = 0, limit: int = 100):
    """
    Get all users or a paginated list of users
    
    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records to return (default: 100)
    """
    if limit < 0:
        raise HTTPException(status_code=400, detail="Limit must be non-negative")
    
    users = list(users_db.values())
    paginated_users = users[skip:skip + limit]
    
    return paginated_users


@app.get("/users/{user_id}", response_model=UserInResponse, tags=["users"])
async def get_user(user_id: str):
    """
    Get a single user by ID
    
    - **user_id**: The unique identifier of the user to retrieve
    """
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="User not found")
    
    return users_db[user_id]


@app.post("/users", response_model=UserInResponse, tags=["users"])
async def create_user(user: UserCreate):
    """
    Create a new user
    
    - **name**: User's full name (required)
    - **email**: Email address (required, must be valid email format)
    - **age**: Age (optional, defaults to null)
    """
    global users_db
    
    # Check if user with this email already exists
    for existing_user in users_db.values():
        if existing_user.email == user.email:
            raise HTTPException(
                status_code=400,
                detail=f"Email '{user.email}' is already registered"
            )
    
    # Generate unique ID
    new_id = str(uuid.uuid4())
    created_at = datetime.datetime.now(datetime.timezone.utc)
    
    # Create user object
    new_user = UserInResponse(
        id=new_id,
        name=user.name,
        email=user.email,
        age=user.age,
        created_at=created_at,
        updated_at=created_at
    )
    
    # Store in database
    users_db[new_id] = new_user
    
    return new_user


@app.put("/users/{user_id}", response_model=UserInResponse, tags=["users"])
async def update_user(user_id: str, user: UserCreate):
    """
    Update an existing user
    
    - **user_id**: The unique identifier of the user to update
    - **name**: User's full name (optional)
    - **email**: Email address (optional, must be valid email format)
    - **age**: Age (optional)
    """
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="User not found")
    
    existing_user = users_db[user_id]
    
    # Check if the new email already exists for another user
    if user.email != existing_user.email:
        for uid, existing in users_db.items():
            if uid != user_id and existing.email == user.email:
                raise HTTPException(
                    status_code=400,
                    detail=f"Email '{user.email}' is already registered"
                )
    
    # Update user data
    updated_user = UserInResponse(
        id=user_id,
        name=user.name,
        email=user.email,
        age=user.age,
        created_at=existing_user.created_at,
        updated_at=datetime.datetime.now(datetime.timezone.utc)
    )
    
    users_db[user_id] = updated_user
    
    return updated_user


@app.delete("/users/{user_id}", tags=["users"])
async def delete_user(user_id: str):
    """
    Delete a user by ID
    
    - **user_id**: The unique identifier of the user to delete
    """
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="User not found")
    
    del users_db[user_id]
    
    return {"message": f"User {user_id} deleted successfully"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
