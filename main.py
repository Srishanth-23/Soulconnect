from flask import Flask, request, jsonify
import functions_framework
import json
import random
import re
from datetime import datetime, timedelta
import hashlib
import base64
import os
import math

app = Flask(__name__)

# Initialize services with error handling
SERVICES_READY = False
speech_client = None
tts_client = None
language_client = None
translate_client = None
db = None

def initialize_services():
    """Initialize Google Cloud services with proper error handling"""
    global SERVICES_READY, speech_client, tts_client, language_client, translate_client, db
    
    try:
        from google.cloud import language_v1, firestore, speech, texttospeech, translate_v2 as translate
        
        # Only initialize if credentials are available
        try:
            language_client = language_v1.LanguageServiceClient()
            db = firestore.Client()
            speech_client = speech.SpeechClient()
            tts_client = texttospeech.TextToSpeechClient()
            translate_client = translate.Client()
            SERVICES_READY = True
            print("✅ All Google Cloud services initialized successfully")
        except Exception as cred_error:
            print(f"⚠️ Google Cloud services not available: {cred_error}")
            SERVICES_READY = False
            
    except ImportError as import_error:
        print(f"⚠️ Import error: {import_error}")
        SERVICES_READY = False

# Initialize on startup
initialize_services()

# MODERN INDIAN LANGUAGES
MODERN_INDIAN_LANGUAGES = {
    'hinglish': {'code': 'hi', 'region': 'IN', 'stt': 'hi-IN', 'tts': 'hi-IN-Wavenet-C', 'vibe': 'casual_modern'},
    'tanglish': {'code': 'ta', 'region': 'IN', 'stt': 'ta-IN', 'tts': 'ta-IN-Wavenet-A', 'vibe': 'chill_modern'},
    'tenglish': {'code': 'te', 'region': 'IN', 'stt': 'te-IN', 'tts': 'te-IN-Standard-A', 'vibe': 'friendly_modern'},
    'benglish': {'code': 'bn', 'region': 'IN', 'stt': 'bn-IN', 'tts': 'bn-IN-Wavenet-A', 'vibe': 'cool_modern'},
    'kanglish': {'code': 'kn', 'region': 'IN', 'stt': 'kn-IN', 'tts': 'kn-IN-Wavenet-A', 'vibe': 'buddy_modern'},
    'marglish': {'code': 'mr', 'region': 'IN', 'stt': 'mr-IN', 'tts': 'mr-IN-Wavenet-A', 'vibe': 'friend_modern'},
    'english_indian': {'code': 'en', 'region': 'IN', 'stt': 'en-IN', 'tts': 'en-IN-Wavenet-D', 'vibe': 'desi_modern'}
}

# EMERGENCY HELPLINES
EMERGENCY_HELPLINES = {
    'crisis_lines': [
        {'number': '9152987821', 'name': 'AASRA', 'available': '24/7'},
        {'number': '08046110007', 'name': 'Vandrevala Foundation', 'available': '24/7'},
        {'number': '1800-599-0019', 'name': 'KIRAN Mental Health', 'available': '24/7'},
        {'number': '112', 'name': 'Emergency Services', 'available': '24/7'}
    ]
}

# GAMIFICATION SYSTEM
GAMIFICATION_POINTS = {
    'chat': 5,
    'voice_chat': 10,
    'crisis_support_used': 50,  # Reward seeking help
    'activity_completed': 15,
    'daily_checkin': 20,
    'study_session': 25,
    'mood_tracking': 10,
    'exam_scheduled': 30,
    'schedule_followed': 35,
    'break_taken': 10,
    'goal_achieved': 40,
    'helping_friend': 30,
    'streak_milestone': 50
}

ACHIEVEMENTS = {
    'first_chat': {'points': 10, 'title': '👋 Hello Friend!', 'description': 'Had your first chat with Alex', 'rarity': 'common'},
    'week_streak': {'points': 100, 'title': '🔥 Consistent Warrior', 'description': '7 days in a row of mental wellness', 'rarity': 'rare'},
    'crisis_survivor': {'points': 200, 'title': '💪 Brave Soul', 'description': 'Reached out during tough times - true courage!', 'rarity': 'legendary'},
    'study_master': {'points': 150, 'title': '📚 Study Champion', 'description': '20 study sessions completed with Alex\'s help', 'rarity': 'epic'},
    'voice_explorer': {'points': 50, 'title': '🎤 Voice Friend', 'description': '10 voice messages with Alex', 'rarity': 'uncommon'},
    'schedule_keeper': {'points': 75, 'title': '📅 Time Master', 'description': 'Followed study schedule for 5 days straight', 'rarity': 'rare'},
    'mood_tracker': {'points': 60, 'title': '😊 Self-Aware', 'description': 'Tracked mood for 10 consecutive days', 'rarity': 'uncommon'},
    'exam_ace': {'points': 120, 'title': '🎯 Exam Warrior', 'description': 'Completed all scheduled study sessions before exam', 'rarity': 'epic'},
    'helper': {'points': 300, 'title': '🦸 Community Hero', 'description': 'Helped others in crisis situations', 'rarity': 'legendary'},
    'wellness_guru': {'points': 500, 'title': '🧘 Wellness Master', 'description': 'Achieved Level 10 in mental wellness journey', 'rarity': 'legendary'},
    'early_bird': {'points': 25, 'title': '🌅 Early Bird', 'description': 'Completed morning study sessions 7 times', 'rarity': 'common'},
    'night_owl': {'points': 25, 'title': '🦉 Night Owl', 'description': 'Completed evening study sessions 7 times', 'rarity': 'common'},
    'break_champion': {'points': 40, 'title': '☕ Break Champion', 'description': 'Took all scheduled breaks for a week', 'rarity': 'uncommon'},
    'goal_crusher': {'points': 200, 'title': '🚀 Goal Crusher', 'description': 'Achieved 10 study goals', 'rarity': 'epic'}
}

