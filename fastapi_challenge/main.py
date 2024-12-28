from fastapi import FastAPI, HTTPException, Header, Request
from pydantic import BaseModel
from typing import Optional, List
from fastapi.responses import RedirectResponse, JSONResponse
from starlette.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from contextlib import asynccontextmanager

limiter = Limiter(key_func=get_remote_address)

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.limiter = limiter
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins = ["*"], 
    allow_credentials = True,
    allow_methods = ["GET", "POST"],
    allow_headers = ["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    print(f"HTTP {request.method} Request to {request.url.path} (sanitized)")
    try:
        response = await call_next(request)
    except Exception as e:
        print(f"Error during request processing: {str(e)}")
        raise
    return response

# Define a Pydantic model for the request body
class Portfolio(BaseModel):
    name: Optional[str] = None
    school: Optional[str] = None
    major: Optional[str] = None
    minor: Optional[str] = None
    hobbies: Optional[List[str]] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None

@app.get("/")
def redirect_to_main_page():
    # Redirect root to /portfolio with a temporary redirect
    return RedirectResponse(url="/portfolio", status_code=307)

@app.get("/portfolio")
@limiter.limit("5/minute")
def submit_details_get(
    request: Request,
    name: Optional[str] = None,
    school: Optional[str] = None,
    major: Optional[str] = None,
    minor: Optional[str] = None,
    hobbies: Optional[str] = None, 
    linkedin: Optional[str] = None,
    github: Optional[str] = None,
    user_agent: str = Header(None)
):
    if user_agent and "bot" in user_agent.lower():
        raise HTTPException(status_code=403, detail="Bots are not allowed")

    hobbies_list = hobbies.split(",") if hobbies else []

    response = JSONResponse(
        {
            "message": "GET request received successfully!",
            "data": {
                "name": name or "Anonymous",
                "school": school or "Not Specified",
                "major": major or "Not Specified",
                "minor": minor or "Not Specified",
                "hobbies": hobbies_list,
                "linkedin": linkedin or "Not Provided",
                "github": github or "Not Provided",
            }
        }
    )
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response

@app.post("/portfolio")
@limiter.limit("10/minute")
def submit_details(request: Request, details: Portfolio):
    if not details.name or not details.school or not details.major:
        raise HTTPException(status_code=400, detail="Name, school, and major are required fields.")

    return {
        "message": "Details received successfully!",
        "data": {
            "name": details.name,
            "school": details.school,
            "major": details.major,
            "minor": details.minor,
            "hobbies": details.hobbies,
            "linkedin": details.linkedin,
            "github": details.github,
        }
    }

@app.get("/v1/portfolio")
def submit_details_v1():
    return {"message": "API Version 1"}

@app.get("/v2/portfolio")
def submit_details_v2():
    return {"message": "API Version 2 with improved features!"}

@app.exception_handler(RateLimitExceeded)
async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"message": "Rate limit exceeded. Please try again later."},
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"message": "An internal server error occurred. Please try again later."},
    )
