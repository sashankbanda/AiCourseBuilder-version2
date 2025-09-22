import requests
import sys
import json
from datetime import datetime
import uuid

class AILearningPlatformTester:
    def __init__(self, base_url="https://smarttutor-5.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.course_data = None
        self.lesson_id = None
        self.session_token = None
        self.user_data = None
        self.session = requests.Session()  # Use session for cookie management

    def run_test(self, name, method, endpoint, expected_status, data=None, timeout=30, auth_required=False):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}" if endpoint else self.base_url
        headers = {'Content-Type': 'application/json'}
        
        # Add session token if available and auth required
        if auth_required and self.session_token:
            headers['Authorization'] = f'Bearer {self.session_token}'

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        if auth_required:
            print(f"   Auth: {'✅ Token provided' if self.session_token else '❌ No token'}")
        
        try:
            if method == 'GET':
                response = self.session.get(url, headers=headers, timeout=timeout)
            elif method == 'POST':
                response = self.session.post(url, json=data, headers=headers, timeout=timeout)
            elif method == 'PUT':
                response = self.session.put(url, json=data, headers=headers, timeout=timeout)

            print(f"   Status Code: {response.status_code}")
            
            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"   Response keys: {list(response_data.keys()) if isinstance(response_data, dict) else 'Non-dict response'}")
                    return True, response_data
                except:
                    return True, response.text
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Error: {response.text}")
                return False, {}

        except requests.exceptions.Timeout:
            print(f"❌ Failed - Request timed out after {timeout} seconds")
            return False, {}
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_health_check(self):
        """Test basic API health check"""
        success, response = self.run_test(
            "API Health Check",
            "GET",
            "",
            200
        )
        return success

    def test_signup(self):
        """Test user signup with email and password"""
        timestamp = datetime.now().strftime('%H%M%S')
        test_data = {
            "email": f"testuser{timestamp}@example.com",
            "password": "testpass123",
            "name": "Test User"
        }
        
        success, response = self.run_test(
            "User Signup",
            "POST",
            "auth/signup",
            200,
            data=test_data
        )
        
        if success and isinstance(response, dict):
            # Validate response structure
            required_fields = ['id', 'email', 'name', 'session_token']
            missing_fields = [field for field in required_fields if field not in response]
            
            if missing_fields:
                print(f"   ❌ Signup response missing fields: {missing_fields}")
                return False
            
            # Store user data and session token for subsequent tests
            self.user_data = response
            self.session_token = response.get('session_token')
            print(f"   ✅ User created: {response['email']}")
            print(f"   🔑 Session token received: {self.session_token[:20]}...")
            return True
        
        return success

    def test_login(self):
        """Test user login with email and password"""
        if not self.user_data:
            print("❌ Cannot test login - no user data from signup")
            return False
        
        login_data = {
            "email": self.user_data['email'],
            "password": "testpass123"
        }
        
        success, response = self.run_test(
            "User Login",
            "POST",
            "auth/login",
            200,
            data=login_data
        )
        
        if success and isinstance(response, dict):
            # Validate response structure
            required_fields = ['id', 'email', 'name', 'session_token']
            missing_fields = [field for field in required_fields if field not in response]
            
            if missing_fields:
                print(f"   ❌ Login response missing fields: {missing_fields}")
                return False
            
            # Update session token
            self.session_token = response.get('session_token')
            print(f"   ✅ Login successful for: {response['email']}")
            print(f"   🔑 New session token: {self.session_token[:20]}...")
            return True
        
        return success

    def test_get_current_user(self):
        """Test getting current user info"""
        success, response = self.run_test(
            "Get Current User",
            "GET",
            "auth/me",
            200,
            auth_required=True
        )
        
        if success and isinstance(response, dict):
            # Validate user response structure
            required_fields = ['id', 'email', 'name', 'created_at']
            missing_fields = [field for field in required_fields if field not in response]
            
            if missing_fields:
                print(f"   ❌ User response missing fields: {missing_fields}")
                return False
            
            print(f"   ✅ Current user: {response['name']} ({response['email']})")
            print(f"   📅 Created: {response['created_at']}")
            return True
        
        return success

    def test_dashboard(self):
        """Test dashboard data retrieval"""
        success, response = self.run_test(
            "Get Dashboard Data",
            "GET",
            "dashboard",
            200,
            auth_required=True
        )
        
        if success and isinstance(response, dict):
            # Validate dashboard structure
            expected_sections = ['user', 'stats', 'recent_courses', 'progress']
            found_sections = [section for section in expected_sections if section in response]
            print(f"   ✅ Dashboard sections: {found_sections}")
            
            if 'stats' in response:
                stats = response['stats']
                print(f"   📊 Stats: {stats}")
            
            if 'user' in response:
                user = response['user']
                print(f"   👤 User: {user.get('name', 'Unknown')}")
            
            return True
        
        return success

    def test_my_courses(self):
        """Test getting user's courses"""
        success, response = self.run_test(
            "Get My Courses",
            "GET",
            "my-courses",
            200,
            auth_required=True
        )
        
        if success:
            if isinstance(response, list):
                print(f"   ✅ Retrieved {len(response)} courses")
                for i, course in enumerate(response):
                    if isinstance(course, dict) and 'lessons' in course:
                        print(f"   📚 Course {i+1}: {len(course['lessons'])} lessons")
            else:
                print(f"   ⚠️  Expected list response, got: {type(response)}")
            return True
        
        return success

    def test_create_course(self):
        """Test course creation with JavaScript Fundamentals"""
        test_data = {
            "topic": "JavaScript Fundamentals",
            "language": "english",
            "mode": "Quick"
        }
        
        success, response = self.run_test(
            "Create Course - JavaScript Fundamentals",
            "POST",
            "create-course",
            200,
            data=test_data,
            timeout=60,  # Longer timeout for AI processing
            auth_required=True
        )
        
        if success and isinstance(response, dict):
            # Validate response structure
            if 'lessons' in response and 'videos' in response:
                self.course_data = response
                lessons = response.get('lessons', [])
                videos = response.get('videos', [])
                
                print(f"   ✅ Course created with {len(lessons)} lessons and {len(videos)} videos")
                
                # Store first lesson ID for quiz testing
                if lessons:
                    self.lesson_id = lessons[0].get('id')
                    print(f"   📝 First lesson ID: {self.lesson_id}")
                
                # Validate lesson structure
                for i, lesson in enumerate(lessons):
                    required_fields = ['id', 'title', 'content', 'order']
                    missing_fields = [field for field in required_fields if field not in lesson]
                    if missing_fields:
                        print(f"   ⚠️  Lesson {i+1} missing fields: {missing_fields}")
                    else:
                        print(f"   ✅ Lesson {i+1}: '{lesson['title']}' (Order: {lesson['order']})")
                
                # Validate video structure
                for i, video in enumerate(videos):
                    required_fields = ['video_id', 'title', 'channel_name']
                    missing_fields = [field for field in required_fields if field not in video]
                    if missing_fields:
                        print(f"   ⚠️  Video {i+1} missing fields: {missing_fields}")
                    else:
                        print(f"   ✅ Video {i+1}: '{video['title']}' by {video['channel_name']}")
                
                return True
            else:
                print(f"   ❌ Invalid response structure. Expected 'lessons' and 'videos' keys")
                return False
        
        return success

    def test_get_quiz(self):
        """Test quiz generation for a lesson"""
        if not self.lesson_id:
            print("❌ Cannot test quiz - no lesson ID available")
            return False
        
        success, response = self.run_test(
            f"Get Quiz for Lesson",
            "GET",
            f"quiz/{self.lesson_id}",
            200,
            timeout=45,  # Longer timeout for AI processing
            auth_required=True
        )
        
        if success and isinstance(response, dict):
            # Validate quiz structure
            required_fields = ['id', 'lesson_id', 'questions']
            missing_fields = [field for field in required_fields if field not in response]
            
            if missing_fields:
                print(f"   ❌ Quiz missing fields: {missing_fields}")
                return False
            
            questions = response.get('questions', [])
            print(f"   ✅ Quiz generated with {len(questions)} questions")
            
            # Validate question structure
            for i, question in enumerate(questions):
                q_type = question.get('type', 'unknown')
                q_text = question.get('question', 'No question text')
                print(f"   📝 Question {i+1} ({q_type}): {q_text[:50]}...")
                
                # Check required fields based on question type
                if q_type == 'mcq':
                    if 'options' not in question or 'correct_answer' not in question:
                        print(f"   ⚠️  MCQ question missing options or correct_answer")
                elif q_type == 'true_false':
                    if 'correct_answer' not in question:
                        print(f"   ⚠️  True/False question missing correct_answer")
                elif q_type == 'fill_blank':
                    if 'correct_answer' not in question:
                        print(f"   ⚠️  Fill blank question missing correct_answer")
            
            return True
        
        return success

    def test_save_progress(self):
        """Test saving user progress"""
        if not self.lesson_id or not self.course_data:
            print("❌ Cannot test progress - no lesson ID or course data available")
            return False
        
        test_progress = {
            "course_id": self.course_data.get('id'),
            "topic": "JavaScript Fundamentals",
            "language": "english",
            "mode": "Quick",
            "lessons_completed": [self.lesson_id],
            "quiz_scores": {self.lesson_id: 85},
            "notes": {self.lesson_id: "Great lesson on JavaScript basics!"}
        }
        
        success, response = self.run_test(
            "Save User Progress",
            "POST",
            "progress",
            200,
            data=test_progress,
            auth_required=True
        )
        
        if success:
            print(f"   ✅ Progress saved for course: {test_progress['course_id']}")
        
        return success

    def test_get_progress(self):
        """Test retrieving user progress"""
        success, response = self.run_test(
            "Get User Progress",
            "GET",
            "progress",
            200,
            auth_required=True
        )
        
        if success:
            if isinstance(response, list):
                print(f"   ✅ Retrieved {len(response)} progress records")
                for i, progress in enumerate(response):
                    if isinstance(progress, dict):
                        topic = progress.get('topic', 'Unknown')
                        completed = len(progress.get('lessons_completed', []))
                        print(f"   📚 Progress {i+1}: {topic} - {completed} lessons completed")
            else:
                print(f"   ⚠️  Expected list response, got: {type(response)}")
        
        return success

    def test_logout(self):
        """Test user logout"""
        success, response = self.run_test(
            "User Logout",
            "POST",
            "auth/logout",
            200,
            auth_required=True
        )
        
        if success:
            print(f"   ✅ Logout successful")
            # Clear session token
            self.session_token = None
        
        return success

    def test_unauthorized_access(self):
        """Test that protected routes require authentication"""
        # Clear session token temporarily
        original_token = self.session_token
        self.session_token = None
        
        print("\n🔍 Testing Unauthorized Access...")
        
        # Test dashboard without auth
        success1, _ = self.run_test(
            "Dashboard without Auth",
            "GET",
            "dashboard",
            401,
            auth_required=False
        )
        
        # Test create course without auth
        success2, _ = self.run_test(
            "Create Course without Auth",
            "POST",
            "create-course",
            401,
            data={"topic": "Test", "language": "english", "mode": "Quick"},
            auth_required=False
        )
        
        # Test my courses without auth
        success3, _ = self.run_test(
            "My Courses without Auth",
            "GET",
            "my-courses",
            401,
            auth_required=False
        )
        
        # Restore session token
        self.session_token = original_token
        
        return success1 and success2 and success3

    def test_invalid_endpoints(self):
        """Test error handling for invalid endpoints"""
        print("\n🔍 Testing Error Handling...")
        
        # Test invalid credentials
        success1, _ = self.run_test(
            "Invalid Login Credentials",
            "POST",
            "auth/login",
            401,
            data={"email": "nonexistent@example.com", "password": "wrongpass"}
        )
        
        # Test duplicate signup
        if self.user_data:
            success2, _ = self.run_test(
                "Duplicate User Signup",
                "POST",
                "auth/signup",
                400,
                data={
                    "email": self.user_data['email'],
                    "password": "testpass123",
                    "name": "Duplicate User"
                }
            )
        else:
            success2 = True  # Skip if no user data
        
        # Test invalid lesson ID for quiz (with auth)
        success3, _ = self.run_test(
            "Invalid Lesson ID for Quiz",
            "GET",
            "quiz/invalid-lesson-id",
            404,
            auth_required=True
        )
        
        # Test missing required fields in course creation
        success4, _ = self.run_test(
            "Missing Topic in Course Creation",
            "POST",
            "create-course",
            422,  # Validation error
            data={"language": "english", "mode": "Quick"},
            auth_required=True
        )
        
        return success1 and success2 and success3 and success4