DAILY_CHALLENGES = [
    {
        'id': 'gratitude_boost',
        'title': '🙏 Gratitude Boost',
        'description': 'Share 3 things you\'re grateful for today with Alex',
        'points': 25,
        'type': 'gratitude',
        'estimated_time': '2 minutes',
        'difficulty': 'easy'
    },
    {
        'id': 'study_break_master',
        'title': '☕ Study Break Master',
        'description': 'Take a 10-minute mindful break during study time',
        'points': 30,
        'type': 'mindfulness',
        'estimated_time': '10 minutes',
        'difficulty': 'easy'
    },
    {
        'id': 'voice_connection',
        'title': '🎤 Voice Connection',
        'description': 'Send a voice message to Alex about your day',
        'points': 35,
        'type': 'voice_interaction',
        'estimated_time': '3 minutes',
        'difficulty': 'medium'
    },
    {
        'id': 'stress_buster',
        'title': '💆 Stress Buster',
        'description': 'Complete a stress-relief activity suggested by Alex',
        'points': 40,
        'type': 'activity',
        'estimated_time': '5 minutes',
        'difficulty': 'medium'
    },
    {
        'id': 'study_goal_setter',
        'title': '🎯 Study Goal Setter',
        'description': 'Set and achieve one small study goal today',
        'points': 45,
        'type': 'productivity',
        'estimated_time': '30 minutes',
        'difficulty': 'hard'
    },
    {
        'id': 'mood_check',
        'title': '😊 Mood Check-in',
        'description': 'Track your mood and share how you\'re feeling',
        'points': 20,
        'type': 'self_awareness',
        'estimated_time': '2 minutes',
        'difficulty': 'easy'
    },
    {
        'id': 'exam_prep',
        'title': '📝 Exam Prep Champion',
        'description': 'Complete a focused 25-minute study session',
        'points': 50,
        'type': 'study',
        'estimated_time': '25 minutes',
        'difficulty': 'hard'
    }
]

# EXAM SCHEDULING SYSTEM
EXAM_TYPES = {
    'entrance': {'difficulty_multiplier': 1.5, 'recommended_hours': 100, 'revision_days': 7},
    'semester': {'difficulty_multiplier': 1.2, 'recommended_hours': 40, 'revision_days': 5}, 
    'competitive': {'difficulty_multiplier': 1.8, 'recommended_hours': 150, 'revision_days': 10},
    'board': {'difficulty_multiplier': 1.3, 'recommended_hours': 60, 'revision_days': 7},
    'unit_test': {'difficulty_multiplier': 0.8, 'recommended_hours': 20, 'revision_days': 3}
}

SUBJECTS_DATA = {
    'mathematics': {'difficulty': 'high', 'hours_per_topic': 3, 'practice_ratio': 0.6},
    'physics': {'difficulty': 'high', 'hours_per_topic': 2.5, 'practice_ratio': 0.5},
    'chemistry': {'difficulty': 'medium', 'hours_per_topic': 2, 'practice_ratio': 0.4},
    'biology': {'difficulty': 'medium', 'hours_per_topic': 2, 'practice_ratio': 0.3},
    'english': {'difficulty': 'low', 'hours_per_topic': 1.5, 'practice_ratio': 0.2},
    'history': {'difficulty': 'low', 'hours_per_topic': 1.5, 'practice_ratio': 0.1},
    'computer_science': {'difficulty': 'high', 'hours_per_topic': 3, 'practice_ratio': 0.7}
}

