import React, { useState, useEffect, createContext, useContext } from 'react';
import './App.css';
import { BrowserRouter, Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom';
import axios from 'axios';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './components/ui/card';
import { Button } from './components/ui/button';
import { Input } from './components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './components/ui/select';
import { Badge } from './components/ui/badge';
import { Progress } from './components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs';
import { Textarea } from './components/ui/textarea';
import { Avatar, AvatarFallback, AvatarImage } from './components/ui/avatar';
import { 
  BookOpen, Play, Trophy, Moon, Sun, Eye, CheckCircle, Circle, Star, Target, Zap, Brain,
  User, Settings, LogOut, Home, TrendingUp, Award, Calendar, Clock, BarChart3,
  PlayCircle, FileText, MessageSquare
} from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Auth Context
const AuthContext = createContext();

// Theme Context
const ThemeContext = createContext();

// Theme Provider
const ThemeProvider = ({ children }) => {
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('theme') || 'light';
  });

  useEffect(() => {
    localStorage.setItem('theme', theme);
    document.documentElement.className = theme;
  }, [theme]);

  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};

// Auth Provider
const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Check for existing session on app load
  useEffect(() => {
    checkExistingSession();
  }, []);

  // Handle OAuth redirect
  useEffect(() => {
    const handleOAuthRedirect = async () => {
      const hash = window.location.hash;
      if (hash.includes('session_id=')) {
        setLoading(true);
        const sessionId = hash.split('session_id=')[1].split('&')[0];
        
        try {
          const response = await axios.get(`${API}/auth/session-data`, {
            headers: { 'X-Session-ID': sessionId }
          });
          
          setUser(response.data);
          // Clear the hash from URL
          window.history.replaceState({}, document.title, window.location.pathname);
          toast.success('Login successful!');
        } catch (error) {
          console.error('OAuth login failed:', error);
          toast.error('Login failed. Please try again.');
        } finally {
          setLoading(false);
        }
      }
    };

    handleOAuthRedirect();
  }, []);

  const checkExistingSession = async () => {
    try {
      const response = await axios.get(`${API}/auth/me`, {
        withCredentials: true
      });
      setUser(response.data);
    } catch (error) {
      // No existing session
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  const login = (userData) => {
    setUser(userData);
  };

  const logout = async () => {
    try {
      await axios.post(`${API}/auth/logout`, {}, { withCredentials: true });
      setUser(null);
      toast.success('Logged out successfully');
    } catch (error) {
      console.error('Logout error:', error);
      // Still clear local state even if request fails
      setUser(null);
    }
  };

  const value = {
    user,
    login,
    logout,
    loading,
    isAuthenticated: !!user
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

// Custom hooks
const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider');
  }
  return context;
};

// Theme Toggle Component
const ThemeToggle = () => {
  const { theme, setTheme } = useTheme();

  const cycleTheme = () => {
    const themes = ['light', 'dark', 'sepia'];
    const currentIndex = themes.indexOf(theme);
    const nextIndex = (currentIndex + 1) % themes.length;
    setTheme(themes[nextIndex]);
  };

  const getThemeIcon = () => {
    switch (theme) {
      case 'light': return <Sun className="h-4 w-4" />;
      case 'dark': return <Moon className="h-4 w-4" />;
      case 'sepia': return <Eye className="h-4 w-4" />;
      default: return <Sun className="h-4 w-4" />;
    }
  };

  const getButtonText = () => {
    switch (theme) {
      case 'light': return 'Light';
      case 'dark': return 'Dark';
      case 'sepia': return 'Sepia';
      default: return 'Light';
    }
  };

  return (
    <Button
      variant="outline"
      size="sm"
      onClick={cycleTheme}
      className="flex items-center gap-2 theme-button"
    >
      {getThemeIcon()}
      {getButtonText()}
    </Button>
  );
};

// Login/Signup Components
const AuthPage = () => {
  const [isLogin, setIsLogin] = useState(true);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    name: ''
  });
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();

  const handleGoogleLogin = () => {
    const redirectUrl = encodeURIComponent(`${window.location.origin}/dashboard`);
    window.location.href = `https://auth.emergentagent.com/?redirect=${redirectUrl}`;
  };

  const handleEmailAuth = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const endpoint = isLogin ? '/auth/login' : '/auth/signup';
      const response = await axios.post(`${API}${endpoint}`, formData, {
        withCredentials: true
      });
      
      login(response.data);
      toast.success(isLogin ? 'Login successful!' : 'Account created successfully!');
    } catch (error) {
      console.error('Auth error:', error);
      toast.error(error.response?.data?.detail || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="absolute top-4 right-4">
        <ThemeToggle />
      </div>
      
      <Card className="max-w-md w-full auth-card">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl font-bold flex items-center justify-center gap-2">
            <Brain className="h-6 w-6 text-accent" />
            AI Learning Platform
          </CardTitle>
          <CardDescription>
            {isLogin ? 'Welcome back!' : 'Create your account'}
          </CardDescription>
        </CardHeader>
        
        <CardContent className="space-y-4">
          {/* Google OAuth Button */}
          <Button
            onClick={handleGoogleLogin}
            className="w-full h-12 google-auth-button"
            variant="outline"
          >
            <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24">
              <path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
              <path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            Continue with Google
          </Button>

          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-background px-2 text-muted-foreground">Or</span>
            </div>
          </div>

          {/* Email/Password Form */}
          <form onSubmit={handleEmailAuth} className="space-y-4">
            {!isLogin && (
              <div>
                <Input
                  placeholder="Full Name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  required={!isLogin}
                />
              </div>
            )}
            
            <div>
              <Input
                type="email"
                placeholder="Email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                required
              />
            </div>
            
            <div>
              <Input
                type="password"
                placeholder="Password"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                required
              />
            </div>

            <Button type="submit" className="w-full primary-button" disabled={loading}>
              {loading ? (
                <div className="flex items-center gap-2">
                  <div className="loader"></div>
                  {isLogin ? 'Signing in...' : 'Creating account...'}
                </div>
              ) : (
                isLogin ? 'Sign In' : 'Create Account'
              )}
            </Button>
          </form>

          <div className="text-center">
            <Button
              variant="link"
              onClick={() => setIsLogin(!isLogin)}
              className="text-sm"
            >
              {isLogin ? "Don't have an account? Sign up" : "Already have an account? Sign in"}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

// Navigation Component
const Navigation = () => {
  const { user, logout } = useAuth();
  const location = useLocation();

  const navItems = [
    { path: '/dashboard', icon: Home, label: 'Dashboard' },
    { path: '/create-course', icon: Brain, label: 'Create Course' },
    { path: '/my-courses', icon: BookOpen, label: 'My Courses' },
    { path: '/profile', icon: User, label: 'Profile' }
  ];

  return (
    <nav className="navigation-bar">
      <div className="nav-brand">
        <Brain className="h-6 w-6 text-accent" />
        <span className="font-bold">AI Learning</span>
      </div>

      <div className="nav-items">
        {navItems.map((item) => (
          <Button
            key={item.path}
            variant={location.pathname === item.path ? "default" : "ghost"}
            size="sm"
            asChild
          >
            <a href={item.path} className="flex items-center gap-2">
              <item.icon className="h-4 w-4" />
              {item.label}
            </a>
          </Button>
        ))}
      </div>

      <div className="nav-user">
        <ThemeToggle />
        <div className="user-menu">
          <Avatar>
            <AvatarImage src={user?.picture} />
            <AvatarFallback>{user?.name?.charAt(0)}</AvatarFallback>
          </Avatar>
          <div className="user-info">
            <span className="user-name">{user?.name}</span>
            <Button
              variant="ghost"
              size="sm"
              onClick={logout}
              className="logout-button"
            >
              <LogOut className="h-4 w-4" />
              Logout
            </Button>
          </div>
        </div>
      </div>
    </nav>
  );
};

// Dashboard Component
const Dashboard = () => {
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      const response = await axios.get(`${API}/dashboard`, { withCredentials: true });
      setDashboardData(response.data);
    } catch (error) {
      console.error('Error fetching dashboard:', error);
      toast.error('Failed to load dashboard');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="dashboard-loading">
        <div className="loader"></div>
        <p>Loading your dashboard...</p>
      </div>
    );
  }

  return (
    <div className="dashboard">
      <Navigation />
      
      <div className="dashboard-content">
        <div className="dashboard-header">
          <h1>Welcome back, {dashboardData?.user?.name}!</h1>
          <p>Continue your learning journey</p>
        </div>

        {/* Stats Cards */}
        <div className="stats-grid">
          <Card className="stat-card">
            <CardContent className="p-6">
              <div className="stat-icon-wrapper">
                <BookOpen className="h-8 w-8 text-blue-500" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Total Courses</p>
                <p className="text-2xl font-bold">{dashboardData?.stats?.total_courses || 0}</p>
              </div>
            </CardContent>
          </Card>

          <Card className="stat-card">
            <CardContent className="p-6">
              <div className="stat-icon-wrapper">
                <CheckCircle className="h-8 w-8 text-green-500" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Lessons Completed</p>
                <p className="text-2xl font-bold">{dashboardData?.stats?.lessons_completed || 0}</p>
              </div>
            </CardContent>
          </Card>

          <Card className="stat-card">
            <CardContent className="p-6">
              <div className="stat-icon-wrapper">
                <Trophy className="h-8 w-8 text-yellow-500" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Avg Quiz Score</p>
                <p className="text-2xl font-bold">{dashboardData?.stats?.average_quiz_score || 0}%</p>
              </div>
            </CardContent>
          </Card>

          <Card className="stat-card">
            <CardContent className="p-6">
              <div className="stat-icon-wrapper">
                <TrendingUp className="h-8 w-8 text-purple-500" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Learning Streak</p>
                <p className="text-2xl font-bold">{dashboardData?.stats?.streak_count || 0} days</p>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Recent Courses */}
        <Card className="recent-courses">
          <CardHeader>
            <CardTitle>Recent Courses</CardTitle>
            <CardDescription>Continue where you left off</CardDescription>
          </CardHeader>
          <CardContent>
            {dashboardData?.recent_courses?.length > 0 ? (
              <div className="courses-list">
                {dashboardData.recent_courses.map((course) => (
                  <div key={course.id} className="course-item">
                    <div className="course-info">
                      <h3>{course.lessons[0]?.title || 'Untitled Course'}</h3>
                      <p>{course.lessons.length} lessons</p>
                    </div>
                    <Button size="sm" asChild>
                      <a href={`/course/${course.id}`}>Continue</a>
                    </Button>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-state">
                <BookOpen className="h-12 w-12 text-muted-foreground" />
                <p>No courses yet. Create your first course!</p>
                <Button asChild>
                  <a href="/create-course">Create Course</a>
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

// Course Creation Form (Updated)
const CourseCreator = ({ onCourseCreated }) => {
  const [formData, setFormData] = useState({
    topic: '',
    language: 'english',
    mode: 'Mixed'
  });
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.topic.trim()) {
      toast.error('Please enter a topic');
      return;
    }

    setLoading(true);
    
    try {
      const response = await axios.post(`${API}/create-course`, formData, {
        withCredentials: true
      });
      onCourseCreated(response.data, formData.topic);
      toast.success('Course created successfully!');
    } catch (error) {
      console.error('Error creating course:', error);
      toast.error('Failed to create course. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen">
      <Navigation />
      <div className="course-creator-container">
        <Card className="max-w-2xl mx-auto course-creator-card">
          <CardHeader className="text-center">
            <CardTitle className="text-3xl font-bold flex items-center justify-center gap-3">
              <Brain className="h-8 w-8 text-accent" />
              Create New Course
            </CardTitle>
            <CardDescription className="text-lg">
              Transform any topic into an interactive learning experience
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="space-y-2">
                <label className="text-sm font-medium">What would you like to learn?</label>
                <Input
                  placeholder="e.g., Dynamic Programming in Python, React Hooks, Machine Learning"
                  value={formData.topic}
                  onChange={(e) => setFormData({ ...formData, topic: e.target.value })}
                  className="text-base input-focus"
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Video Language</label>
                  <Select
                    value={formData.language}
                    onValueChange={(value) => setFormData({ ...formData, language: value })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="english">English</SelectItem>
                      <SelectItem value="hindi">Hindi</SelectItem>
                      <SelectItem value="telugu">Telugu</SelectItem>
                      <SelectItem value="tamil">Tamil</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium">Learning Mode</label>
                  <Select
                    value={formData.mode}
                    onValueChange={(value) => setFormData({ ...formData, mode: value })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Quick">
                        <div className="flex items-center gap-2">
                          <Zap className="h-4 w-4" />
                          Quick - Fast overview
                        </div>
                      </SelectItem>
                      <SelectItem value="Detailed">
                        <div className="flex items-center gap-2">
                          <BookOpen className="h-4 w-4" />
                          Detailed - In-depth study
                        </div>
                      </SelectItem>
                      <SelectItem value="Mixed">
                        <div className="flex items-center gap-2">
                          <Target className="h-4 w-4" />
                          Mixed - Balanced approach
                        </div>
                      </SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <Button
                type="submit"
                className="w-full h-12 text-base font-semibold primary-button"
                disabled={loading}
              >
                {loading ? (
                  <div className="flex items-center gap-2">
                    <div className="loader"></div>
                    Creating Your Course...
                  </div>
                ) : (
                  <div className="flex items-center gap-2">
                    <Play className="h-5 w-5" />
                    Create Course
                  </div>
                )}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

// Video Player Component (same as before)
const VideoPlayer = ({ video, isRecommended }) => {
  return (
    <div className="video-player-container">
      {isRecommended && (
        <Badge className="mb-2 bg-gradient-to-r from-yellow-400 to-orange-500 text-white">
          <Star className="h-3 w-3 mr-1" />
          Recommended
        </Badge>
      )}
      <div className="video-embed">
        <iframe
          width="100%"
          height="315"
          src={`https://www.youtube.com/embed/${video.video_id}`}
          title={video.title}
          frameBorder="0"
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowFullScreen
          className="rounded-lg"
        ></iframe>
      </div>
      <div className="mt-3">
        <h3 className="font-semibold text-sm line-clamp-2">{video.title}</h3>
        <p className="text-xs text-muted-foreground mt-1">{video.channel_name}</p>
        <div className="flex items-center gap-3 mt-2 text-xs text-muted-foreground">
          <span>{video.view_count.toLocaleString()} views</span>
          <span>•</span>
          <span>{video.duration}</span>
        </div>
      </div>
    </div>
  );
};

// Lesson Component (same as before)
const LessonView = ({ lesson, onComplete, isCompleted, onQuizRequest }) => {
  const [notes, setNotes] = useState('');

  const handleComplete = () => {
    onComplete(lesson.id, notes);
  };

  return (
    <Card className="lesson-card">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            {isCompleted ? (
              <CheckCircle className="h-5 w-5 text-green-500" />
            ) : (
              <Circle className="h-5 w-5 text-muted-foreground" />
            )}
            {lesson.title}
          </CardTitle>
          <Badge variant={isCompleted ? "default" : "secondary"}>
            Lesson {lesson.order}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="lesson-content">
          <p className="text-base leading-relaxed whitespace-pre-line">
            {lesson.content}
          </p>
        </div>

        <div className="space-y-3">
          <label className="text-sm font-medium">Your Notes</label>
          <Textarea
            placeholder="Write your thoughts, key takeaways, or questions about this lesson..."
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            className="min-h-[100px] resize-y"
          />
        </div>

        <div className="flex gap-3 pt-2">
          <Button
            onClick={handleComplete}
            disabled={isCompleted}
            className="flex-1 primary-button"
          >
            {isCompleted ? 'Completed' : 'Mark Complete'}
          </Button>
          <Button
            onClick={() => onQuizRequest(lesson.id)}
            variant="outline"
            className="flex-1"
          >
            <Trophy className="h-4 w-4 mr-2" />
            Take Quiz
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};

// Quiz Component (same as before)
const QuizView = ({ quiz, onQuizComplete }) => {
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [answers, setAnswers] = useState({});
  const [showResults, setShowResults] = useState(false);
  const [score, setScore] = useState(0);

  const handleAnswer = (questionIndex, answer) => {
    setAnswers({ ...answers, [questionIndex]: answer });
  };

  const handleSubmit = () => {
    let correctCount = 0;
    quiz.questions.forEach((question, index) => {
      if (answers[index] === question.correct_answer) {
        correctCount++;
      }
    });
    
    const finalScore = Math.round((correctCount / quiz.questions.length) * 100);
    setScore(finalScore);
    setShowResults(true);
    onQuizComplete(finalScore);
  };

  if (showResults) {
    return (
      <Card className="quiz-results">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">Quiz Results</CardTitle>
          <div className="text-4xl font-bold text-accent mt-2">{score}%</div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {quiz.questions.map((question, index) => (
              <div key={index} className="p-3 rounded-lg bg-muted/50">
                <p className="font-medium mb-2">{question.question}</p>
                <div className="flex items-center gap-2">
                  {answers[index] === question.correct_answer ? (
                    <CheckCircle className="h-4 w-4 text-green-500" />
                  ) : (
                    <Circle className="h-4 w-4 text-red-500" />
                  )}
                  <span className="text-sm text-muted-foreground">
                    {question.explanation}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  const question = quiz.questions[currentQuestion];

  return (
    <Card className="quiz-card">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Quiz Time!</CardTitle>
          <Badge>{currentQuestion + 1} of {quiz.questions.length}</Badge>
        </div>
        <Progress value={((currentQuestion + 1) / quiz.questions.length) * 100} />
      </CardHeader>
      <CardContent className="space-y-4">
        <h3 className="text-lg font-semibold">{question.question}</h3>
        
        {question.type === 'mcq' && (
          <div className="space-y-2">
            {question.options.map((option, index) => (
              <Button
                key={index}
                variant={answers[currentQuestion] === index ? "default" : "outline"}
                className="w-full text-left justify-start h-auto p-3"
                onClick={() => handleAnswer(currentQuestion, index)}
              >
                <span className="font-medium mr-2">{String.fromCharCode(65 + index)}.</span>
                {option}
              </Button>
            ))}
          </div>
        )}
        
        {question.type === 'true_false' && (
          <div className="flex gap-4">
            <Button
              variant={answers[currentQuestion] === true ? "default" : "outline"}
              className="flex-1"
              onClick={() => handleAnswer(currentQuestion, true)}
            >
              True
            </Button>
            <Button
              variant={answers[currentQuestion] === false ? "default" : "outline"}
              className="flex-1"
              onClick={() => handleAnswer(currentQuestion, false)}
            >
              False
            </Button>
          </div>
        )}
        
        {question.type === 'fill_blank' && (
          <Input
            placeholder="Type your answer..."
            onChange={(e) => handleAnswer(currentQuestion, e.target.value)}
            className="text-base"
          />
        )}

        <div className="flex justify-between pt-4">
          <Button
            variant="outline"
            onClick={() => setCurrentQuestion(Math.max(0, currentQuestion - 1))}
            disabled={currentQuestion === 0}
          >
            Previous
          </Button>
          
          {currentQuestion === quiz.questions.length - 1 ? (
            <Button
              onClick={handleSubmit}
              disabled={answers[currentQuestion] === undefined}
              className="primary-button"
            >
              Submit Quiz
            </Button>
          ) : (
            <Button
              onClick={() => setCurrentQuestion(currentQuestion + 1)}
              disabled={answers[currentQuestion] === undefined}
              className="primary-button"
            >
              Next
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

// Main Course View
const CourseView = ({ courseData, topicName }) => {
  const [completedLessons, setCompletedLessons] = useState([]);
  const [currentQuiz, setCurrentQuiz] = useState(null);
  const [lessonNotes, setLessonNotes] = useState({});
  const [quizScores, setQuizScores] = useState({});
  const [activeVideo, setActiveVideo] = useState(0);

  const handleLessonComplete = async (lessonId, notes) => {
    if (!completedLessons.includes(lessonId)) {
      setCompletedLessons([...completedLessons, lessonId]);
    }
    if (notes) {
      setLessonNotes({ ...lessonNotes, [lessonId]: notes });
    }

    // Save progress to backend
    try {
      await axios.post(`${API}/progress`, {
        course_id: courseData.id,
        topic: topicName,
        language: 'english', // You might want to track this
        mode: 'Mixed', // You might want to track this
        lessons_completed: [...completedLessons, lessonId],
        notes: { ...lessonNotes, [lessonId]: notes }
      }, { withCredentials: true });
    } catch (error) {
      console.error('Error saving progress:', error);
    }

    toast.success('Lesson completed!');
  };

  const handleQuizRequest = async (lessonId) => {
    try {
      const response = await axios.get(`${API}/quiz/${lessonId}`, {
        withCredentials: true
      });
      setCurrentQuiz(response.data);
    } catch (error) {
      console.error('Error loading quiz:', error);
      toast.error('Failed to load quiz');
    }
  };

  const handleQuizComplete = async (score) => {
    setQuizScores({ ...quizScores, [currentQuiz.lesson_id]: score });
    
    // Save quiz score
    try {
      await axios.post(`${API}/progress`, {
        course_id: courseData.id,
        topic: topicName,
        language: 'english',
        mode: 'Mixed',
        lessons_completed: completedLessons,
        quiz_scores: { ...quizScores, [currentQuiz.lesson_id]: score },
        notes: lessonNotes
      }, { withCredentials: true });
    } catch (error) {
      console.error('Error saving quiz score:', error);
    }

    toast.success(`Quiz completed! Score: ${score}%`);
    setTimeout(() => setCurrentQuiz(null), 3000);
  };

  const progressPercentage = (completedLessons.length / courseData.lessons.length) * 100;

  if (currentQuiz) {
    return (
      <div className="min-h-screen">
        <Navigation />
        <div className="p-4 max-w-4xl mx-auto">
          <div className="mb-6">
            <Button
              variant="outline"
              onClick={() => setCurrentQuiz(null)}
              className="mb-4"
            >
              ← Back to Course
            </Button>
          </div>
          <QuizView quiz={currentQuiz} onQuizComplete={handleQuizComplete} />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <Navigation />
      <div className="p-4 max-w-6xl mx-auto space-y-6">
        {/* Course Header */}
        <Card className="course-header">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-2xl">{topicName}</CardTitle>
                <CardDescription className="text-base mt-2">
                  {courseData.lessons.length} lessons • Interactive learning experience
                </CardDescription>
              </div>
            </div>
            <div className="mt-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium">Progress</span>
                <span className="text-sm text-muted-foreground">
                  {completedLessons.length} of {courseData.lessons.length} lessons
                </span>
              </div>
              <Progress value={progressPercentage} className="h-2" />
            </div>
          </CardHeader>
        </Card>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Video Section */}
          <div className="lg:col-span-1">
            <Card className="video-section">
              <CardHeader>
                <CardTitle className="text-lg">Course Videos</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <VideoPlayer
                  video={courseData.videos[activeVideo]}
                  isRecommended={activeVideo === 0}
                />
                
                {courseData.videos.length > 1 && (
                  <div className="space-y-2">
                    <h4 className="font-medium text-sm">Alternative Videos</h4>
                    {courseData.videos.slice(1).map((video, index) => (
                      <Button
                        key={index}
                        variant="outline"
                        size="sm"
                        className="w-full text-left justify-start h-auto p-2"
                        onClick={() => setActiveVideo(index + 1)}
                      >
                        <Play className="h-3 w-3 mr-2 flex-shrink-0" />
                        <span className="text-xs line-clamp-2">{video.title}</span>
                      </Button>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Lessons Section */}
          <div className="lg:col-span-2">
            <div className="space-y-6">
              {courseData.lessons
                .sort((a, b) => a.order - b.order)
                .map((lesson) => (
                  <LessonView
                    key={lesson.id}
                    lesson={lesson}
                    onComplete={handleLessonComplete}
                    isCompleted={completedLessons.includes(lesson.id)}
                    onQuizRequest={handleQuizRequest}
                  />
                ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// Profile Component
const Profile = () => {
  const { user } = useAuth();

  return (
    <div className="min-h-screen">
      <Navigation />
      <div className="p-4 max-w-4xl mx-auto">
        <Card>
          <CardHeader>
            <CardTitle>Profile</CardTitle>
            <CardDescription>Manage your account settings</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="flex items-center gap-4">
              <Avatar className="h-20 w-20">
                <AvatarImage src={user?.picture} />
                <AvatarFallback className="text-xl">{user?.name?.charAt(0)}</AvatarFallback>
              </Avatar>
              <div>
                <h3 className="text-xl font-semibold">{user?.name}</h3>
                <p className="text-muted-foreground">{user?.email}</p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium">Name</label>
                <Input value={user?.name || ''} disabled />
              </div>
              <div>
                <label className="text-sm font-medium">Email</label>
                <Input value={user?.email || ''} disabled />
              </div>
            </div>

            <div className="space-y-2">
              <h4 className="font-medium">Account Stats</h4>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-muted-foreground">Member since:</span>
                  <p>{new Date(user?.created_at).toLocaleDateString()}</p>
                </div>
                <div>
                  <span className="text-muted-foreground">Last login:</span>
                  <p>{user?.last_login ? new Date(user.last_login).toLocaleDateString() : 'Never'}</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

// My Courses Component
const MyCourses = () => {
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchMyCourses();
  }, []);

  const fetchMyCourses = async () => {
    try {
      const response = await axios.get(`${API}/my-courses`, { withCredentials: true });
      setCourses(response.data);
    } catch (error) {
      console.error('Error fetching courses:', error);
      toast.error('Failed to load courses');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen">
      <Navigation />
      <div className="p-4 max-w-6xl mx-auto">
        <Card>
          <CardHeader>
            <CardTitle>My Courses</CardTitle>
            <CardDescription>All your created courses</CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex items-center justify-center py-8">
                <div className="loader"></div>
                <span className="ml-2">Loading courses...</span>
              </div>
            ) : courses.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {courses.map((course) => (
                  <Card key={course.id} className="course-card">
                    <CardContent className="p-4">
                      <h3 className="font-semibold mb-2">
                        {course.lessons[0]?.title || 'Untitled Course'}
                      </h3>
                      <p className="text-sm text-muted-foreground mb-3">
                        {course.lessons.length} lessons
                      </p>
                      <Button size="sm" className="w-full" asChild>
                        <a href={`/course/${course.id}`}>Continue Learning</a>
                      </Button>
                    </CardContent>
                  </Card>
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <BookOpen className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                <p className="text-muted-foreground mb-4">No courses yet</p>
                <Button asChild>
                  <a href="/create-course">Create Your First Course</a>
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

// Protected Route Component
const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="loader mx-auto mb-4"></div>
          <p>Loading...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/auth" replace />;
  }

  return children;
};

// Main App Component
const MainApp = () => {
  const [courseData, setCourseData] = useState(null);
  const [topicName, setTopicName] = useState('');

  const handleCourseCreated = (data, topic) => {
    setCourseData(data);
    setTopicName(topic);
  };

  const handleBackToHome = () => {
    setCourseData(null);
    setTopicName('');
  };

  if (courseData) {
    return (
      <div>
        <div className="fixed top-4 left-4 z-50">
          <Button variant="outline" onClick={handleBackToHome}>
            ← Dashboard
          </Button>
        </div>
        <CourseView courseData={courseData} topicName={topicName} />
      </div>
    );
  }

  return (
    <Routes>
      <Route path="/auth" element={<AuthPage />} />
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="/dashboard" element={
        <ProtectedRoute>
          <Dashboard />
        </ProtectedRoute>
      } />
      <Route path="/create-course" element={
        <ProtectedRoute>
          <CourseCreator onCourseCreated={handleCourseCreated} />
        </ProtectedRoute>
      } />
      <Route path="/my-courses" element={
        <ProtectedRoute>
          <MyCourses />
        </ProtectedRoute>
      } />
      <Route path="/profile" element={
        <ProtectedRoute>
          <Profile />
        </ProtectedRoute>
      } />
    </Routes>
  );
};

function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <div className="App">
          <BrowserRouter>
            <MainApp />
          </BrowserRouter>
        </div>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;