def main():
    print("🚀 Starting AI Learning Platform API Tests with Authentication")
    print("=" * 70)
    
    tester = AILearningPlatformTester()
    
    # Run all tests in order (authentication first)
    tests = [
        ("Basic API", tester.test_health_check),
        ("Authentication - Signup", tester.test_signup),
        ("Authentication - Login", tester.test_login),
        ("Authentication - Get Current User", tester.test_get_current_user),
        ("Dashboard Data", tester.test_dashboard),
        ("My Courses", tester.test_my_courses),
        ("Course Creation", tester.test_create_course),
        ("Quiz Generation", tester.test_get_quiz),
        ("Progress Saving", tester.test_save_progress),
        ("Progress Retrieval", tester.test_get_progress),
        ("User Logout", tester.test_logout),
        ("Unauthorized Access", tester.test_unauthorized_access),
        ("Error Handling", tester.test_invalid_endpoints)
    ]
    
    for test_name, test_func in tests:
        try:
            print(f"\n{'='*20} {test_name} {'='*20}")
            test_func()
        except Exception as e:
            print(f"❌ Test '{test_name}' failed with exception: {str(e)}")
    
    # Print final results
    print("\n" + "=" * 70)
    print(f"📊 FINAL RESULTS")
    print(f"Tests Run: {tester.tests_run}")
    print(f"Tests Passed: {tester.tests_passed}")
    print(f"Tests Failed: {tester.tests_run - tester.tests_passed}")
    print(f"Success Rate: {(tester.tests_passed / tester.tests_run * 100):.1f}%" if tester.tests_run > 0 else "0%")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed. Check the logs above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())