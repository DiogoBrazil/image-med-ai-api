from fastapi import APIRouter, Request
from typing import Optional
from ..controllers.user_controller import UserController
from ..interfaces.create_user import CreateUser
from ..interfaces.update_user import UpdateUser
from ..interfaces.login_user import LoginUser
from ..interfaces.create_subscriptions import CreateSubscriptions

router = APIRouter(
    prefix="/api/users",
    tags=["users"],
    responses={404: {"description": "Not found"}},
)

user_controller = UserController()

@router.post("/", status_code=201, summary="Create new user")
async def create_user(request: Request, user: CreateUser):
    """
    Creates a new user in the system.
    
    - **Requires administrator profile**
    - Administrator can only create users associated with them
    
    Returns the details of the created user.
    """
    return await user_controller.add_user(request, user)

@router.post("/login", summary="User login")
async def login(request: Request, user: LoginUser):
    """
    Authenticates a user and returns a JWT token.
    
    - **Does not require prior authentication**
    - Only requires valid API key
    
    Returns JWT token and basic user information.
    """
    return await user_controller.login_user(request, user)

@router.get("/", summary="List users")
async def get_users(request: Request, admin_id: Optional[str] = None):
    """
    Lists users in the system.
    
    - **Administrators**: Can see users linked to them
    - **Professionals**: Can see users with the same admin_id
    
    Optional parameters:
    - **admin_id**: Filter by specific administrator
    
    Returns list of users.
    """
    return await user_controller.get_users(request, admin_id)

@router.get("/administrators/list", summary="List administrators")
async def get_administrators(request: Request):
    """
    Lists all users with administrator profile.
    
    - **Requires administrator profile**
    
    Returns list of administrators.
    """
    return await user_controller.get_administrators(request)

@router.get("/professionals/list", summary="List professionals")
async def get_professionals(request: Request, admin_id: Optional[str] = None):
    """
    Lists healthcare professionals.
    
    - **Administrators**: Can see professionals linked to them
    - **Professionals**: Can see professionals with the same admin_id
    
    Optional parameters:
    - **admin_id**: Administrator ID (if not provided, uses current administrator ID)
    
    Returns list of professionals.
    """
    return await user_controller.get_professionals(request, admin_id)

@router.get("/subscriptions", summary="List subscriptions")
async def get_subscriptions(request: Request):
    """
    Lists all existing subscriptions in the system.
    
    - **Requires general administrator profile**
    - Includes subscriptions of all administrators
    
    Returns list of subscriptions.
    """
    return await user_controller.get_subscriptions(request)

@router.get("/subscriptions/{subscription_id}", summary="Get professional subscription")
async def get_subscription_by_id(request: Request, subscription_id: str):
    """
    Retrieves information about a professional's subscription.
    """
    return await user_controller.get_subscription_by_id(request, subscription_id)


@router.put("/subscriptions/{subscription_id}", summary="Update professional subscription")
async def update_subscription(request: Request, subscription_id: str, subscription: CreateSubscriptions):
    """
    Updates the status of a professional's subscription.
    """
    return await user_controller.update_subscription(request, subscription_id, subscription)


@router.post("/subscriptions", summary="Create professional subscription")
async def create_subscription(request: Request, subscription: CreateSubscriptions):
    """
    Creates a healthcare professional subscription.
    """
    return await user_controller.create_subscription(request, subscription)

@router.get("/{user_id}", summary="Get user by ID")
async def get_user(request: Request, user_id: str):
    """
    Retrieves information about a specific user.
    
    - **Users**: Can only see their own data
    - **Administrators**: Can see data of users linked to them
    
    Returns details of the requested user.
    """
    return await user_controller.get_user_by_id(request, user_id)

@router.put("/{user_id}", summary="Update user")
async def update_user(request: Request, user_id: str, user: UpdateUser):
    """
    Updates information of an existing user.
    
    - **Users**: Can only update their own data
    - **Administrators**: Can update data of users linked to them
    
    Returns update confirmation.
    """
    return await user_controller.update_user(request, user_id, user)

@router.delete("/{user_id}", summary="Remove user")
async def delete_user(request: Request, user_id: str):
    """
    Removes a user from the system.
    
    - **Requires administrator profile**
    - Administrator can only remove users linked to them
    
    Returns removal confirmation.
    """
    return await user_controller.delete_user(request, user_id)