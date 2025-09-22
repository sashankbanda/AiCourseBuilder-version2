from fastapi import FastAPI, APIRouter, HTTPException, Depends, Response, Request, Cookie
from fastapi.security import HTTPBearer
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import requests
import json
import re
from urllib.parse import quote
import asyncio
import aiohttp
from jose import JWTError, jwt
from passlib.context import CryptContext


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Configuration
SECRET_KEY = os.environ.get("JWT_SECRET", "your-secret-key-change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Security
security = HTTPBearer(auto_error=False)


# Authentication Models
class UserBase(BaseModel):
    email: EmailStr
    name: str
    picture: Optional[str] = None

class UserCreate(UserBase):
    password: Optional[str] = None

class UserResponse(UserBase):
    id: str
    created_at: datetime
    courses_enrolled: List[str] = []
    badges: List[str] = []
    streak_count: int = 0
    last_login: Optional[datetime] = None

class UserSession(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    session_token: str
    expires_at: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class EmailPasswordLogin(BaseModel):
    email: EmailStr
    password: str

class SessionResponse(BaseModel):
    id: str
    email: str
    name: str
    picture: Optional[str] = None
    session_token: str

# Course Models
class TopicRequest(BaseModel):
    topic: str
    language: str
    mode: str  # Quick, Detailed, Mixed

class VideoInfo(BaseModel):
    video_id: str
    title: str
    duration: str
    view_count: int
    channel_name: str
    thumbnail_url: str
    engagement_score: float

class Lesson(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    content: str
    video_id: Optional[str] = None
    order: int
    
class Quiz(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    lesson_id: str
    questions: List[Dict[str, Any]]
    
class UserProgress(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None  # Will be set automatically from authenticated user
    course_id: str
    topic: str
    language: str
    mode: str
    lessons_completed: List[str] = []
    quiz_scores: Dict[str, int] = {}
    notes: Dict[str, str] = {}
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
class CourseResponse(BaseModel):
    id: str
    lessons: List[Lesson]
    videos: List[VideoInfo]
    created_at: datetime

class Course(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    topic: str
    language: str
    mode: str
    lessons: List[Lesson]
    videos: List[VideoInfo]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# Authentication Helper Functions
def create_access_token(user_id: str, expires_delta: Optional[timedelta] = None):
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    
    to_encode = {"sub": user_id, "exp": expire}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

async def get_current_user(request: Request, session_token: Optional[str] = Cookie(None)):
    """Get current user from session token (cookie or header)"""
    token = session_token
    
    # Fallback to Authorization header if no cookie
    if not token and hasattr(request, 'headers'):
        auth_header = request.headers.get('authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
    
    if not token:
        return None
    
    try:
        # Check if session exists and is valid
        session = await db.user_sessions.find_one({
            "session_token": token,
            "expires_at": {"$gt": datetime.now(timezone.utc)}
        })
        
        if not session:
            return None
        
        # Get user data
        user = await db.users.find_one({"id": session["user_id"]})
        if user:
            return UserResponse(**user)
        
    except Exception as e:
        logger.error(f"Error getting current user: {str(e)}")
        return None
    
    return None

async def require_auth(current_user: Optional[UserResponse] = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return current_user


# YouTube API functions
async def search_youtube_videos(topic: str, language: str, max_results: int = 5):
    """Search for YouTube videos based on topic and language"""
    try:
        youtube_api_key = os.environ.get('YOUTUBE_API_KEY')
        if not youtube_api_key:
            raise HTTPException(status_code=500, detail="YouTube API key not configured")
        
        # Language mapping for search
        lang_map = {
            'english': 'en',
            'hindi': 'hi', 
            'telugu': 'te',
            'tamil': 'ta'
        }
        
        search_query = f"{topic} tutorial {language}"
        if language.lower() != 'english':
            search_query += f" {language} language"
            
        url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            'part': 'snippet',
            'q': search_query,
            'type': 'video',
            'maxResults': max_results,
            'key': youtube_api_key,
            'order': 'relevance',
            'videoDuration': 'medium'  # 4-20 minutes
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    raise HTTPException(status_code=500, detail="YouTube API error")
                
                data = await response.json()
                
        # Get video details
        video_ids = [item['id']['videoId'] for item in data.get('items', [])]
        video_details = await get_video_details(video_ids)
        
        videos = []
        for item, details in zip(data.get('items', []), video_details):
            # Calculate engagement score
            views = int(details.get('viewCount', 0))
            likes = int(details.get('likeCount', 0))
            engagement_score = (likes / max(views, 1)) * 100 if views > 0 else 0
            
            video_info = VideoInfo(
                video_id=item['id']['videoId'],
                title=item['snippet']['title'],
                duration=details.get('duration', ''),
                view_count=views,
                channel_name=item['snippet']['channelTitle'],
                thumbnail_url=item['snippet']['thumbnails']['medium']['url'],
                engagement_score=engagement_score
            )
            videos.append(video_info)
            
        # Sort by engagement score
        videos.sort(key=lambda x: x.engagement_score, reverse=True)
        return videos[:3]  # Return top 3 videos
        
    except Exception as e:
        logger.error(f"Error searching YouTube videos: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error searching videos: {str(e)}")

async def get_video_details(video_ids: List[str]):
    """Get detailed video statistics"""
    try:
        youtube_api_key = os.environ.get('YOUTUBE_API_KEY')
        url = "https://www.googleapis.com/youtube/v3/videos"
        params = {
            'part': 'statistics,contentDetails',
            'id': ','.join(video_ids),
            'key': youtube_api_key
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                data = await response.json()
                
        details = []
        for item in data.get('items', []):
            stats = item.get('statistics', {})
            content = item.get('contentDetails', {})
            details.append({
                'viewCount': stats.get('viewCount', '0'),
                'likeCount': stats.get('likeCount', '0'),
                'duration': content.get('duration', '')
            })
            
        return details
        
    except Exception as e:
        logger.error(f"Error getting video details: {str(e)}")
        return [{}] * len(video_ids)

async def get_video_transcript(video_id: str):
    """Get transcript for a YouTube video"""
    try:
        # For now, return a mock transcript - in production you'd use youtube-transcript-api
        # or similar service to get actual transcripts
        return f"This is a mock transcript for video {video_id}. In a real implementation, you would use the YouTube Transcript API or similar service to fetch the actual video transcript."
        
    except Exception as e:
        logger.error(f"Error getting transcript: {str(e)}")
        return None

async def generate_lessons_from_transcript(transcript: str, topic: str, mode: str):
    """Generate structured lessons from video transcript using Gemini"""
    try:
        google_api_key = os.environ.get('GOOGLE_API_KEY')
        if not google_api_key:
            raise HTTPException(status_code=500, detail="Google API key not configured")
        
        # Determine lesson count based on mode
        lesson_count = {"Quick": 3, "Detailed": 6, "Mixed": 4}.get(mode, 4)
        
        prompt = f"""
        Create {lesson_count} structured lessons from this transcript about {topic}.
        
        Mode: {mode}
        - Quick: Short, focused lessons (2-3 paragraphs each)
        - Detailed: In-depth lessons (4-5 paragraphs each)  
        - Mixed: Balanced approach (3-4 paragraphs each)
        
        Transcript: {transcript[:3000]}...
        
        Format each lesson as:
        LESSON_TITLE: [Clear, descriptive title]
        LESSON_CONTENT: [Educational content with examples, explanations, and key points]
        
        Make the lessons progressive, building upon each other.
        """
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={google_api_key}"
        
        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }]
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status != 200:
                    raise HTTPException(status_code=500, detail="Gemini API error")
                
                data = await response.json()
                
        content = data['candidates'][0]['content']['parts'][0]['text']
        
        # Parse lessons from response
        lessons = []
        lesson_parts = content.split('LESSON_TITLE:')
        
        for i, part in enumerate(lesson_parts[1:], 1):
            lines = part.strip().split('\n')
            title = lines[0].strip()
            content_lines = []
            
            for line in lines[1:]:
                if line.startswith('LESSON_CONTENT:'):
                    content_lines = lines[lines.index(line)+1:]
                    break
                    
            lesson_content = '\n'.join(content_lines).strip()
            
            lesson = Lesson(
                title=title,
                content=lesson_content,
                order=i
            )
            lessons.append(lesson)
            
        return lessons
        
    except Exception as e:
        logger.error(f"Error generating lessons: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating lessons: {str(e)}")

async def generate_quiz(lesson: Lesson):
    """Generate quiz questions for a lesson using Gemini"""
    try:
        google_api_key = os.environ.get('GOOGLE_API_KEY')
        if not google_api_key:
            raise HTTPException(status_code=500, detail="Google API key not configured")
        
        prompt = f"""
        Create 5-7 quiz questions based on this lesson about {lesson.title}.
        
        Lesson Content: {lesson.content}
        
        Create a mix of question types:
        - Multiple choice (4 options)
        - True/False
        - Fill in the blank
        
        Format as JSON:
        {{
            "questions": [
                {{
                    "type": "mcq",
                    "question": "Question text?",
                    "options": ["A", "B", "C", "D"],
                    "correct_answer": 0,
                    "explanation": "Why this is correct"
                }},
                {{
                    "type": "true_false",
                    "question": "Statement to evaluate",
                    "correct_answer": true,
                    "explanation": "Explanation"
                }},
                {{
                    "type": "fill_blank",
                    "question": "Complete this: Python is a _____ language",
                    "correct_answer": "programming",
                    "explanation": "Explanation"
                }}
            ]
        }}
        """
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={google_api_key}"
        
        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }]
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status != 200:
                    raise HTTPException(status_code=500, detail="Gemini API error")
                
                data = await response.json()
                
        content = data['candidates'][0]['content']['parts'][0]['text']
        
        # Extract JSON from response
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            quiz_data = json.loads(json_match.group())
            quiz = Quiz(
                lesson_id=lesson.id,
                questions=quiz_data['questions']
            )
            return quiz
        else:
            raise ValueError("Could not parse quiz JSON")
            
    except Exception as e:
        logger.error(f"Error generating quiz: {str(e)}")
        # Return a default quiz if generation fails
        default_quiz = Quiz(
            lesson_id=lesson.id,
            questions=[{
                "type": "mcq",
                "question": f"What is the main topic of the lesson '{lesson.title}'?",
                "options": ["Option A", "Option B", "Option C", "Option D"],
                "correct_answer": 0,
                "explanation": "This is a default question."
            }]
        )
        return default_quiz


# Authentication Routes
@api_router.post("/auth/signup", response_model=SessionResponse)
async def signup(user_data: UserCreate, response: Response):
    """Signup with email and password"""
    try:
        # Check if user already exists
        existing_user = await db.users.find_one({"email": user_data.email})
        if existing_user:
            raise HTTPException(status_code=400, detail="User already exists")
        
        # Create new user
        user_id = str(uuid.uuid4())
        hashed_password = get_password_hash(user_data.password) if user_data.password else None
        
        user = {
            "id": user_id,
            "email": user_data.email,
            "name": user_data.name,
            "picture": user_data.picture,
            "password_hash": hashed_password,
            "created_at": datetime.now(timezone.utc),
            "courses_enrolled": [],
            "badges": [],
            "streak_count": 0,
            "last_login": datetime.now(timezone.utc)
        }
        
        await db.users.insert_one(user)
        
        # Create session
        session_token = create_access_token(user_id)
        session = UserSession(
            user_id=user_id,
            session_token=session_token,
            expires_at=datetime.now(timezone.utc) + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
        )
        
        await db.user_sessions.insert_one(session.dict())
        
        # Set cookie
        response.set_cookie(
            key="session_token",
            value=session_token,
            httponly=True,
            secure=True,
            samesite="none",
            path="/",
            max_age=7 * 24 * 60 * 60  # 7 days
        )
        
        return SessionResponse(
            id=user_id,
            email=user_data.email,
            name=user_data.name,
            picture=user_data.picture,
            session_token=session_token
        )
        
    except Exception as e:
        logger.error(f"Error during signup: {str(e)}")
        raise HTTPException(status_code=500, detail="Signup failed")

@api_router.post("/auth/login", response_model=SessionResponse)
async def login(login_data: EmailPasswordLogin, response: Response):
    """Login with email and password"""
    try:
        # Find user
        user = await db.users.find_one({"email": login_data.email})
        if not user or not verify_password(login_data.password, user.get("password_hash", "")):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Update last login
        await db.users.update_one(
            {"id": user["id"]},
            {"$set": {"last_login": datetime.now(timezone.utc)}}
        )
        
        # Create session
        session_token = create_access_token(user["id"])
        session = UserSession(
            user_id=user["id"],
            session_token=session_token,
            expires_at=datetime.now(timezone.utc) + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
        )
        
        await db.user_sessions.insert_one(session.dict())
        
        # Set cookie
        response.set_cookie(
            key="session_token",
            value=session_token,
            httponly=True,
            secure=True,
            samesite="none",
            path="/",
            max_age=7 * 24 * 60 * 60  # 7 days
        )
        
        return SessionResponse(
            id=user["id"],
            email=user["email"],
            name=user["name"],
            picture=user.get("picture"),
            session_token=session_token
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during login: {str(e)}")
        raise HTTPException(status_code=500, detail="Login failed")

@api_router.get("/auth/session-data", response_model=SessionResponse)
async def get_session_data(request: Request):
    """Process session_id from Emergent Auth and return session data"""
    try:
        session_id = request.headers.get('X-Session-ID')
        if not session_id:
            raise HTTPException(status_code=400, detail="Session ID required")
        
        # Call Emergent Auth API
        async with aiohttp.ClientSession() as session:
            headers = {'X-Session-ID': session_id}
            async with session.get(
                'https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data',
                headers=headers
            ) as response:
                if response.status != 200:
                    raise HTTPException(status_code=400, detail="Invalid session")
                
                auth_data = await response.json()
        
        # Check if user exists, create if not
        user = await db.users.find_one({"email": auth_data["email"]})
        
        if not user:
            # Create new user from Google OAuth data
            user_id = str(uuid.uuid4())
            user = {
                "id": user_id,
                "email": auth_data["email"],
                "name": auth_data["name"],
                "picture": auth_data.get("picture"),
                "password_hash": None,  # OAuth users don't have passwords
                "created_at": datetime.now(timezone.utc),
                "courses_enrolled": [],
                "badges": [],
                "streak_count": 0,
                "last_login": datetime.now(timezone.utc)
            }
            await db.users.insert_one(user)
        else:
            # Update last login
            await db.users.update_one(
                {"id": user["id"]},
                {"$set": {"last_login": datetime.now(timezone.utc)}}
            )
        
        # Store session from Emergent Auth
        session = UserSession(
            user_id=user["id"],
            session_token=auth_data["session_token"],
            expires_at=datetime.now(timezone.utc) + timedelta(days=7)
        )
        
        await db.user_sessions.insert_one(session.dict())
        
        return SessionResponse(
            id=user["id"],
            email=user["email"],
            name=user["name"],
            picture=user.get("picture"),
            session_token=auth_data["session_token"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing session: {str(e)}")
        raise HTTPException(status_code=500, detail="Session processing failed")

@api_router.post("/auth/logout")
async def logout(response: Response, current_user: UserResponse = Depends(require_auth)):
    """Logout user and clear session"""
    try:
        # Delete all sessions for this user
        await db.user_sessions.delete_many({"user_id": current_user.id})
        
        # Clear cookie
        response.delete_cookie(
            key="session_token",
            path="/",
            secure=True,
            samesite="none"
        )
        
        return {"message": "Logged out successfully"}
        
    except Exception as e:
        logger.error(f"Error during logout: {str(e)}")
        raise HTTPException(status_code=500, detail="Logout failed")

@api_router.get("/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: UserResponse = Depends(require_auth)):
    """Get current user information"""
    return current_user


# Course Routes
@api_router.post("/create-course", response_model=CourseResponse)
async def create_course(request: TopicRequest, current_user: UserResponse = Depends(require_auth)):
    """Create a complete course with videos, lessons, and quizzes"""
    try:
        # Step 1: Search for YouTube videos
        videos = await search_youtube_videos(request.topic, request.language)
        
        if not videos:
            raise HTTPException(status_code=404, detail="No suitable videos found")
        
        # Step 2: Get transcripts for top videos
        transcripts = []
        for video in videos[:2]:  # Use top 2 videos
            transcript = await get_video_transcript(video.video_id)
            if transcript:
                transcripts.append(transcript)
        
        # Combine transcripts
        combined_transcript = " ".join(transcripts) if transcripts else f"Default content for {request.topic}"
        
        # Step 3: Generate lessons
        lessons = await generate_lessons_from_transcript(combined_transcript, request.topic, request.mode)
        
        # Step 4: Create and store course
        course = Course(
            user_id=current_user.id,
            topic=request.topic,
            language=request.language,
            mode=request.mode,
            lessons=lessons,
            videos=videos
        )
        
        course_dict = course.dict()
        course_dict['created_at'] = course_dict['created_at'].isoformat()
        await db.courses.insert_one(course_dict)
        
        # Update user's enrolled courses
        await db.users.update_one(
            {"id": current_user.id},
            {"$addToSet": {"courses_enrolled": course.id}}
        )
        
        return CourseResponse(
            id=course.id,
            lessons=lessons,
            videos=videos,
            created_at=course.created_at
        )
        
    except Exception as e:
        logger.error(f"Error creating course: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating course: {str(e)}")

@api_router.get("/quiz/{lesson_id}")
async def get_quiz(lesson_id: str, current_user: UserResponse = Depends(require_auth)):
    """Generate and return quiz for a specific lesson"""
    try:
        # Get lesson from database
        course = await db.courses.find_one({"lessons.id": lesson_id, "user_id": current_user.id})
        if not course:
            raise HTTPException(status_code=404, detail="Lesson not found")
        
        # Find the specific lesson
        lesson_data = None
        for lesson in course['lessons']:
            if lesson['id'] == lesson_id:
                lesson_data = lesson
                break
                
        if not lesson_data:
            raise HTTPException(status_code=404, detail="Lesson not found")
        
        lesson = Lesson(**lesson_data)
        quiz = await generate_quiz(lesson)
        
        return quiz
        
    except Exception as e:
        logger.error(f"Error getting quiz: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting quiz: {str(e)}")

@api_router.post("/progress")
async def save_progress(progress: UserProgress, current_user: UserResponse = Depends(require_auth)):
    """Save user progress"""
    try:
        progress.user_id = current_user.id
        progress.updated_at = datetime.now(timezone.utc)
        
        # Check if progress already exists for this course
        existing_progress = await db.user_progress.find_one({
            "user_id": current_user.id,
            "course_id": progress.course_id
        })
        
        if existing_progress:
            # Update existing progress
            await db.user_progress.update_one(
                {"user_id": current_user.id, "course_id": progress.course_id},
                {"$set": progress.dict()}
            )
        else:
            # Create new progress
            await db.user_progress.insert_one(progress.dict())
        
        return {"message": "Progress saved successfully"}
        
    except Exception as e:
        logger.error(f"Error saving progress: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error saving progress: {str(e)}")

@api_router.get("/progress")
async def get_user_progress(current_user: UserResponse = Depends(require_auth)):
    """Get all user progress"""
    try:
        progress_list = await db.user_progress.find({"user_id": current_user.id}).to_list(length=None)
        return [UserProgress(**progress) for progress in progress_list]
        
    except Exception as e:
        logger.error(f"Error getting progress: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting progress: {str(e)}")

@api_router.get("/my-courses")
async def get_user_courses(current_user: UserResponse = Depends(require_auth)):
    """Get all courses created by the user"""
    try:
        courses = await db.courses.find({"user_id": current_user.id}).to_list(length=None)
        course_responses = []
        
        for course in courses:
            course_responses.append(CourseResponse(
                id=course["id"],
                lessons=[Lesson(**lesson) for lesson in course["lessons"]],
                videos=[VideoInfo(**video) for video in course["videos"]],
                created_at=datetime.fromisoformat(course["created_at"]) if isinstance(course["created_at"], str) else course["created_at"]
            ))
        
        return course_responses
        
    except Exception as e:
        logger.error(f"Error getting user courses: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting user courses: {str(e)}")

@api_router.get("/dashboard")
async def get_dashboard_data(current_user: UserResponse = Depends(require_auth)):
    """Get dashboard data for the user"""
    try:
        # Get user courses
        courses = await db.courses.find({"user_id": current_user.id}).to_list(length=None)
        
        # Get user progress
        progress_list = await db.user_progress.find({"user_id": current_user.id}).to_list(length=None)
        
        # Calculate stats
        total_courses = len(courses)
        total_lessons_completed = sum(len(p.get("lessons_completed", [])) for p in progress_list)
        average_quiz_score = 0
        
        if progress_list:
            all_scores = []
            for p in progress_list:
                scores = p.get("quiz_scores", {})
                all_scores.extend(scores.values())
            average_quiz_score = sum(all_scores) / len(all_scores) if all_scores else 0
        
        return {
            "user": current_user,
            "stats": {
                "total_courses": total_courses,
                "lessons_completed": total_lessons_completed,
                "average_quiz_score": round(average_quiz_score, 1),
                "streak_count": current_user.streak_count
            },
            "recent_courses": [
                CourseResponse(
                    id=course["id"],
                    lessons=[Lesson(**lesson) for lesson in course["lessons"]],
                    videos=[VideoInfo(**video) for video in course["videos"]],
                    created_at=datetime.fromisoformat(course["created_at"]) if isinstance(course["created_at"], str) else course["created_at"]
                ) for course in courses[-5:]  # Last 5 courses
            ],
            "progress": [UserProgress(**p) for p in progress_list]
        }
        
    except Exception as e:
        logger.error(f"Error getting dashboard data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting dashboard data: {str(e)}")


# Basic health check
@api_router.get("/")
async def root():
    return {"message": "AI Learning Platform API with Authentication"}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()