# MODERN FRIEND RESPONSES (Previous responses + new gamified ones)
MODERN_FRIEND_RESPONSES = {
    'greeting': {
        'hinglish': [
            "Hey! I'm Alex, your friend here. 😊 How's it going? What's up?",
            "Yo! Alex here. Sup? How are you feeling today?",
            "Hey there! I'm Alex. What's happening? How's your day?",
            "Hi! Alex here, ready to chat. Kya chal raha hai? What's on your mind?"
        ],
        'english_indian': [
            "Hey! I'm Alex, here to chat. 😊 How's it going? What's up?",
            "Yo! Alex here. How are you doing today? What's on your mind?",
            "Hey there! I'm Alex, your supportive friend. How's everything?",
            "Hi! Alex here, ready to listen. What's happening in your life?"
        ]
    },
    
    'gamified_responses': {
        'level_up': [
            "🎉 LEVEL UP! You just reached Level {level}! Your mental wellness journey is inspiring! Keep crushing it! 💪",
            "🚀 Amazing! Level {level} achieved! You're becoming a true wellness warrior! So proud of you! ⭐",
            "🔥 Level {level} unlocked! Your consistency and self-care are paying off! You're unstoppable! 🌟"
        ],
        'achievement_unlocked': [
            "🏆 ACHIEVEMENT UNLOCKED: {title}! +{points} points! You're absolutely smashing your wellness goals! 🎊",
            "✨ Woohoo! New achievement: {title}! That's {points} points added to your awesomeness! 🎉",
            "💎 {title} achievement earned! +{points} points! Your dedication is incredible! Keep going! 🚀"
        ],
        'daily_challenge_complete': [
            "🌟 Daily challenge crushed! +{points} points! You're building amazing habits one day at a time! 💪",
            "🎯 Challenge completed! That's {points} points! Your commitment to wellness is inspiring! 🔥",
            "⚡ Daily challenge done! +{points} points! You're proving that small steps lead to big changes! 🌈"
        ]
    },
    
    'exam_schedule_responses': {
        'schedule_created': [
            "📅 Your personalized exam schedule is ready! I've optimized it based on your goals and energy patterns. You've got this! 💪",
            "🎯 Perfect! Your smart study schedule is all set up. I made sure to include breaks and stress-busters. Ready to ace those exams? 📚",
            "⚡ Schedule locked and loaded! I've balanced study time with wellness breaks. Your success is inevitable! 🚀"
        ],
        'schedule_reminder': [
            "⏰ Study session reminder! Time for {subject}. Remember, consistent effort beats cramming every time! You've got this! 📖",
            "🔔 Hey! Your {subject} session is starting. Take a deep breath, focus, and remember - I'm here if you need motivation! 💙",
            "📚 Study time! {subject} is up next. You're doing amazing by sticking to your schedule. Proud of you! ⭐"
        ]
    }
}

# STUDY ACTIVITIES AND BREAKS
STUDY_ACTIVITIES = {
    'focus_techniques': [
        {'name': 'Pomodoro Technique', 'duration': 25, 'description': '25 minutes focused study, 5-minute break'},
        {'name': 'Deep Work Session', 'duration': 90, 'description': '90 minutes of uninterrupted focus'},
        {'name': 'Active Recall', 'duration': 30, 'description': 'Test yourself without looking at notes'},
        {'name': 'Spaced Repetition', 'duration': 20, 'description': 'Review material at increasing intervals'}
    ],
    
    'break_activities': [
        {'name': 'Mindful Breathing', 'duration': 5, 'description': '4-7-8 breathing technique for relaxation'},
        {'name': 'Stretching Session', 'duration': 10, 'description': 'Full body stretches to release tension'},
        {'name': 'Gratitude Moment', 'duration': 3, 'description': 'Think of 3 things you\'re grateful for'},
        {'name': 'Progressive Muscle Relaxation', 'duration': 15, 'description': 'Tense and release muscle groups'},
        {'name': 'Quick Walk', 'duration': 10, 'description': 'Fresh air and light movement'},
        {'name': 'Hydration Break', 'duration': 2, 'description': 'Drink water and have a healthy snack'}
    ]
}

# Core functions from previous version (detect_natural_language, etc.)
def detect_natural_language(text):
    """Detect natural mixed language patterns"""
    text_lower = text.lower()
    language_patterns = {
        'hinglish': ['yaar', 'bhai', 'kya', 'hai', 'main', 'aur', 'but', 'like', 'actually', 'really'],
        'tanglish': ['da', 'anna', 'enna', 'but', 'actually', 'like', 'really', 'super', 'vera level'],
        'english_indian': ['actually', 'like', 'really', 'but', 'you know', 'right']
    }
    
    scores = {}
    for lang, markers in language_patterns.items():
        score = sum(2 if marker in text_lower else 0 for marker in markers)
        if score > 0:
            scores[lang] = score
    
    if not scores:
        return 'english_indian'
    return max(scores.items(), key=lambda x: x[1])[0]

# GAMIFICATION ENDPOINTS

@app.route('/gamification/profile', methods=['GET', 'POST'])
def gamification_profile():
    """Get or update user's gamification profile"""
    
    try:
        user_id = request.args.get('user_id') if request.method == 'GET' else request.json.get('user_id')
        
        if request.method == 'POST':
            action = request.json.get('action')
            points_earned = calculate_points(action)
            user_stats = update_user_gamification(user_id, action, points_earned)
            new_achievements = check_achievements(user_stats)
            motivation = generate_gamified_response(user_stats, new_achievements)
        else:
            user_stats = get_user_gamification(user_id)
            new_achievements = []
            motivation = generate_gamified_response(user_stats, [])
        
        return jsonify({
            'user_stats': user_stats,
            'new_achievements': new_achievements,
            'motivation_message': motivation,
            'daily_challenge': get_daily_challenge(user_stats),
            'next_level_requirements': calculate_next_level_requirements(user_stats),
            'recent_activities': get_recent_activities(user_id),
            'leaderboard_rank': get_user_leaderboard_rank(user_id)
        })
        
    except Exception as e:
        return jsonify({'error': str(e), 'fallback_stats': get_basic_user_stats()})

@app.route('/gamification/achievements', methods=['GET'])
def get_achievements():
    """Get all available achievements"""
    
    user_id = request.args.get('user_id')
    user_achievements = get_user_achievements(user_id) if user_id else []
    
    achievement_list = []
    for ach_id, ach_data in ACHIEVEMENTS.items():
        achievement_list.append({
            'id': ach_id,
            'title': ach_data['title'],
            'description': ach_data['description'],
            'points': ach_data['points'],
            'rarity': ach_data['rarity'],
            'unlocked': ach_id in user_achievements,
            'progress': get_achievement_progress(user_id, ach_id) if user_id else 0
        })
    
    return jsonify({
        'achievements': achievement_list,
        'total_achievements': len(ACHIEVEMENTS),
        'unlocked_count': len(user_achievements),
        'completion_percentage': (len(user_achievements) / len(ACHIEVEMENTS)) * 100
    })

@app.route('/gamification/daily-challenge', methods=['GET', 'POST'])
def daily_challenge():
    """Get daily challenge or complete it"""
    
    try:
        user_id = request.args.get('user_id') if request.method == 'GET' else request.json.get('user_id')
        
        if request.method == 'POST':
            # Complete daily challenge
            challenge_id = request.json.get('challenge_id')
            completion_data = request.json.get('completion_data', {})
            
            result = complete_daily_challenge(user_id, challenge_id, completion_data)
            return jsonify(result)
        else:
            # Get today's challenge
            challenge = get_daily_challenge_for_user(user_id)
            return jsonify(challenge)
            
    except Exception as e:
        return jsonify({'error': str(e), 'fallback_challenge': get_fallback_challenge()})

@app.route('/gamification/leaderboard', methods=['GET'])
def leaderboard():
    """Get leaderboard rankings"""
    
    try:
        leaderboard_type = request.args.get('type', 'points')  # points, level, streak
        limit = int(request.args.get('limit', 50))
        user_id = request.args.get('user_id')
        
        rankings = get_leaderboard_rankings(leaderboard_type, limit)
        user_rank = get_user_leaderboard_rank(user_id) if user_id else None
        
        return jsonify({
            'leaderboard': rankings,
            'user_rank': user_rank,
            'total_users': get_total_users_count(),
            'leaderboard_type': leaderboard_type,
            'last_updated': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e), 'message': 'Leaderboard temporarily unavailable'})

# EXAM SCHEDULING ENDPOINTS

@app.route('/exam-scheduler/create', methods=['POST'])
def create_exam_schedule():
    """Create optimized exam schedule"""
    
    try:
        data = request.json
        user_id = data.get('user_id')
        exams = data.get('exams', [])  # [{name, date, type, subjects, difficulty}]
        preferences = data.get('preferences', {})  # {daily_hours, break_interval, etc}
        
        # Generate optimized schedule
        schedule = generate_smart_exam_schedule(exams, preferences, user_id)
        
        # Store schedule in database
        if SERVICES_READY and db:
            store_user_schedule(user_id, schedule)
        
        # Award points for creating schedule
        update_user_gamification(user_id, 'exam_scheduled', 30)
        
        response_message = random.choice(MODERN_FRIEND_RESPONSES['exam_schedule_responses']['schedule_created'])
        
        return jsonify({
            'schedule': schedule,
            'optimization_summary': generate_optimization_summary(schedule),
            'wellness_plan': create_wellness_integration(schedule),
            'success_tips': generate_exam_success_tips(exams),
            'response_message': response_message,
            'estimated_success_rate': calculate_success_probability(schedule, exams)
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'fallback_schedule': generate_basic_schedule(exams if 'exams' in locals() else [])
        })

@app.route('/exam-scheduler/daily-plan', methods=['GET'])
def get_daily_study_plan():
    """Get today's study plan"""
    
    try:
        user_id = request.args.get('user_id')
        date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
        
        # Get user's schedule
        schedule = get_user_schedule(user_id)
        if not schedule:
            return jsonify({'error': 'No schedule found', 'message': 'Create your exam schedule first!'})
        
        # Generate today's plan
        daily_plan = generate_daily_plan(schedule, date)
        
        # Add motivational message
        motivation = generate_daily_motivation(daily_plan, user_id)
        
        return jsonify({
            'daily_plan': daily_plan,
            'motivation_message': motivation,
            'progress_summary': calculate_daily_progress(user_id, date),
            'upcoming_deadlines': get_upcoming_deadlines(schedule),
            'wellness_reminders': get_wellness_reminders(daily_plan)
        })
        
    except Exception as e:
        return jsonify({'error': str(e), 'fallback_plan': get_basic_daily_plan()})

@app.route('/exam-scheduler/progress', methods=['POST'])
def update_study_progress():
    """Update study session progress"""
    
    try:
        data = request.json
        user_id = data.get('user_id')
        session_data = data.get('session_data')  # {subject, duration, completed, quality}
        
        # Update progress
        progress_update = record_study_session(user_id, session_data)
        
        # Award points
        points_earned = calculate_study_points(session_data)
        user_stats = update_user_gamification(user_id, 'study_session', points_earned)
        
        # Check for achievements
        new_achievements = check_study_achievements(user_id, session_data)
        
        # Generate motivational response
        motivation = generate_study_completion_message(session_data, points_earned)
        
        return jsonify({
            'progress_update': progress_update,
            'points_earned': points_earned,
            'new_achievements': new_achievements,
            'motivation_message': motivation,
            'next_session': get_next_study_session(user_id),
            'performance_insights': analyze_study_performance(user_id)
        })
        
    except Exception as e:
        return jsonify({'error': str(e), 'message': 'Progress not updated, but great job studying!'})

@app.route('/exam-scheduler/analytics', methods=['GET'])
def get_study_analytics():
    """Get comprehensive study analytics"""
    
    try:
        user_id = request.args.get('user_id')
        timeframe = request.args.get('timeframe', '7d')  # 7d, 30d, all
        
        analytics = generate_study_analytics(user_id, timeframe)
        
        return jsonify({
            'analytics': analytics,
            'recommendations': generate_study_recommendations(analytics),
            'goal_tracking': get_goal_progress(user_id),
            'performance_trends': analyze_performance_trends(analytics),
            'wellness_correlation': analyze_wellness_study_correlation(user_id)
        })
        
    except Exception as e:
        return jsonify({'error': str(e), 'message': 'Analytics temporarily unavailable'})

# HELPER FUNCTIONS FOR GAMIFICATION

def calculate_points(action):
    """Calculate points for user actions"""
    return GAMIFICATION_POINTS.get(action, 5)

def update_user_gamification(user_id, action, points):
    """Update user's gamification stats"""
    if not SERVICES_READY or not db:
        return get_basic_user_stats()
    
    try:
        user_ref = db.collection('user_gamification').document(user_id)
        user_doc = user_ref.get()
        
        if user_doc.exists:
            stats = user_doc.to_dict()
        else:
            stats = initialize_user_gamification()
        
        # Add points
        stats['total_points'] += points
        stats['level'] = calculate_user_level(stats['total_points'])
        stats['progress_to_next_level'] = stats['total_points'] % 100
        
        # Update streak
        today = datetime.now().strftime('%Y-%m-%d')
        update_user_streak(stats, today)
        
        # Record activity
        record_user_activity(stats, action, points, today)
        
        # Store in database
        user_ref.set(stats)
        return stats
        
    except Exception as e:
        print(f"Gamification error: {e}")
        return get_basic_user_stats()

def get_user_gamification(user_id):
    """Get user's gamification data"""
    if not SERVICES_READY or not db:
        return get_basic_user_stats()
    
    try:
        user_doc = db.collection('user_gamification').document(user_id).get()
        if user_doc.exists:
            return user_doc.to_dict()
        else:
            return initialize_user_gamification()
    except:
        return get_basic_user_stats()

def initialize_user_gamification():
    """Initialize new user gamification data"""
    return {
        'total_points': 0,
        'level': 1,
        'current_streak': 0,
        'longest_streak': 0,
        'last_activity': None,
        'achievements': [],
        'daily_activities': {},
        'study_sessions': 0,
        'total_study_hours': 0,
        'goals_achieved': 0,
        'challenges_completed': [],
        'created_at': datetime.now().isoformat(),
        'progress_to_next_level': 0
    }

def calculate_user_level(total_points):
    """Calculate user level based on points"""
    return min((total_points // 100) + 1, 100)  # Max level 100

def check_achievements(user_stats):
    """Check for new achievements"""
    new_achievements = []
    current_achievements = user_stats.get('achievements', [])
    
    # Check various achievement conditions
    checks = {
        'first_chat': user_stats.get('total_points', 0) >= 10,
        'week_streak': user_stats.get('current_streak', 0) >= 7,
        'study_master': user_stats.get('study_sessions', 0) >= 20,
        'voice_explorer': user_stats.get('voice_messages', 0) >= 10,
        'schedule_keeper': user_stats.get('schedule_followed_days', 0) >= 5,
        'mood_tracker': user_stats.get('mood_entries', 0) >= 10,
        'exam_ace': user_stats.get('exams_completed', 0) >= 1,
        'wellness_guru': user_stats.get('level', 1) >= 10,
        'goal_crusher': user_stats.get('goals_achieved', 0) >= 10
    }
    
    for achievement_id, condition in checks.items():
        if condition and achievement_id not in current_achievements:
            new_achievements.append(achievement_id)
            current_achievements.append(achievement_id)
    
    user_stats['achievements'] = current_achievements
    return new_achievements

def generate_gamified_response(user_stats, new_achievements):
    """Generate motivational message based on gamification"""
    
    if new_achievements:
        achievement = new_achievements[0]  # Focus on first achievement
        achievement_data = ACHIEVEMENTS[achievement]
        return random.choice(MODERN_FRIEND_RESPONSES['gamified_responses']['achievement_unlocked']).format(
            title=achievement_data['title'],
            points=achievement_data['points']
        )
    
    level = user_stats.get('level', 1)
    points = user_stats.get('total_points', 0)
    streak = user_stats.get('current_streak', 0)
    
    if level > user_stats.get('last_level', 0):
        user_stats['last_level'] = level
        return random.choice(MODERN_FRIEND_RESPONSES['gamified_responses']['level_up']).format(level=level)
    elif streak >= 7:
        return f"🔥 {streak} day streak! You're absolutely crushing it at Level {level}! Your consistency is inspiring! 🌟"
    else:
        return f"💪 Great job! Level {level}, {points} points earned. Every step counts in your mental health journey! 🌟"

def get_daily_challenge_for_user(user_id):
    """Get personalized daily challenge for user"""
    
    # Get user's completed challenges to avoid repetition
    user_stats = get_user_gamification(user_id)
    completed_today = user_stats.get('daily_activities', {}).get(datetime.now().strftime('%Y-%m-%d'), {}).get('challenges', [])
    
    # Filter available challenges
    available_challenges = [c for c in DAILY_CHALLENGES if c['id'] not in completed_today]
    
    if not available_challenges:
        # User completed all challenges, give bonus challenge
        challenge = {
            'id': 'bonus_challenge',
            'title': '🌟 Bonus Challenge',
            'description': 'You\'ve completed all daily challenges! Share your success story with Alex',
            'points': 100,
            'type': 'bonus',
            'difficulty': 'epic'
        }
    else:
        # Select challenge based on user preferences/history
        challenge = select_personalized_challenge(available_challenges, user_stats)
    
    # Add weekend bonus
    if datetime.now().weekday() in [5, 6]:
        challenge['points'] = int(challenge['points'] * 1.5)
        challenge['weekend_bonus'] = True
    
    challenge['expires_at'] = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d 23:59:59')
    return challenge

def complete_daily_challenge(user_id, challenge_id, completion_data):
    """Complete a daily challenge"""
    
    challenge = next((c for c in DAILY_CHALLENGES if c['id'] == challenge_id), None)
    if not challenge:
        return {'error': 'Invalid challenge ID'}
    
    # Award points
    points = challenge['points']
    if datetime.now().weekday() in [5, 6]:  # Weekend bonus
        points = int(points * 1.5)
    
    user_stats = update_user_gamification(user_id, 'daily_challenge_completed', points)
    
    # Record challenge completion
    record_challenge_completion(user_id, challenge_id, completion_data)
    
    response_message = random.choice(MODERN_FRIEND_RESPONSES['gamified_responses']['daily_challenge_complete']).format(
        points=points
    )
    
    return {
        'success': True,
        'points_earned': points,
        'message': response_message,
        'next_challenge': get_daily_challenge_for_user(user_id),
        'total_points': user_stats['total_points'],
        'level': user_stats['level']
    }

# HELPER FUNCTIONS FOR EXAM SCHEDULING

def generate_smart_exam_schedule(exams, preferences, user_id):
    """Generate AI-optimized exam schedule"""
    
    if not exams:
        return {'error': 'No exams provided'}
    
    # Sort exams by date
    sorted_exams = sorted(exams, key=lambda x: datetime.strptime(x['date'], '%Y-%m-%d'))
    
    schedule = []
    current_date = datetime.now()
    
    for exam in sorted_exams:
        exam_date = datetime.strptime(exam['date'], '%Y-%m-%d')
        days_available = max((exam_date - current_date).days, 1)
        
        # Calculate required hours based on exam type and subjects
        exam_config = EXAM_TYPES.get(exam.get('type', 'semester'), EXAM_TYPES['semester'])
        subject_hours = calculate_subject_hours(exam.get('subjects', []), exam_config)
        
        # Generate daily schedule
        daily_plan = create_daily_study_plan(
            exam, subject_hours, days_available, preferences, exam_config
        )
        
        schedule.append({
            'exam_id': generate_exam_id(exam),
            'exam_name': exam['name'],
            'exam_date': exam['date'],
            'exam_type': exam.get('type', 'semester'),
            'subjects': exam.get('subjects', []),
            'total_study_hours': sum(subject_hours.values()),
            'days_available': days_available,
            'daily_plan': daily_plan,
            'revision_schedule': create_revision_schedule(exam, exam_config),
            'wellness_breaks': integrate_wellness_breaks(daily_plan),
            'stress_level_prediction': predict_stress_levels(daily_plan, exam),
            'success_probability': calculate_exam_success_probability(daily_plan, exam)
        })
        
        # Update current_date for next exam
        current_date = exam_date + timedelta(days=1)
    
    return {
        'user_id': user_id,
        'schedule': schedule,
        'created_at': datetime.now().isoformat(),
        'total_exams': len(exams),
        'study_start_date': datetime.now().strftime('%Y-%m-%d'),
        'last_exam_date': sorted_exams[-1]['date'],
        'optimization_notes': generate_optimization_notes(schedule)
    }

def calculate_subject_hours(subjects, exam_config):
    """Calculate required hours for each subject"""
    
    subject_hours = {}
    base_hours = exam_config['recommended_hours'] / len(subjects) if subjects else 20
    
    for subject in subjects:
        subject_data = SUBJECTS_DATA.get(subject.lower(), SUBJECTS_DATA.get('mathematics'))
        difficulty_multiplier = 1.0
        
        if subject_data['difficulty'] == 'high':
            difficulty_multiplier = 1.3
        elif subject_data['difficulty'] == 'low':
            difficulty_multiplier = 0.8
        
        subject_hours[subject] = int(base_hours * difficulty_multiplier)
    
    return subject_hours

def create_daily_study_plan(exam, subject_hours, days_available, preferences, exam_config):
    """Create detailed daily study plan"""
    
    max_daily_hours = preferences.get('max_daily_hours', 6)
    preferred_break_interval = preferences.get('break_interval', 90)  # minutes
    
    daily_plan = []
    remaining_hours = subject_hours.copy()
    
    for day in range(days_available - exam_config['revision_days']):
        current_date = datetime.now() + timedelta(days=day)
        
        # Distribute hours across subjects for this day
        day_schedule = distribute_daily_hours(
            remaining_hours, max_daily_hours, preferred_break_interval
        )
        
        # Add wellness integration
        day_schedule = add_wellness_activities(day_schedule, preferences)
        
        daily_plan.append({
            'date': current_date.strftime('%Y-%m-%d'),
            'day_of_week': current_date.strftime('%A'),
            'study_sessions': day_schedule['sessions'],
            'total_study_hours': day_schedule['total_hours'],
            'break_activities': day_schedule['breaks'],
            'wellness_score': calculate_wellness_score(day_schedule),
            'stress_level': predict_daily_stress(day_schedule),
            'motivation_tip': generate_daily_tip()
        })
        
        # Update remaining hours
        for session in day_schedule['sessions']:
            if session['subject'] in remaining_hours:
                remaining_hours[session['subject']] = max(
                    0, remaining_hours[session['subject']] - session['duration']
                )
    
    return daily_plan

def distribute_daily_hours(remaining_hours, max_daily_hours, break_interval):
    """Intelligently distribute study hours across subjects for a day"""
    
    sessions = []
    breaks = []
    total_hours = 0
    
    # Sort subjects by remaining hours (prioritize subjects with more hours left)
    sorted_subjects = sorted(remaining_hours.items(), key=lambda x: x[1], reverse=True)
    
    current_time = 9 * 60  # Start at 9 AM (in minutes)
    
    for subject, hours_left in sorted_subjects:
        if total_hours >= max_daily_hours or hours_left <= 0:
            break
        
        # Calculate session duration (1-3 hours per session)
        session_duration = min(3, hours_left, max_daily_hours - total_hours)
        
        if session_duration > 0:
            sessions.append({
                'subject': subject,
                'start_time': f"{current_time // 60:02d}:{current_time % 60:02d}",
                'duration': session_duration,
                'end_time': f"{(current_time + session_duration * 60) // 60:02d}:{(current_time + session_duration * 60) % 60:02d}",
                'type': 'focused_study',
                'techniques': get_study_techniques_for_subject(subject)
            })
            
            total_hours += session_duration
            current_time += session_duration * 60
            
            # Add break after session
            if total_hours < max_daily_hours:
                break_duration = 15 if session_duration <= 1 else 30
                breaks.append({
                    'start_time': f"{current_time // 60:02d}:{current_time % 60:02d}",
                    'duration': break_duration,
                    'activity': get_recommended_break_activity(session_duration),
                    'type': 'wellness_break'
                })
                current_time += break_duration
    
    return {
        'sessions': sessions,
        'breaks': breaks,
        'total_hours': total_hours
    }

def get_study_techniques_for_subject(subject):
    """Get recommended study techniques for subject"""
    
    subject_data = SUBJECTS_DATA.get(subject.lower(), SUBJECTS_DATA['mathematics'])
    techniques = ['active_reading', 'note_taking']
    
    if subject_data['practice_ratio'] > 0.5:
        techniques.extend(['practice_problems', 'mock_tests'])
    
    if subject_data['difficulty'] == 'high':
        techniques.append('concept_mapping')
    
    return techniques

def get_recommended_break_activity(session_duration):
    """Get recommended break activity based on session length"""
    
    if session_duration >= 2:
        return random.choice(['stretching_session', 'quick_walk', 'mindful_breathing'])
    else:
        return random.choice(['hydration_break', 'gratitude_moment', 'eye_rest'])

# Core chat endpoints (keeping existing functionality)
@app.route('/', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'SoulConnect Advanced API with Gamification & Scheduling',
        'version': '3.0.0',
        'timestamp': datetime.now().isoformat(),
        'services_ready': SERVICES_READY,
        'features': {
            'chat': True,
            'voice': SERVICES_READY,
            'gamification': True,
            'exam_scheduling': True,
            'crisis_support': True,
            'multilingual': True
        }
    })

@app.route('/chat', methods=['POST'])
def natural_chat():
    """Enhanced chat with gamification integration"""
    
    try:
        user_message = request.json.get('text', '') if request.json else ''
        user_id = request.json.get('user_id', f'user_{hashlib.md5(user_message.encode()).hexdigest()[:8]}')
        
        if not user_message.strip():
            return jsonify({'error': 'Message cannot be empty'}), 400
        
        # Award points for chatting
        user_stats = update_user_gamification(user_id, 'chat', 5)
        
        # Simple assessment (keeping existing logic)
        assessment = assess_situation_naturally(user_message)
        
        # Generate natural response (keeping existing logic)
        response_data = generate_natural_response(user_message, assessment)
        
        # Add gamification elements to response
        if user_stats['level'] > user_stats.get('last_notified_level', 0):
            user_stats['last_notified_level'] = user_stats['level']
            response_data['level_up_message'] = random.choice(
                MODERN_FRIEND_RESPONSES['gamified_responses']['level_up']
            ).format(level=user_stats['level'])
        
        # Get sentiment analysis (keeping existing logic)
        sentiment_data = get_sentiment_analysis(user_message)
        
        return jsonify({
            'response': response_data['response'],
            'language_detected': assessment['language_preference'],
            'conversation_id': user_id,
            'friend_name': 'Alex',
            'gamification': {
                'points_earned': 5,
                'total_points': user_stats['total_points'],
                'level': user_stats['level'],
                'progress_to_next_level': user_stats['progress_to_next_level'],
                'current_streak': user_stats['current_streak']
            },
            'level_up_message': response_data.get('level_up_message'),
            'urgency': response_data['urgency'],
            'sentiment_score': sentiment_data['score'],
            'daily_challenge_available': bool(get_daily_challenge_for_user(user_id))
        })
        
    except Exception as e:
        print(f"Chat error: {e}")
        return jsonify({
            'response': "Hey! I'm Alex, your supportive friend. 😊 How can I help you today?",
            'error': str(e),
            'status': 'fallback',
            'friend_name': 'Alex'
        }), 200

# Previous helper functions (keeping existing ones)
def assess_situation_naturally(message, voice_analysis=None):
    """Simple, natural situation assessment"""
    
    message_lower = message.lower()
    
    crisis_words = ['kill myself', 'want to die', 'suicide', 'end it all', 'hurt myself']
    high_stress_words = ['can\'t cope', 'overwhelmed', 'breaking down', 'too much']
    academic_words = ['exam', 'study', 'grades', 'college', 'pressure', 'competition']
    
    assessment = {
        'needs_help': False,
        'main_concern': 'general',
        'urgency': 'normal',
        'language_preference': 'english_indian'
    }
    
    if any(word in message_lower for word in crisis_words):
        assessment['needs_help'] = True
        assessment['urgency'] = 'crisis'
        assessment['main_concern'] = 'crisis'
    elif any(word in message_lower for word in high_stress_words):
        assessment['needs_help'] = True
        assessment['urgency'] = 'high'
        assessment['main_concern'] = 'stress'
    elif any(word in message_lower for word in academic_words):
        assessment['main_concern'] = 'academic'
    
    assessment['language_preference'] = detect_natural_language(message)
    return assessment

def generate_natural_response(message, assessment):
    """Generate natural, friend-like response"""
    
    language = assessment['language_preference']
    urgency = assessment['urgency']
    
    if urgency == 'crisis':
        crisis_response = "Hey, I can tell you're going through something really tough right now. 💙 I'm here with you. Are you safe? Let's talk about what's happening."
        helplines = "If you need immediate help, these numbers are available 24/7: AASRA (9152987821), Vandrevala Foundation (08046110007), Emergency (112)"
        
        return {
            'response': crisis_response,
            'additional_info': helplines,
            'urgency': 'crisis',
            'follow_up_needed': True
        }
    
    # Handle greetings
    if any(word in message.lower() for word in ['hi', 'hello', 'hey', 'sup', 'yo']):
        response_pool = MODERN_FRIEND_RESPONSES['greeting']
        response = random.choice(response_pool.get(language, response_pool['english_indian']))
    else:
        response = "I can hear that you're dealing with something tough. 💙 That takes courage to share. What would help most right now?"
    
    return {
        'response': response,
        'urgency': urgency,
        'language_used': language,
        'natural_conversation': True
    }

def get_sentiment_analysis(text):
    """Get sentiment analysis if service is available"""
    
    if not SERVICES_READY or not language_client:
        negative_words = ['sad', 'angry', 'stressed', 'worried', 'depressed', 'anxious']
        positive_words = ['happy', 'good', 'great', 'awesome', 'excited', 'love']
        
        text_lower = text.lower()
        neg_score = sum(1 for word in negative_words if word in text_lower)
        pos_score = sum(1 for word in positive_words if word in text_lower)
        
        if neg_score > pos_score:
            return {'score': -0.5, 'magnitude': 0.7}
        elif pos_score > neg_score:
            return {'score': 0.5, 'magnitude': 0.7}
        else:
            return {'score': 0.0, 'magnitude': 0.5}
    
    try:
        from google.cloud import language_v1
        document = language_v1.Document(content=text, type_=language_v1.Document.Type.PLAIN_TEXT)
        result = language_client.analyze_sentiment(request={'document': document})
        return {'score': result.document_sentiment.score, 'magnitude': result.document_sentiment.magnitude}
    except Exception as e:
        print(f"Sentiment analysis error: {e}")
        return {'score': 0.0, 'magnitude': 0.5}

# Placeholder helper functions (implement as needed)
def get_basic_user_stats():
    return {
        'total_points': 0, 'level': 1, 'current_streak': 0,
        'progress_to_next_level': 0, 'achievements': []
    }

def generate_exam_id(exam):
    return hashlib.md5(f"{exam['name']}_{exam['date']}".encode()).hexdigest()[:8]

def get_user_schedule(user_id):
    return None  # Implement database retrieval

def generate_daily_tip():
    tips = [
        "Remember to take breaks! Your brain needs rest to consolidate learning.",
        "Stay hydrated and eat brain-healthy foods during study sessions.",
        "Practice active recall - test yourself without looking at notes!",
        "Get enough sleep. A well-rested mind learns much better.",
        "Use the Pomodoro technique: 25 minutes study, 5 minutes break."
    ]
    return random.choice(tips)

@functions_framework.http
def app_entry(request):
    """Entry point for Cloud Functions"""
    try:
        return app(request.environ, lambda status, headers: None)
    except Exception as e:
        print(f"Function entry error: {e}")
        return jsonify({'error': 'Service temporarily unavailable', 'status': 'error'}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)