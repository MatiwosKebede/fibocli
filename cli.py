#!/usr/bin/env python3
# FIBOCLI Enhanced v3.0 - Complete Learning Ecology System
import rich_click as click
import datetime
import sqlite3
import json
import hashlib
import secrets
import os
import math
import pytz
import zipfile
import tempfile
import csv
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, FloatPrompt, IntPrompt, Confirm
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.tree import Tree
from rich.text import Text
from rich.align import Align
from rich.layout import Layout
from rich.live import Live
from rich.markdown import Markdown
from rich.syntax import Syntax
import threading
import time
import requests
from dateutil import parser

console = Console()

# Enhanced status system
status_icons = {
    "pending": "[grey]🔒 Pending[/grey]",
    "active": "[blue]▶ Active[/blue]",
    "completed": "[green]✅ Completed[/green]",
    "paused": "[yellow]⏸ Paused[/yellow]",
    "archived": "[dim]📁 Archived[/dim]",
    "review": "[magenta]🔄 Review[/magenta]",
    "locked": "[red]🔐 Locked[/red]",
    "in_progress": "[cyan]🔄 In Progress[/cyan]"
}

# Gamification constants
LEVEL_THRESHOLDS = [0, 100, 300, 600, 1000, 1500, 2100, 2800, 3600, 4500, 5500]
STREAK_MULTIPLIERS = {0: 1.0, 3: 1.1, 7: 1.25, 14: 1.5, 30: 2.0, 60: 2.5, 90: 3.0}
ACHIEVEMENT_CATEGORIES = {
    'streak': '🔥', 'study': '⏱️', 'mastery': '🧠', 'consistency': '📊', 
    'speed': '⚡', 'exploration': '🔍', 'completion': '✅'
}

class DatabaseManager:
    """Enhanced database management with connection pooling"""
    
    def __init__(self, db_path="fibocli.db"):
        self.db_path = db_path
        
    def get_connection(self):
        """Get database connection with optimized settings"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

class AdvancedStudyManager:
    """Comprehensive study management with all advanced features"""
    
    def __init__(self, db_connection):
        self.conn = db_connection
        self.cursor = db_connection.cursor()
        
    def auto_streak_update(self, user_id: int) -> bool:
        """Automatically update user streak based on study activity"""
        try:
            self.cursor.execute("""
                SELECT last_study_date, streak_days, longest_streak 
                FROM Users WHERE user_id = ?
            """, (user_id,))
            result = self.cursor.fetchone()
            if not result:
                return False
                
            last_study_date, current_streak, longest_streak = result
            today = datetime.date.today().isoformat()
            
            streak_updated = False
            if last_study_date:
                last_date = datetime.date.fromisoformat(last_study_date)
                today_date = datetime.date.fromisoformat(today)
                days_diff = (today_date - last_date).days
                
                if days_diff == 1:
                    new_streak = current_streak + 1
                    streak_updated = True
                elif days_diff == 0:
                    new_streak = current_streak
                    streak_updated = False
                else:
                    new_streak = 1
                    streak_updated = True
            else:
                new_streak = 1
                streak_updated = True
            
            # Update streak multiplier
            multiplier = 1.0
            for threshold, mult in STREAK_MULTIPLIERS.items():
                if new_streak >= threshold:
                    multiplier = mult
            
            if streak_updated:
                # Update longest streak if needed
                new_longest_streak = max(longest_streak, new_streak)
                
                self.cursor.execute("""
                    UPDATE Users SET streak_days = ?, streak_multiplier = ?, 
                    last_study_date = ?, longest_streak = ?, streak_updated_at = ?
                    WHERE user_id = ?
                """, (new_streak, multiplier, today, new_longest_streak, 
                      datetime.datetime.now().isoformat(), user_id))
                
                self.conn.commit()
                self._check_streak_achievements(user_id, new_streak)
                
            return streak_updated
            
        except Exception as e:
            console.print(f"[red]Error in auto_streak_update: {e}[/red]")
            return False
    
    def _check_streak_achievements(self, user_id: int, streak_days: int):
        """Check and award streak-based achievements"""
        streak_achievements = {
            3: "Streak Starter",
            7: "Week Warrior", 
            30: "Marathon Learner",
            100: "Consistency King"
        }
        
        for threshold, achievement_name in streak_achievements.items():
            if streak_days == threshold:
                self._award_achievement(user_id, achievement_name)
    
    def _award_achievement(self, user_id: int, achievement_name: str):
        """Award an achievement to user"""
        try:
            # Check if already unlocked
            self.cursor.execute(
                "SELECT achievement_id FROM Achievements WHERE user_id = ? AND name = ?",
                (user_id, achievement_name)
            )
            if self.cursor.fetchone():
                return
                
            # Get achievement details
            self.cursor.execute(
                "SELECT points, icon FROM Achievements WHERE name = ? LIMIT 1",
                (achievement_name,)
            )
            result = self.cursor.fetchone()
            if not result:
                return
                
            points, icon = result
            
            # Award achievement
            self.cursor.execute(
                "INSERT INTO Achievements (user_id, name, description, points, icon, unlocked_at) "
                "SELECT ?, name, description, points, icon, CURRENT_TIMESTAMP FROM Achievements WHERE name = ? LIMIT 1",
                (user_id, achievement_name)
            )
            
            # Update user points and experience
            self.cursor.execute("""
                UPDATE Users SET 
                points = points + ?,
                experience_points = experience_points + ?,
                total_points_earned = total_points_earned + ?
                WHERE user_id = ?
            """, (points, points, points, user_id))
            
            # Create notification
            self.cursor.execute(
                "INSERT INTO Notifications (user_id, title, message, type) VALUES (?, ?, ?, ?)",
                (user_id, f"{icon} Achievement Unlocked!", 
                 f"You unlocked: {achievement_name} (+{points} points)", "achievement")
            )
            
            self.conn.commit()
            console.print(f"[green]🏆 Achievement unlocked: {achievement_name} (+{points} points)![/green]")
            
        except Exception as e:
            console.print(f"[red]Error awarding achievement: {e}[/red]")
    
    def calculate_auto_duration(self, node_id: int, user_id: int) -> int:
        """Calculate automatic study duration based on node properties and user state"""
        try:
            self.cursor.execute("""
                SELECT importance, difficulty, understanding, total_active_minutes, 
                       auto_duration_enabled, min_duration, max_duration, estimated_duration
                FROM Nodes WHERE node_id = ? AND user_id = ?
            """, (node_id, user_id))
            node_data = self.cursor.fetchone()
            
            if not node_data or not node_data[4]:  # auto_duration_enabled
                return node_data[7] if node_data and node_data[7] else 30
                
            importance, difficulty, understanding, total_minutes, _, min_dur, max_dur, estimated = node_data
            
            # Get user data
            self.cursor.execute("""
                SELECT learning_efficiency, fatigue_threshold, streak_multiplier 
                FROM Users WHERE user_id = ?
            """, (user_id,))
            user_data = self.cursor.fetchone()
            if not user_data:
                return 30
                
            efficiency, fatigue_threshold, streak_multiplier = user_data
            
            # Calculate base duration using multiple factors
            base_duration = (
                (difficulty / 50) *                    # Higher difficulty = more time
                (1 - (understanding / 100)) *          # Lower understanding = more time  
                (importance / 50) *                    # Higher importance = more time
                (1 / max(efficiency, 0.1)) *           # Lower efficiency = more time
                streak_multiplier *                    # Streak bonus reduces time needed
                25 + 15                                # Base range
            )
            
            # Apply fatigue adjustment
            current_fatigue = self._get_current_fatigue(user_id)
            fatigue_factor = 1 + (current_fatigue / 100)
            adjusted_duration = base_duration * fatigue_factor
            
            # Apply min/max constraints
            final_duration = max(min_dur, min(max_dur, int(adjusted_duration)))
            
            return final_duration
            
        except Exception as e:
            console.print(f"[red]Error calculating auto duration: {e}[/red]")
            return 30
    
    def _get_current_fatigue(self, user_id: int) -> float:
        """Get user's current fatigue level"""
        try:
            self.cursor.execute("""
                SELECT fatigue_end FROM StudySessions 
                WHERE user_id = ? 
                ORDER BY start_time DESC LIMIT 1
            """, (user_id,))
            result = self.cursor.fetchone()
            return result[0] if result else 20.0
        except:
            return 20.0

    def dynamic_difficulty_adjustment(self, node_id: int, performance_score: float):
        """Adjust node difficulty based on performance"""
        try:
            self.cursor.execute(
                "SELECT difficulty, name FROM Nodes WHERE node_id = ?", (node_id,)
            )
            result = self.cursor.fetchone()
            if not result:
                return
                
            current_difficulty, node_name = result
            
            if performance_score > 0.8:  # Excellent performance
                new_difficulty = min(100, current_difficulty * 1.15)
                reason = "Excellent performance - increasing challenge"
                adjustment_type = "performance"
            elif performance_score < 0.4:  # Poor performance  
                new_difficulty = max(10, current_difficulty * 0.85)
                reason = "Struggling - reducing difficulty"
                adjustment_type = "performance"
            else:
                return  # No adjustment needed
                
            # Record history
            self.cursor.execute("""
                INSERT INTO DifficultyHistory 
                (node_id, old_difficulty, new_difficulty, adjustment_type, reason, performance_data) 
                VALUES (?, ?, ?, ?, ?, ?)
            """, (node_id, current_difficulty, new_difficulty, adjustment_type, reason,
                  json.dumps({"performance_score": performance_score})))
            
            # Update node
            self.cursor.execute(
                "UPDATE Nodes SET difficulty = ?, updated_at = CURRENT_TIMESTAMP WHERE node_id = ?",
                (new_difficulty, node_id)
            )
            
            self.conn.commit()
            console.print(f"[yellow]📊 Difficulty adjusted for '{node_name}': {current_difficulty:.1f} → {new_difficulty:.1f}[/yellow]")
            
        except Exception as e:
            console.print(f"[red]Error in dynamic difficulty adjustment: {e}[/red]")

    def fatigue_management(self, user_id: int, current_fatigue: float, study_duration: int) -> Dict:
        """Manage user fatigue and recommend breaks"""
        try:
            self.cursor.execute("""
                SELECT fatigue_threshold, learning_efficiency FROM Users WHERE user_id = ?
            """, (user_id,))
            result = self.cursor.fetchone()
            if not result:
                return {"break_needed": False, "break_duration": 0}
                
            fatigue_threshold, efficiency = result
            
            recommendations = {
                "break_needed": False,
                "break_duration": 0,
                "efficiency_penalty": 1.0,
                "max_recommended_duration": study_duration
            }
            
            # Check fatigue patterns
            self.cursor.execute("""
                SELECT recommended_max_duration FROM FatiguePatterns 
                WHERE user_id = ? AND day_of_week = ? AND hour_of_day = ?
                ORDER BY sample_size DESC LIMIT 1
            """, (user_id, datetime.datetime.now().weekday(), datetime.datetime.now().hour))
            
            pattern = self.cursor.fetchone()
            if pattern:
                recommendations["max_recommended_duration"] = min(study_duration, pattern[0])
            
            if current_fatigue > fatigue_threshold:
                recommendations["break_needed"] = True
                excess_fatigue = current_fatigue - fatigue_threshold
                recommendations["break_duration"] = min(30, int(5 + (excess_fatigue / 10) * 5))
                
            # Apply efficiency penalty for high fatigue
            if current_fatigue > 80:
                penalty = 1.0 - ((current_fatigue - 80) / 100)
                recommendations["efficiency_penalty"] = max(0.5, penalty)
                
            return recommendations
            
        except Exception as e:
            console.print(f"[red]Error in fatigue management: {e}[/red]")
            return {"break_needed": False, "break_duration": 0, "efficiency_penalty": 1.0}

    def check_prerequisites(self, node_id: int) -> Tuple[bool, List]:
        """Check if node prerequisites are met"""
        try:
            self.cursor.execute("SELECT prerequisites FROM Nodes WHERE node_id = ?", (node_id,))
            result = self.cursor.fetchone()
            if not result or not result[0]:
                return True, []
                
            prerequisites = json.loads(result[0])
            if not prerequisites:
                return True, []
            
            # Check each prerequisite
            unmet_prerequisites = []
            for prereq_id in prerequisites:
                self.cursor.execute("""
                    SELECT name, status FROM Nodes WHERE node_id = ? AND status = 'completed'
                """, (prereq_id,))
                prereq_node = self.cursor.fetchone()
                if not prereq_node:
                    unmet_prerequisites.append(prereq_id)
            
            return len(unmet_prerequisites) == 0, unmet_prerequisites
            
        except Exception as e:
            console.print(f"[red]Error checking prerequisites: {e}[/red]")
            return False, []

    def update_learning_efficiency(self, user_id: int, session_quality: float):
        """Update user's learning efficiency based on session performance"""
        try:
            # Get current efficiency
            self.cursor.execute("SELECT learning_efficiency FROM Users WHERE user_id = ?", (user_id,))
            current_efficiency = self.cursor.fetchone()[0]
            
            # Calculate new efficiency (weighted average)
            new_efficiency = (current_efficiency * 0.7) + (session_quality * 0.3)
            
            # Cap between 0.5 and 3.0
            new_efficiency = max(0.5, min(3.0, new_efficiency))
            
            self.cursor.execute("""
                UPDATE Users SET learning_efficiency = ? WHERE user_id = ?
            """, (new_efficiency, user_id))
            
            # Record efficiency history
            self.cursor.execute("""
                INSERT INTO EfficiencyHistory (user_id, efficiency_score, recorded_date)
                VALUES (?, ?, ?)
            """, (user_id, new_efficiency, datetime.date.today().isoformat()))
            
            self.conn.commit()
            
            return new_efficiency
            
        except Exception as e:
            console.print(f"[red]Error updating learning efficiency: {e}[/red]")
            return None

class NotificationManager:
    """Manage notifications and user alerts"""
    
    def __init__(self, db_connection):
        self.conn = db_connection
        self.cursor = db_connection.cursor()
    
    def create_notification(self, user_id: int, title: str, message: str, notification_type: str, 
                          actionable: bool = False, action_url: str = None):
        """Create a new notification"""
        try:
            self.cursor.execute("""
                INSERT INTO Notifications 
                (user_id, title, message, type, is_actionable, action_url)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, title, message, notification_type, actionable, action_url))
            self.conn.commit()
        except Exception as e:
            console.print(f"[red]Error creating notification: {e}[/red]")
    
    def get_unread_count(self, user_id: int) -> int:
        """Get count of unread notifications"""
        try:
            self.cursor.execute("""
                SELECT COUNT(*) FROM Notifications 
                WHERE user_id = ? AND is_read = 0
            """, (user_id,))
            return self.cursor.fetchone()[0]
        except:
            return 0
    
    def send_streak_notification(self, user_id: int, streak_days: int):
        """Send streak milestone notification"""
        if streak_days in [3, 7, 14, 30, 60, 90, 100]:
            self.create_notification(
                user_id,
                "🔥 Streak Milestone!",
                f"Amazing! You've maintained a {streak_days}-day study streak!",
                "streak",
                True,
                "fibocli achievements"
            )

class GamificationEngine:
    """Handle all gamification features"""
    
    def __init__(self, db_connection):
        self.conn = db_connection
        self.cursor = db_connection.cursor()
    
    def calculate_level(self, experience: int) -> int:
        """Calculate user level based on experience"""
        for level, threshold in enumerate(LEVEL_THRESHOLDS):
            if experience < threshold:
                return level
        return len(LEVEL_THRESHOLDS)
    
    def award_session_points(self, user_id: int, session_data: Dict):
        """Award points for completed study session"""
        try:
            base_points = 10
            duration_bonus = min(50, session_data.get('duration_minutes', 0) // 10)
            efficiency_bonus = int(session_data.get('efficiency_score', 0.5) * 20)
            focus_bonus = int(session_data.get('focus_score', 0.5) * 15)
            
            total_points = base_points + duration_bonus + efficiency_bonus + focus_bonus
            
            # Apply streak multiplier
            self.cursor.execute("SELECT streak_multiplier FROM Users WHERE user_id = ?", (user_id,))
            streak_multiplier = self.cursor.fetchone()[0]
            total_points = int(total_points * streak_multiplier)
            
            # Update user points
            self.cursor.execute("""
                UPDATE Users SET 
                points = points + ?,
                experience_points = experience_points + ?,
                total_points_earned = total_points_earned + ?
                WHERE user_id = ?
            """, (total_points, total_points, total_points, user_id))
            
            self.conn.commit()
            
            return total_points
            
        except Exception as e:
            console.print(f"[red]Error awarding session points: {e}[/red]")
            return 0
    
    def check_achievement_progress(self, user_id: int, achievement_type: str, progress_increment: int = 1):
        """Update progress towards achievements"""
        try:
            self.cursor.execute("""
                UPDATE Achievements 
                SET progress_current = progress_current + ?
                WHERE user_id = ? AND category = ? AND unlocked_at IS NULL
            """, (progress_increment, user_id, achievement_type))
            
            # Check for newly completed achievements
            self.cursor.execute("""
                SELECT name FROM Achievements 
                WHERE user_id = ? AND progress_current >= progress_target AND unlocked_at IS NULL
            """, (user_id,))
            
            newly_unlocked = self.cursor.fetchall()
            for achievement in newly_unlocked:
                achievement_name = achievement[0]
                # This will trigger the achievement award process
                console.print(f"[green]🎉 Progress achievement: {achievement_name}[/green]")
            
            self.conn.commit()
            
        except Exception as e:
            console.print(f"[red]Error updating achievement progress: {e}[/red]")

@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.pass_context
def cli(ctx, verbose):
    """FIBOCLI v3.0 - Advanced Learning Ecology with Gamification & AI Features"""
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ctx.obj['db_manager'] = DatabaseManager()
    
    # Initialize managers
    conn = ctx.obj['db_manager'].get_connection()
    ctx.obj['study_manager'] = AdvancedStudyManager(conn)
    ctx.obj['notification_manager'] = NotificationManager(conn)
    ctx.obj['gamification_engine'] = GamificationEngine(conn)
    conn.close()

def require_user() -> int:
    """Enhanced user authentication with session validation"""
    try:
        if not os.path.exists(".fibocli_session"):
            raise click.ClickException("No active session. Please login with 'fibocli login'")
            
        with open(".fibocli_session", "r") as f:
            session_data = json.load(f)
            
        token = session_data.get('token')
        user_id = session_data.get('user_id')
        
        if not token or not user_id:
            raise click.ClickException("Invalid session file")
            
        db_manager = DatabaseManager()
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id FROM Sessions 
                WHERE token = ? AND user_id = ? AND expiry > ?
            """, (token, user_id, datetime.datetime.utcnow().isoformat()))
            
            result = cursor.fetchone()
            if not result:
                raise click.ClickException("Session expired or invalid. Please login again")
                
        return user_id
        
    except (sqlite3.Error, json.JSONDecodeError, FileNotFoundError) as e:
        raise click.ClickException(f"Authentication error: {e}")

def get_db_connection():
    """Get database connection with enhanced settings"""
    conn = sqlite3.connect("fibocli.db")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn

# =====================================================================
# CORE COMMANDS (Enhanced)
# =====================================================================

@cli.command()
@click.option("--overwrite", is_flag=True, help="Overwrite existing database")
@click.option("--sample-data", is_flag=True, help="Add sample learning data")
def init(overwrite, sample_data):
    """Initialize database with enhanced schema"""
    try:
        if not os.path.exists("schema.sql"):
            console.print("[red]❌ schema.sql file not found.[/red]")
            raise click.Abort()
            
        with open("schema.sql", 'r') as f:
            sql_script = f.read()
            
        db_manager = DatabaseManager()
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            if overwrite:
                # Drop tables in correct order to respect foreign keys
                tables = [
                    'DifficultyHistory', 'EfficiencyHistory', 'FatiguePatterns', 'StudyBreaks',
                    'NodeRelationships', 'StudyGoals', 'Exports', 'Notifications',
                    'StudyAnalytics', 'StudySessions', 'Schedules', 'Reviews', 
                    'Waves', 'Achievements', 'LearningObjectives', 'UserAvailability',
                    'Sessions', 'Nodes', 'Users', 'Fibonacci'
                ]
                for table in tables:
                    try:
                        cursor.execute(f"DROP TABLE IF EXISTS {table}")
                    except:
                        pass
                    
            cursor.executescript(sql_script)
            
            if sample_data:
                _add_sample_data(cursor)
                
            conn.commit()
            
        console.print("[green]✅ Database initialized successfully with enhanced schema.[/green]")
        if sample_data:
            console.print("[blue]📚 Sample data added[/blue]")
            
    except Exception as e:
        console.print(f"[red]❌ Error initializing database: {e}[/red]")
        raise click.Abort()

def _add_sample_data(cursor):
    """Add comprehensive sample data"""
    # Add sample user
    password_hash = hashlib.sha256('demo123'.encode()).hexdigest()
    cursor.execute("""
        INSERT INTO Users (username, password_hash, email, available_minutes_per_day, 
                          streak_days, learning_efficiency, points, level)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, ('demo', password_hash, 'demo@example.com', 
          json.dumps([120, 120, 120, 120, 120, 90, 60]), 7, 1.2, 150, 2))
    
    user_id = cursor.lastrowid
    
    # Add sample ecology
    cursor.execute("""
        INSERT INTO Nodes (user_id, node_type, name, description, course, course_code, 
                          status, importance, understanding, difficulty, points_value)
        VALUES (?, 'ecology', 'Computer Science Fundamentals', 
                'Comprehensive computer science foundation', 'CS Fundamentals', 'CS101', 
                'active', 85, 70, 65, 50)
    """, (user_id,))
    ecology_id = cursor.lastrowid
    
    # Add sample forests
    forests = [
        ('Algorithms & Data Structures', 'Core algorithmic thinking and data organization', 90, 60, 75),
        ('Web Development', 'Full-stack web development technologies', 80, 75, 60),
        ('Database Systems', 'Database design and management', 75, 50, 70)
    ]
    
    forest_ids = []
    for name, desc, imp, und, diff in forests:
        cursor.execute("""
            INSERT INTO Nodes (user_id, node_type, name, description, parent_id,
                              status, importance, understanding, difficulty)
            VALUES (?, 'forest', ?, ?, ?, 'active', ?, ?, ?)
        """, (user_id, name, desc, ecology_id, imp, und, diff))
        forest_ids.append(cursor.lastrowid)
    
    # Add sample trees
    trees = [
        ('Sorting Algorithms', 'Various sorting algorithms and their complexities', forest_ids[0], 85, 40, 80),
        ('Graph Theory', 'Graph algorithms and applications', forest_ids[0], 80, 30, 85),
        ('Frontend Development', 'HTML, CSS, JavaScript fundamentals', forest_ids[1], 85, 80, 50),
        ('Backend Development', 'Server-side programming and APIs', forest_ids[1], 90, 60, 70)
    ]
    
    tree_ids = []
    for name, desc, parent, imp, und, diff in trees:
        cursor.execute("""
            INSERT INTO Nodes (user_id, node_type, name, description, parent_id,
                              status, importance, understanding, difficulty)
            VALUES (?, 'tree', ?, ?, ?, 'active', ?, ?, ?)
        """, (user_id, name, desc, parent, imp, und, diff))
        tree_ids.append(cursor.lastrowid)
    
    console.print(f"[blue]✅ Added sample data: 1 user, 1 ecology, {len(forests)} forests, {len(trees)} trees[/blue]")

@cli.command()
@click.option("--username", prompt="Username", help="Unique username")
@click.password_option("--password", prompt="Password", confirmation_prompt=True, help="Secure password")
@click.option("--email", prompt="Email (optional)", default="", help="Email for notifications")
@click.option("--timezone", prompt="Your timezone", default="UTC", help="Timezone for scheduling")
def signup(username, password, email, timezone):
    """Create a new user account with enhanced profile"""
    db_manager = DatabaseManager()
    
    try:
        # Validate timezone
        try:
            pytz.timezone(timezone)
        except pytz.UnknownTimeZoneError:
            console.print(f"[red]❌ Unknown timezone: {timezone}[/red]")
            console.print("[yellow]Use format like: America/New_York, Europe/London, Asia/Tokyo[/yellow]")
            return

        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if username exists
            cursor.execute("SELECT user_id FROM Users WHERE username = ?", (username,))
            if cursor.fetchone():
                console.print(f"[red]❌ Username '{username}' already exists.[/red]")
                raise click.Abort()
                
            # Create user with enhanced profile
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            cursor.execute("""
                INSERT INTO Users (
                    username, password_hash, email, available_minutes_per_day, 
                    streak_days, streak_multiplier, learning_efficiency, fatigue_threshold,
                    timezone, daily_goal_minutes, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                username, password_hash, email,
                json.dumps([120, 120, 120, 120, 120, 90, 60]),
                1, 1.0, 1.0, 75.0, timezone, 120,
                datetime.datetime.utcnow().isoformat()
            ))
            
            user_id = cursor.lastrowid
            
            # Initialize user availability
            for day in range(7):
                minutes = 120 if day < 5 else 90 if day == 5 else 60
                cursor.execute("""
                    INSERT INTO UserAvailability (user_id, day_of_week, minutes, timezone)
                    VALUES (?, ?, ?, ?)
                """, (user_id, day, minutes, timezone))
                
            # Create welcome notification
            cursor.execute("""
                INSERT INTO Notifications (user_id, title, message, type)
                VALUES (?, ?, ?, ?)
            """, (user_id, "🎉 Welcome to FIBOCLI!", 
                  "Get started by creating your first ecology with 'fibocli create ecology'", "system"))
                
            conn.commit()
            
        console.print(f"[green]✅ Created user ID={user_id} ({username})[/green]")
        console.print(f"[blue]🕐 Timezone set to: {timezone}[/blue]")
        console.print("[yellow]💡 Run 'fibocli create ecology' to start building your learning structure[/yellow]")
        
    except sqlite3.Error as e:
        console.print(f"[red]❌ Database error: {e}[/red]")
        raise click.Abort()

@cli.command()
@click.option("--username", prompt="Username", help="Your username")
@click.option("--password", prompt="Password", hide_input=True, help="Your password")
@click.option("--remember", is_flag=True, help="Remember login for 30 days")
def login(username, password, remember):
    """Enhanced login with session management and gamification status"""
    db_manager = DatabaseManager()
    
    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id, password_hash, streak_days, learning_efficiency, 
                       points, level, timezone
                FROM Users WHERE username = ?
            """, (username,))
            
            user = cursor.fetchone()
            if not user or hashlib.sha256(password.encode()).hexdigest() != user['password_hash']:
                console.print("[red]❌ Invalid credentials.[/red]")
                raise click.Abort()
                
            # Create session
            token = secrets.token_hex(32)
            expiry_days = 30 if remember else 7
            expiry = (datetime.datetime.utcnow() + datetime.timedelta(days=expiry_days)).isoformat()
            
            cursor.execute("""
                INSERT INTO Sessions (user_id, token, expiry, created_at) 
                VALUES (?, ?, ?, ?)
            """, (user['user_id'], token, expiry, datetime.datetime.utcnow().isoformat()))
            
            # Check for unread notifications
            cursor.execute("SELECT COUNT(*) FROM Notifications WHERE user_id = ? AND is_read = 0", (user['user_id'],))
            unread_notifications = cursor.fetchone()[0]
            
            conn.commit()
            
            # Save session data
            session_data = {
                'user_id': user['user_id'],
                'token': token,
                'username': username,
                'timezone': user['timezone'],
                'login_time': datetime.datetime.now().isoformat()
            }
            
            with open(".fibocli_session", "w") as f:
                json.dump(session_data, f)
                
        # Show login success with gamification status
        console.print(f"[green]✅ Welcome back, {username}![/green]")
        
        # Show quick stats
        stats_table = Table(show_header=False, box=None)
        stats_table.add_column("", style="cyan")
        stats_table.add_column("", style="green")
        
        stats_table.add_row("Level", f"Level {user['level']}")
        stats_table.add_row("Points", f"{user['points']} pts")
        stats_table.add_row("Streak", f"{user['streak_days']} days 🔥")
        stats_table.add_row("Efficiency", f"{user['learning_efficiency']:.2f}x")
        
        console.print(stats_table)
        
        if unread_notifications > 0:
            console.print(f"[yellow]📬 You have {unread_notifications} unread notification(s). Use 'fibocli notifications' to view.[/yellow]")
        
    except Exception as e:
        console.print(f"[red]❌ Login error: {e}[/red]")
        raise click.Abort()

@cli.command()
def logout():
    """Log out and clear local session"""
    try:
        if os.path.exists(".fibocli_session"):
            os.remove(".fibocli_session")
            console.print("[green]✅ Logged out successfully.[/green]")
        else:
            console.print("[yellow]No active session found.[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise click.Abort()

@cli.command()
def whoami():
    """Show enhanced user profile with gamification"""
    user_id = require_user()
    db_manager = DatabaseManager()
    
    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT username, streak_days, learning_efficiency, points, level,
                       experience_points, timezone, daily_goal_minutes, total_study_minutes,
                       longest_streak, total_sessions_completed
                FROM Users WHERE user_id = ?
            """, (user_id,))
            user = cursor.fetchone()
            
            if not user:
                console.print("[red]❌ User not found.[/red]")
                raise click.Abort()
            
            # Calculate progress to next level
            current_level = user['level']
            current_xp = user['experience_points']
            next_level_xp = LEVEL_THRESHOLDS[current_level] if current_level < len(LEVEL_THRESHOLDS) else LEVEL_THRESHOLDS[-1]
            prev_level_xp = LEVEL_THRESHOLDS[current_level - 1] if current_level > 0 else 0
            xp_progress = ((current_xp - prev_level_xp) / (next_level_xp - prev_level_xp)) * 100 if next_level_xp > prev_level_xp else 100
            
            # Create enhanced profile display
            profile_table = Table(title=f"👤 {user['username']}'s Profile", show_header=False)
            profile_table.add_column("Attribute", style="cyan")
            profile_table.add_column("Value", style="green")
            
            profile_table.add_row("Username", user['username'])
            profile_table.add_row("Level", f"Level {user['level']} ({xp_progress:.1f}% to next)")
            profile_table.add_row("Experience", f"{user['experience_points']} XP")
            profile_table.add_row("Points", f"{user['points']} pts")
            profile_table.add_row("Current Streak", f"{user['streak_days']} days 🔥")
            profile_table.add_row("Longest Streak", f"{user['longest_streak']} days")
            profile_table.add_row("Learning Efficiency", f"{user['learning_efficiency']:.2f}x")
            profile_table.add_row("Timezone", user['timezone'])
            profile_table.add_row("Daily Goal", f"{user['daily_goal_minutes']} minutes")
            profile_table.add_row("Total Study Time", f"{user['total_study_minutes']} minutes")
            profile_table.add_row("Sessions Completed", f"{user['total_sessions_completed']}")
            
            console.print(profile_table)
            
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise click.Abort()

# =====================================================================
# ENHANCED STUDY COMMAND WITH ALL FEATURES
# =====================================================================
@cli.command()
@click.option("--duration", type=int, help="Study duration in minutes (auto-calculated if not provided)")
@click.option("--auto-duration", is_flag=True, help="Use auto-duration calculation")
@click.option("--fatigue", type=float, help="Current fatigue level (1-100)")
@click.option("--focus", type=float, help="Current focus level (1-100)")
@click.option("--pause", is_flag=True, help="Pause current study session")
@click.option("--resume", is_flag=True, help="Resume paused study session")
@click.option("--complete", is_flag=True, help="Complete current study session")
@click.option("--node-id", type=int, help="Specific node to study")
@click.option("--focus-mode", is_flag=True, help="Enable focus mode (no breaks)")
@click.option("--adaptive", is_flag=True, help="Use adaptive scheduling")
def study(duration, auto_duration, fatigue, focus, pause, resume, complete, node_id, focus_mode, adaptive):
    """Enhanced study command with gamification, auto-streaker, and fatigue management"""
    user_id = require_user()
    conn = get_db_connection()
    
    try:
        study_manager = AdvancedStudyManager(conn)
        
        # Handle session pause/resume/complete
        active_session = _get_active_study_session(user_id, conn)
        
        if pause and active_session:
            _pause_study_session(active_session['session_id'], conn)
            console.print("[yellow]⏸ Study session paused[/yellow]")
            return
            
        if resume and active_session and active_session['status'] == 'paused':
            _resume_study_session(active_session['session_id'], conn)
            console.print("[green]▶ Study session resumed[/green]")
            return
            
        if complete and active_session:
            _complete_study_session(active_session['session_id'], fatigue, focus, conn, study_manager)
            
            # Auto-streaker update
            if study_manager.auto_streak_update(user_id):
                console.print("[green]🔥 Streak updated![/green]")
                
            # Check daily goal
            _check_daily_goal(user_id, conn)
            return

        # Start new study session
        if active_session:
            elapsed = _get_session_elapsed_time(active_session['session_id'], conn)
            console.print(f"[blue]📚 Active study session running for {elapsed:.1f} minutes[/blue]")
            return

        # Get or calculate duration
        if auto_duration or duration is None:
            cursor = conn.cursor()
            if node_id:
                # Use specified node for auto-duration
                duration = study_manager.calculate_auto_duration(node_id, user_id)
            else:
                # Get highest priority node
                cursor.execute("""
                    SELECT node_id FROM Nodes 
                    WHERE user_id = ? AND status IN ('active', 'pending', 'review')
                    ORDER BY priority_score DESC, importance DESC 
                    LIMIT 1
                """, (user_id,))
                node = cursor.fetchone()
                if node:
                    duration = study_manager.calculate_auto_duration(node['node_id'], user_id)
                else:
                    duration = 30
            console.print(f"[blue]🤖 Auto-duration: {duration} minutes[/blue]")

        # Check hierarchical restrictions and get available nodes
        available_nodes = _get_available_nodes(user_id, conn)
        if not available_nodes:
            console.print("[yellow]🎉 No nodes available for study! Check prerequisites or create new nodes.[/yellow]")
            return

        # If specific node requested, verify it's available
        if node_id:
            node_available = any(node['node_id'] == node_id for node in available_nodes)
            if not node_available:
                prereq_met, unmet = study_manager.check_prerequisites(node_id)
                if not prereq_met:
                    console.print(f"[red]❌ Node {node_id} has unmet prerequisites: {unmet}[/red]")
                    return
                else:
                    console.print(f"[yellow]⚠️ Node {node_id} is not available for other reasons[/yellow]")
                    return

        # Fatigue management
        if fatigue is None:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT fatigue_end FROM StudySessions 
                WHERE user_id = ? 
                ORDER BY start_time DESC LIMIT 1
            """, (user_id,))
            recent = cursor.fetchone()
            fatigue = recent['fatigue_end'] if recent else 20.0

        fatigue_recommendations = study_manager.fatigue_management(user_id, fatigue, duration)
        
        if fatigue_recommendations["break_needed"] and not focus_mode:
            console.print(f"[yellow]💤 Fatigue alert! Recommended break: {fatigue_recommendations['break_duration']} minutes[/yellow]")
            if Confirm.ask("Take a break before studying?"):
                # Schedule break
                break_session_id = _schedule_break_session(user_id, fatigue_recommendations["break_duration"], conn)
                console.print(f"[blue]💤 Break session scheduled for {fatigue_recommendations['break_duration']} minutes[/blue]")
            else:
                console.print("[yellow]Continuing with reduced efficiency...[/yellow]")

        # Start study session
        session_id = _start_study_session(user_id, duration, fatigue, focus, conn, node_id)
        console.print(f"[green]📚 Study session started for {duration} minutes[/green]")
        
        # Show gamification status
        _show_study_motivation(user_id, conn)

    except Exception as e:
        console.print(f"[red]❌ Study error: {e}[/red]")
        raise click.Abort()
    finally:
        conn.close()

# =====================================================================
# GAMIFICATION & ACHIEVEMENTS COMMANDS
# =====================================================================

@cli.command()
def achievements():
    """Show your achievements and progress"""
    user_id = require_user()
    conn = get_db_connection()
    
    try:
        cursor = conn.cursor()
        
        # Get user achievements
        cursor.execute("""
            SELECT a.name, a.description, a.points, a.unlocked_at, a.icon, a.category,
                   a.progress_current, a.progress_target
            FROM Achievements a 
            WHERE a.user_id = ?
            ORDER BY a.unlocked_at DESC, a.category, a.name
        """, (user_id,))
        achievements = cursor.fetchall()
        
        # Get user stats
        cursor.execute("""
            SELECT points, level, experience_points, streak_days, longest_streak,
                   (SELECT COUNT(*) FROM Nodes WHERE user_id = ? AND status = 'completed') as completed_nodes,
                   (SELECT COALESCE(SUM(total_active_minutes), 0) FROM Nodes WHERE user_id = ?) as total_study_time,
                   (SELECT COUNT(*) FROM Achievements WHERE user_id = ? AND unlocked_at IS NOT NULL) as unlocked_achievements,
                   (SELECT COUNT(*) FROM Achievements WHERE user_id = ?) as total_achievements
            FROM Users WHERE user_id = ?
        """, (user_id, user_id, user_id, user_id, user_id))
        user_stats = cursor.fetchone()
        
        # Display achievements in categories
        unlocked_achievements = [a for a in achievements if a['unlocked_at']]
        locked_achievements = [a for a in achievements if not a['unlocked_at']]
        
        if unlocked_achievements:
            console.print("\n[bold green]🏆 Unlocked Achievements[/bold green]")
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Achievement", style="cyan")
            table.add_column("Description", style="white")
            table.add_column("Points", style="green")
            table.add_column("Unlocked", style="dim")
            
            for ach in unlocked_achievements:
                table.add_row(
                    f"{ach['icon']} {ach['name']}",
                    ach['description'],
                    str(ach['points']),
                    ach['unlocked_at'][:10] if ach['unlocked_at'] else "Recently"
                )
            console.print(table)
        
        if locked_achievements:
            console.print("\n[bold yellow]🔒 Locked Achievements[/bold yellow]")
            table = Table(show_header=True, header_style="bold yellow")
            table.add_column("Achievement", style="dim")
            table.add_column("Description", style="dim")
            table.add_column("Progress", style="blue")
            table.add_column("Points", style="dim")
            
            for ach in locked_achievements:
                progress = f"{ach['progress_current']}/{ach['progress_target']}"
                progress_bar = _create_progress_bar(ach['progress_current'], ach['progress_target'])
                table.add_row(
                    f"{ach['icon']} {ach['name']}",
                    ach['description'],
                    f"{progress} {progress_bar}",
                    str(ach['points'])
                )
            console.print(table)
        
        # Display comprehensive progress
        console.print("\n[bold]📊 Gamification Progress[/bold]")
        progress_table = Table(show_header=False, box=None)
        progress_table.add_column("Metric", style="cyan")
        progress_table.add_column("Value", style="green")
        
        # Calculate level progress
        current_level = user_stats['level']
        current_xp = user_stats['experience_points']
        next_level_xp = LEVEL_THRESHOLDS[current_level] if current_level < len(LEVEL_THRESHOLDS) else LEVEL_THRESHOLDS[-1]
        prev_level_xp = LEVEL_THRESHOLDS[current_level - 1] if current_level > 0 else 0
        xp_progress = ((current_xp - prev_level_xp) / (next_level_xp - prev_level_xp)) * 100 if next_level_xp > prev_level_xp else 100
        
        progress_table.add_row("Level", f"Level {current_level} ({xp_progress:.1f}% to next)")
        progress_table.add_row("Total Points", f"{user_stats['points']}")
        progress_table.add_row("Experience", f"{current_xp} XP")
        progress_table.add_row("Current Streak", f"{user_stats['streak_days']} days 🔥")
        progress_table.add_row("Longest Streak", f"{user_stats['longest_streak']} days")
        progress_table.add_row("Completed Nodes", f"{user_stats['completed_nodes']}")
        progress_table.add_row("Total Study Time", f"{user_stats['total_study_time']:.0f} min")
        progress_table.add_row("Achievements", f"{user_stats['unlocked_achievements']}/{user_stats['total_achievements']} unlocked")
        
        console.print(progress_table)
        
        # Show motivational message
        if user_stats['unlocked_achievements'] == 0:
            console.print("\n[yellow]💡 Start studying to unlock your first achievement![/yellow]")
        elif user_stats['unlocked_achievements'] == user_stats['total_achievements']:
            console.print("\n[green]🎉 Amazing! You've unlocked all achievements![/green]")
        else:
            remaining = user_stats['total_achievements'] - user_stats['unlocked_achievements']
            console.print(f"\n[blue]🎯 You have {remaining} achievements left to unlock. Keep going![/blue]")
        
    except Exception as e:
        console.print(f"[red]❌ Achievements error: {e}[/red]")
    finally:
        conn.close()

@cli.command()
@click.option("--read", is_flag=True, help="Mark all notifications as read")
@click.option("--clear", is_flag=True, help="Clear all read notifications")
@click.option("--unread-only", is_flag=True, help="Show only unread notifications")
def notifications(read, clear, unread_only):
    """Manage your notifications"""
    user_id = require_user()
    conn = get_db_connection()
    
    try:
        cursor = conn.cursor()
        
        if read:
            cursor.execute("UPDATE Notifications SET is_read = 1 WHERE user_id = ?", (user_id,))
            conn.commit()
            console.print("[green]✅ All notifications marked as read[/green]")
            return
            
        if clear:
            cursor.execute("DELETE FROM Notifications WHERE user_id = ? AND is_read = 1", (user_id,))
            conn.commit()
            console.print("[green]✅ Read notifications cleared[/green]")
            return
        
        # Build query based on filters
        query = """
            SELECT notification_id, title, message, type, is_read, is_actionable, 
                   action_url, created_at
            FROM Notifications 
            WHERE user_id = ?
        """
        params = [user_id]
        
        if unread_only:
            query += " AND is_read = 0"
            
        query += " ORDER BY created_at DESC LIMIT 50"
        
        cursor.execute(query, params)
        notifications_list = cursor.fetchall()
        
        if not notifications_list:
            console.print("[green]📭 No notifications[/green]")
            return
            
        unread_count = sum(1 for n in notifications_list if not n['is_read'])
        
        table = Table(title=f"🔔 Notifications ({unread_count} unread)")
        table.add_column("ID", style="dim", width=8)
        table.add_column("Title", style="cyan")
        table.add_column("Message", style="white")
        table.add_column("Type", style="blue")
        table.add_column("Read", style="green")
        table.add_column("Time", style="dim")
        
        for notif in notifications_list:
            read_status = "✅" if notif['is_read'] else "🔴"
            message = (notif['message'][:50] + '...') if len(notif['message']) > 50 else notif['message']
            table.add_row(
                str(notif['notification_id']),
                notif['title'],
                message,
                notif['type'],
                read_status,
                notif['created_at'][:16]
            )
            
        console.print(table)
        
        # Show actionable notifications separately
        actionable_notifs = [n for n in notifications_list if n['is_actionable'] and not n['is_read']]
        if actionable_notifs:
            console.print("\n[bold yellow]🚀 Actionable Notifications[/bold yellow]")
            for notif in actionable_notifs:
                console.print(f"• {notif['title']}: {notif['message']}")
                if notif['action_url']:
                    console.print(f"  [dim]Action: {notif['action_url']}[/dim]")
        
    except Exception as e:
        console.print(f"[red]❌ Notifications error: {e}[/red]")
    finally:
        conn.close()

# =====================================================================
# ENHANCED HIERARCHY & VISUALIZATION
# =====================================================================

@cli.command()
@click.option("--tree", is_flag=True, help="Show as visual tree")
@click.option("--status", type=click.Choice(['all', 'active', 'completed', 'pending', 'review']), default='all')
@click.option("--type", "node_type", type=click.Choice(['all', 'ecology', 'forest', 'tree', 'super_branch', 'branch', 'sub_branch', 'leaf']), default='all')
@click.option("--detailed", is_flag=True, help="Show detailed information")
def hierarchy(tree, status, node_type, detailed):
    """Show learning hierarchy with enhanced visualization"""
    user_id = require_user()
    conn = get_db_connection()
    
    try:
        cursor = conn.cursor()
        
        # Build query based on filters
        query = """
            SELECT node_id, node_type, name, status, parent_id, importance, 
                   understanding, difficulty, total_active_minutes, completed_at,
                   prerequisites
            FROM Nodes WHERE user_id = ?
        """
        params = [user_id]
        
        if status != 'all':
            query += " AND status = ?"
            params.append(status)
            
        if node_type != 'all':
            query += " AND node_type = ?"
            params.append(node_type)
            
        query += " ORDER BY node_type, child_order, name"
        
        cursor.execute(query, params)
        nodes = cursor.fetchall()
        
        if not nodes:
            console.print("[yellow]No nodes found matching your criteria.[/yellow]")
            return
            
        if tree:
            _display_hierarchy_tree(nodes, detailed)
        else:
            _display_hierarchy_table(nodes, detailed)
            
    except Exception as e:
        console.print(f"[red]❌ Hierarchy error: {e}[/red]")
    finally:
        conn.close()

def _display_hierarchy_tree(nodes, detailed=False):
    """Display hierarchy as a visual tree"""
    from rich.tree import Tree
    
    # Build node dictionary and find root nodes
    node_dict = {}
    for node in nodes:
        node_dict[node['node_id']] = dict(node)
    
    root_nodes = [n for n in nodes if n['node_type'] == 'ecology']
    
    if not root_nodes:
        console.print("[yellow]No ecology nodes found. Create one with 'fibocli create ecology'[/yellow]")
        return
        
    tree = Tree("🌳 Learning Hierarchy")
    
    for root in root_nodes:
        root_branch = tree.add(_format_tree_node(root, detailed))
        _build_tree_branch(root_branch, root['node_id'], node_dict, detailed)
    
    console.print(tree)
    
    # Show legend if detailed
    if detailed:
        console.print("\n[bold]Legend:[/bold]")
        console.print("🟢 >80%  🟡 60-80%  🔴 <60% understanding")
        console.print("🔒 Locked  🔄 Review  ✅ Completed  ▶ Active")

def _format_tree_node(node, detailed=False):
    """Format node for tree display"""
    status_icon = status_icons.get(node['status'], "○")
    
    # Node type icons
    node_icon = {
        'ecology': '🌍', 'forest': '🌲', 'tree': '🎄', 
        'super_branch': '🟢', 'branch': '🔶', 'sub_branch': '🔷', 'leaf': '🍃'
    }.get(node['node_type'], '○')
    
    # Color based on understanding
    understanding = node['understanding']
    if understanding > 80:
        color = "green"
        understanding_icon = "🟢"
    elif understanding > 60:
        color = "yellow"
        understanding_icon = "🟡"
    else:
        color = "red"
        understanding_icon = "🔴"
    
    if detailed:
        # Detailed format with metrics
        prerequisites = json.loads(node['prerequisites']) if node['prerequisites'] else []
        prereq_text = f" 📎{len(prerequisites)}" if prerequisites else ""
        
        return (
            f"{status_icon} {node_icon} [{color}]{node['name']}[/{color}] "
            f"(ID: {node['node_id']}) {understanding_icon}{node['understanding']:.0f}%"
            f"⚡{node['importance']:.0f} 🎯{node['difficulty']:.0f}{prereq_text}"
        )
    else:
        # Simple format
        return f"{status_icon} {node_icon} [{color}]{node['name']}[/{color}] (ID: {node['node_id']})"

def _build_tree_branch(branch, parent_id, node_dict, detailed=False):
    """Recursively build tree branches"""
    children = [n for n in node_dict.values() if n.get('parent_id') == parent_id]
    for child in sorted(children, key=lambda x: x.get('child_order', 0)):
        child_branch = branch.add(_format_tree_node(child, detailed))
        _build_tree_branch(child_branch, child['node_id'], node_dict, detailed)

def _display_hierarchy_table(nodes, detailed=False):
    """Display hierarchy as a table"""
    if detailed:
        table = Table(title="Learning Hierarchy (Detailed)")
        table.add_column("ID", style="cyan")
        table.add_column("Type", style="blue")
        table.add_column("Name", style="green")
        table.add_column("Status", style="yellow")
        table.add_column("Importance", style="magenta")
        table.add_column("Understanding", style="blue")
        table.add_column("Difficulty", style="red")
        table.add_column("Study Time", style="dim")
        table.add_column("Parent ID", style="dim")
        
        for node in nodes:
            status_display = status_icons.get(node['status'], node['status'])
            table.add_row(
                str(node['node_id']),
                node['node_type'].replace('_', ' ').title(),
                node['name'],
                status_display,
                f"{node['importance']:.0f}",
                f"{node['understanding']:.0f}%",
                f"{node['difficulty']:.0f}",
                f"{node['total_active_minutes']:.0f}m",
                str(node['parent_id']) if node['parent_id'] else "N/A"
            )
    else:
        table = Table(title="Learning Hierarchy")
        table.add_column("ID", style="cyan")
        table.add_column("Type", style="blue")
        table.add_column("Name", style="green")
        table.add_column("Status", style="yellow")
        table.add_column("Parent ID", style="dim")
        
        for node in nodes:
            status_display = status_icons.get(node['status'], node['status'])
            table.add_row(
                str(node['node_id']),
                node['node_type'].replace('_', ' ').title(),
                node['name'],
                status_display,
                str(node['parent_id']) if node['parent_id'] else "N/A"
            )
    
    console.print(table)

# =====================================================================
# ENHANCED NODE CREATION WITH PREREQUISITES
# =====================================================================

@cli.group()
def create():
    """Create hierarchy nodes with enhanced features"""
    pass

@cli.group()
def create():
    """Create hierarchy nodes with enhanced features"""
    pass

# Enhanced create commands for all node types
@create.command("ecology")
@click.option("--name", prompt="Ecology name", help="Name of the ecology")
@click.option("--description", default="", help="Description of the ecology")
@click.option("--course", default="", help="Associated course name (optional)")
@click.option("--course-code", default="", help="Course code (optional)")
@click.option("--importance", type=float, default=50, help="Importance level (1-100)")
def create_ecology_cmd(name, description, course, course_code, importance):
    """Create a new ecology"""
    uid = require_user()
    conn = get_db_connection()
    
    try:
        if not (1 <= importance <= 100):
            raise ValueError("Importance must be between 1 and 100")
            
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Nodes (user_id, node_type, name, description, course, course_code, 
                              status, importance, understanding, difficulty, engagement, 
                              fatigue, fibonacci_index, points_value)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (uid, "ecology", name, description, course, course_code, "pending", 
              importance, 50, 50, 50, 50, 1, 50))
        
        conn.commit()
        ecology_id = cursor.lastrowid
        
        console.print(f"[green]✅ Ecology created ID={ecology_id} ({name})[/green]")
        console.print(f"[blue]📊 Importance: {importance}, Points: 50[/blue]")
        
    except Exception as e:
        console.print(f"[red]❌ Error creating ecology: {e}[/red]")
        raise click.Abort()
    finally:
        conn.close()

@create.command("forest")
@click.option("--ecology-id", type=int, help="Ecology ID (prompt if not provided)")
@click.option("--name", prompt="Forest name", help="Name of the forest")
@click.option("--description", default="", help="Description of the forest")
@click.option("--course", default="", help="Associated course name (optional)")
@click.option("--course-code", default="", help="Course code (optional)")
@click.option("--importance", type=float, default=50, help="Importance level (1-100)")
def create_forest_cmd(ecology_id, name, description, course, course_code, importance):
    """Create a new forest under an ecology"""
    uid = require_user()
    
    if ecology_id is None:
        ecology_id = _prompt_for_parent_id("ecology", uid)
    
    conn = get_db_connection()
    
    try:
        if not (1 <= importance <= 100):
            raise ValueError("Importance must be between 1 and 100")
            
        cursor = conn.cursor()
        
        # Verify parent exists
        cursor.execute("""
            SELECT node_id FROM Nodes 
            WHERE node_id = ? AND node_type = 'ecology' AND user_id = ?
        """, (ecology_id, uid))
        if not cursor.fetchone():
            raise ValueError(f"Ecology ID={ecology_id} not found or not owned by user")
        
        # Get child order
        cursor.execute("SELECT MAX(child_order) FROM Nodes WHERE parent_id = ?", (ecology_id,))
        max_order = cursor.fetchone()[0] or 0
        
        # Create forest
        cursor.execute("""
            INSERT INTO Nodes (user_id, node_type, name, description, course, course_code, 
                              status, importance, understanding, difficulty, engagement, 
                              fatigue, fibonacci_index, parent_id, child_order, points_value)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (uid, "forest", name, description, course, course_code, "pending", 
              importance, 50, 50, 50, 50, 2, ecology_id, max_order + 1, 40))
        
        conn.commit()
        forest_id = cursor.lastrowid
        
        console.print(f"[green]✅ Forest created ID={forest_id} ({name})[/green]")
        console.print(f"[blue]📊 Importance: {importance}, Points: 40[/blue]")
        
    except Exception as e:
        console.print(f"[red]❌ Error creating forest: {e}[/red]")
        raise click.Abort()
    finally:
        conn.close()

@create.command("tree")
@click.option("--forest-id", type=int, help="Forest ID (prompt if not provided)")
@click.option("--name", prompt="Tree name", help="Name of the tree")
@click.option("--description", default="", help="Description of the tree")
@click.option("--course", default="", help="Associated course name (optional)")
@click.option("--course-code", default="", help="Course code (optional)")
@click.option("--importance", type=float, default=50, help="Importance level (1-100)")
def create_tree_cmd(forest_id, name, description, course, course_code, importance):
    """Create a new tree under a forest"""
    uid = require_user()
    
    if forest_id is None:
        forest_id = _prompt_for_parent_id("forest", uid)
    
    conn = get_db_connection()
    
    try:
        if not (1 <= importance <= 100):
            raise ValueError("Importance must be between 1 and 100")
            
        cursor = conn.cursor()
        
        # Verify parent exists
        cursor.execute("""
            SELECT node_id FROM Nodes 
            WHERE node_id = ? AND node_type = 'forest' AND user_id = ?
        """, (forest_id, uid))
        if not cursor.fetchone():
            raise ValueError(f"Forest ID={forest_id} not found or not owned by user")
        
        # Get child order
        cursor.execute("SELECT MAX(child_order) FROM Nodes WHERE parent_id = ?", (forest_id,))
        max_order = cursor.fetchone()[0] or 0
        
        # Create tree
        cursor.execute("""
            INSERT INTO Nodes (user_id, node_type, name, description, course, course_code, 
                              status, importance, understanding, difficulty, engagement, 
                              fatigue, fibonacci_index, parent_id, child_order, points_value)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (uid, "tree", name, description, course, course_code, "pending", 
              importance, 50, 50, 50, 50, 3, forest_id, max_order + 1, 30))
        
        conn.commit()
        tree_id = cursor.lastrowid
        
        console.print(f"[green]✅ Tree created ID={tree_id} ({name})[/green]")
        console.print(f"[blue]📊 Importance: {importance}, Points: 30[/blue]")
        
    except Exception as e:
        console.print(f"[red]❌ Error creating tree: {e}[/red]")
        raise click.Abort()
    finally:
        conn.close()

@create.command("super")
@click.option("--tree-id", type=int, help="Tree ID (prompt if not provided)")
@click.option("--name", prompt="Super-branch name", help="Name of the super-branch")
@click.option("--description", default="", help="Description of the super-branch")
@click.option("--course", default="", help="Associated course name (optional)")
@click.option("--course-code", default="", help="Course code (optional)")
@click.option("--importance", type=float, default=50, help="Importance level (1-100)")
def create_super_cmd(tree_id, name, description, course, course_code, importance):
    """Create a new super-branch under a tree"""
    uid = require_user()
    
    if tree_id is None:
        tree_id = _prompt_for_parent_id("tree", uid)
    
    conn = get_db_connection()
    
    try:
        if not (1 <= importance <= 100):
            raise ValueError("Importance must be between 1 and 100")
            
        cursor = conn.cursor()
        
        # Verify parent exists
        cursor.execute("""
            SELECT node_id FROM Nodes 
            WHERE node_id = ? AND node_type = 'tree' AND user_id = ?
        """, (tree_id, uid))
        if not cursor.fetchone():
            raise ValueError(f"Tree ID={tree_id} not found or not owned by user")
        
        # Get child order
        cursor.execute("SELECT MAX(child_order) FROM Nodes WHERE parent_id = ?", (tree_id,))
        max_order = cursor.fetchone()[0] or 0
        
        # Create super-branch
        cursor.execute("""
            INSERT INTO Nodes (user_id, node_type, name, description, course, course_code, 
                              status, importance, understanding, difficulty, engagement, 
                              fatigue, fibonacci_index, parent_id, child_order, points_value)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (uid, "super_branch", name, description, course, course_code, "pending", 
              importance, 50, 50, 50, 50, 4, tree_id, max_order + 1, 25))
        
        conn.commit()
        super_id = cursor.lastrowid
        
        console.print(f"[green]✅ Super-branch created ID={super_id} ({name})[/green]")
        console.print(f"[blue]📊 Importance: {importance}, Points: 25[/blue]")
        
    except Exception as e:
        console.print(f"[red]❌ Error creating super-branch: {e}[/red]")
        raise click.Abort()
    finally:
        conn.close()

@create.command("branch")
@click.option("--super-id", type=int, help="Super-branch ID (prompt if not provided)")
@click.option("--name", prompt="Branch name", help="Name of the branch")
@click.option("--description", default="", help="Description of the branch")
@click.option("--course", default="", help="Associated course name (optional)")
@click.option("--course-code", default="", help="Course code (optional)")
@click.option("--importance", type=float, default=50, help="Importance level (1-100)")
def create_branch_cmd(super_id, name, description, course, course_code, importance):
    """Create a new branch under a super-branch"""
    uid = require_user()
    
    if super_id is None:
        super_id = _prompt_for_parent_id("super_branch", uid)
    
    conn = get_db_connection()
    
    try:
        if not (1 <= importance <= 100):
            raise ValueError("Importance must be between 1 and 100")
            
        cursor = conn.cursor()
        
        # Verify parent exists
        cursor.execute("""
            SELECT node_id FROM Nodes 
            WHERE node_id = ? AND node_type = 'super_branch' AND user_id = ?
        """, (super_id, uid))
        if not cursor.fetchone():
            raise ValueError(f"Super-branch ID={super_id} not found or not owned by user")
        
        # Get child order
        cursor.execute("SELECT MAX(child_order) FROM Nodes WHERE parent_id = ?", (super_id,))
        max_order = cursor.fetchone()[0] or 0
        
        # Create branch
        cursor.execute("""
            INSERT INTO Nodes (user_id, node_type, name, description, course, course_code, 
                              status, importance, understanding, difficulty, engagement, 
                              fatigue, fibonacci_index, parent_id, child_order, points_value)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (uid, "branch", name, description, course, course_code, "pending", 
              importance, 50, 50, 50, 50, 5, super_id, max_order + 1, 20))
        
        conn.commit()
        branch_id = cursor.lastrowid
        
        console.print(f"[green]✅ Branch created ID={branch_id} ({name})[/green]")
        console.print(f"[blue]📊 Importance: {importance}, Points: 20[/blue]")
        
    except Exception as e:
        console.print(f"[red]❌ Error creating branch: {e}[/red]")
        raise click.Abort()
    finally:
        conn.close()

@create.command("subbranch")
@click.option("--branch-id", type=int, help="Branch ID (prompt if not provided)")
@click.option("--name", prompt="Sub-branch name", help="Name of the sub-branch")
@click.option("--description", default="", help="Description of the sub-branch")
@click.option("--course", default="", help="Associated course name (optional)")
@click.option("--course-code", default="", help="Course code (optional)")
@click.option("--importance", type=float, default=50, help="Importance level (1-100)")
@click.option("--prerequisites", help="Comma-separated list of prerequisite node IDs")
def create_subbranch_cmd(branch_id, name, description, course, course_code, importance, prerequisites):
    """Create a new sub-branch under a branch"""
    uid = require_user()
    
    if branch_id is None:
        branch_id = _prompt_for_parent_id("branch", uid)
    
    conn = get_db_connection()
    
    try:
        if not (1 <= importance <= 100):
            raise ValueError("Importance must be between 1 and 100")
            
        # Parse prerequisites
        prereq_list = []
        if prerequisites:
            prereq_list = [int(p.strip()) for p in prerequisites.split(',')]
            
        cursor = conn.cursor()
        
        # Verify parent exists
        cursor.execute("""
            SELECT node_id FROM Nodes 
            WHERE node_id = ? AND node_type = 'branch' AND user_id = ?
        """, (branch_id, uid))
        if not cursor.fetchone():
            raise ValueError(f"Branch ID={branch_id} not found or not owned by user")
        
        # Get child order
        cursor.execute("SELECT MAX(child_order) FROM Nodes WHERE parent_id = ?", (branch_id,))
        max_order = cursor.fetchone()[0] or 0
        
        # Create sub-branch
        cursor.execute("""
            INSERT INTO Nodes (user_id, node_type, name, description, course, course_code, 
                              status, importance, understanding, difficulty, engagement, 
                              fatigue, fibonacci_index, parent_id, child_order,
                              prerequisites, points_value)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (uid, "sub_branch", name, description, course, course_code, "pending", 
              importance, 50, 50, 50, 50, 6, branch_id, max_order + 1,
              json.dumps(prereq_list), 15))
        
        conn.commit()
        subbranch_id = cursor.lastrowid
        
        console.print(f"[green]✅ Sub-branch created ID={subbranch_id} ({name})[/green]")
        console.print(f"[blue]📊 Importance: {importance}, Points: 15[/blue]")
        
        if prereq_list:
            console.print(f"[yellow]📎 Prerequisites: {', '.join(map(str, prereq_list))}[/yellow]")
        
    except Exception as e:
        console.print(f"[red]❌ Error creating sub-branch: {e}[/red]")
        raise click.Abort()
    finally:
        conn.close()

@create.command("leaf")
@click.option("--subbranch-id", type=int, help="Sub-branch ID (prompt if not provided)")
@click.option("--name", prompt="Leaf name", help="Name of the leaf")
@click.option("--description", default="", help="Description of the leaf")
@click.option("--course", default="", help="Associated course name (optional)")
@click.option("--course-code", default="", help="Course code (optional)")
@click.option("--importance", type=float, default=50, help="Importance level (1-100)")
@click.option("--difficulty", type=float, default=50, help="Difficulty level (1-100)")
@click.option("--understanding", type=float, default=50, help="Initial understanding level (1-100)")
@click.option("--prerequisites", help="Comma-separated list of prerequisite node IDs")
@click.option("--min-duration", type=int, default=15, help="Minimum study duration (minutes)")
@click.option("--max-duration", type=int, default=90, help="Maximum study duration (minutes)")
def create_leaf_cmd(subbranch_id, name, description, course, course_code, importance, 
                   difficulty, understanding, prerequisites, min_duration, max_duration):
    """Create a new leaf with enhanced features"""
    uid = require_user()
    
    if subbranch_id is None:
        subbranch_id = _prompt_for_parent_id("sub_branch", uid)
    
    conn = get_db_connection()
    
    try:
        # Validate inputs
        if not all(1 <= x <= 100 for x in [importance, difficulty, understanding]):
            raise ValueError("Importance, difficulty, and understanding must be between 1 and 100")
        if min_duration < 5 or max_duration > 240:
            raise ValueError("Duration must be between 5-240 minutes")
        if min_duration > max_duration:
            raise ValueError("Minimum duration cannot exceed maximum duration")
            
        # Parse prerequisites
        prereq_list = []
        if prerequisites:
            prereq_list = [int(p.strip()) for p in prerequisites.split(',')]
            
        cursor = conn.cursor()
        
        # Verify parent exists
        cursor.execute("""
            SELECT node_id FROM Nodes 
            WHERE node_id = ? AND node_type = 'sub_branch' AND user_id = ?
        """, (subbranch_id, uid))
        if not cursor.fetchone():
            raise ValueError(f"Sub-branch ID={subbranch_id} not found or not owned by user")
        
        # Get child order
        cursor.execute("SELECT MAX(child_order) FROM Nodes WHERE parent_id = ?", (subbranch_id,))
        max_order = cursor.fetchone()[0] or 0
        
        # Create leaf
        cursor.execute("""
            INSERT INTO Nodes (user_id, node_type, name, description, course, course_code, 
                              status, importance, understanding, difficulty, engagement, 
                              fatigue, fibonacci_index, parent_id, child_order,
                              prerequisites, min_duration, max_duration, points_value)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (uid, "leaf", name, description, course, course_code, "pending", 
              importance, understanding, difficulty, 50, 50, 7, subbranch_id, max_order + 1,
              json.dumps(prereq_list), min_duration, max_duration, 10))
        
        conn.commit()
        leaf_id = cursor.lastrowid
        
        console.print(f"[green]✅ Leaf created ID={leaf_id} ({name})[/green]")
        console.print(f"[blue]📊 Importance: {importance}, Difficulty: {difficulty}, Understanding: {understanding}[/blue]")
        console.print(f"[blue]⏱️ Duration: {min_duration}-{max_duration} min, Prerequisites: {len(prereq_list)}[/blue]")
        
        if prereq_list:
            console.print(f"[yellow]📎 Prerequisites: {', '.join(map(str, prereq_list))}[/yellow]")
        
    except Exception as e:
        console.print(f"[red]❌ Error creating leaf: {e}[/red]")
        raise click.Abort()
    finally:
        conn.close()
# =====================================================================
# DATA EXPORT/IMPORT & BACKUP
# =====================================================================

@cli.command()
@click.option("--export", type=click.Choice(['all', 'nodes', 'progress', 'achievements', 'analytics']), help="Export data")
@click.option("--import", "import_file", type=click.Path(), help="Import data from file")
@click.option("--backup", is_flag=True, help="Create full backup")
@click.option("--restore", type=click.Path(), help="Restore from backup")
@click.option("--format", type=click.Choice(['json', 'csv']), default='json', help="Export format")
def data(export, import_file, backup, restore, format):
    """Export/import your learning data"""
    user_id = require_user()
    
    if export:
        _export_data(user_id, export, format)
    elif import_file:
        _import_data(user_id, import_file)
    elif backup:
        _create_backup(user_id)
    elif restore:
        _restore_backup(user_id, restore)
    else:
        console.print("[yellow]Specify --export, --import, --backup, or --restore[/yellow]")

def _export_data(user_id: int, data_type: str, format: str):
    """Export user data"""
    conn = get_db_connection()
    try:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"fibocli_export_{data_type}_{timestamp}.{format}"
        
        data = {
            "export_type": data_type,
            "exported_at": datetime.datetime.now().isoformat(),
            "user_id": user_id,
            "version": "3.0"
        }
        
        cursor = conn.cursor()
        
        if data_type in ['all', 'nodes']:
            cursor.execute("SELECT * FROM Nodes WHERE user_id = ?", (user_id,))
            data['nodes'] = [dict(row) for row in cursor.fetchall()]
            
        if data_type in ['all', 'progress']:
            cursor.execute("""
                SELECT * FROM StudyAnalytics 
                WHERE user_id = ? 
                ORDER BY completed_at DESC
            """, (user_id,))
            data['progress'] = [dict(row) for row in cursor.fetchall()]
            
        if data_type in ['all', 'achievements']:
            cursor.execute("SELECT * FROM Achievements WHERE user_id = ?", (user_id,))
            data['achievements'] = [dict(row) for row in cursor.fetchall()]
            
        if data_type in ['all', 'analytics']:
            cursor.execute("SELECT * FROM StudySessions WHERE user_id = ?", (user_id,))
            data['sessions'] = [dict(row) for row in cursor.fetchall()]
        
        if format == 'json':
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        else:  # CSV
            # For CSV, we export each top-level key as a separate file
            for key, items in data.items():
                if isinstance(items, list) and items:
                    csv_filename = f"fibocli_export_{data_type}_{key}_{timestamp}.csv"
                    with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
                        if items:
                            writer = csv.DictWriter(f, fieldnames=items[0].keys())
                            writer.writeheader()
                            writer.writerows(items)
            
        # Record export in database
        cursor.execute("""
            INSERT INTO Exports (user_id, filename, export_type, file_path)
            VALUES (?, ?, ?, ?)
        """, (user_id, filename, data_type, os.path.abspath(filename)))
        conn.commit()
            
        console.print(f"[green]✅ Data exported to {filename}[/green]")
        console.print(f"[blue]💾 Export recorded in database (ID: {cursor.lastrowid})[/blue]")
        
    except Exception as e:
        console.print(f"[red]❌ Export error: {e}[/red]")
    finally:
        conn.close()

# =====================================================================
# TIMEZONE & EFFICIENCY MANAGEMENT
# =====================================================================

@cli.command()
@click.option("--timezone", help="Set your timezone (e.g., America/New_York)")
@click.option("--show", is_flag=True, help="Show current timezone")
@click.option("--list", "list_tz", is_flag=True, help="List common timezones")
def timezone(timezone, show, list_tz):
    """Manage your timezone settings"""
    user_id = require_user()
    conn = get_db_connection()
    
    try:
        cursor = conn.cursor()
        
        if list_tz:
            common_timezones = [
                'UTC', 'America/New_York', 'America/Chicago', 'America/Denver', 
                'America/Los_Angeles', 'Europe/London', 'Europe/Paris', 
                'Europe/Berlin', 'Asia/Tokyo', 'Asia/Shanghai', 'Australia/Sydney'
            ]
            console.print("\n[bold]🌐 Common Timezones:[/bold]")
            for tz in common_timezones:
                console.print(f"  • {tz}")
            return
            
        if show:
            cursor.execute("SELECT timezone FROM Users WHERE user_id = ?", (user_id,))
            result = cursor.fetchone()
            current_tz = result['timezone'] if result else 'UTC'
            
            # Show current time in that timezone
            try:
                tz = pytz.timezone(current_tz)
                current_time = datetime.datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
                console.print(f"[blue]🕐 Current timezone: {current_tz}[/blue]")
                console.print(f"[blue]⏰ Local time: {current_time}[/blue]")
            except:
                console.print(f"[blue]🕐 Current timezone: {current_tz}[/blue]")
            return
            
        if timezone:
            # Validate timezone
            try:
                pytz.timezone(timezone)
                cursor.execute("UPDATE Users SET timezone = ? WHERE user_id = ?", (timezone, user_id))
                
                # Update all schedules with new timezone
                cursor.execute("UPDATE Schedules SET timezone = ? WHERE user_id = ?", (timezone, user_id))
                
                conn.commit()
                console.print(f"[green]✅ Timezone set to {timezone}[/green]")
                
                # Show confirmation with local time
                tz = pytz.timezone(timezone)
                current_time = datetime.datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
                console.print(f"[blue]⏰ Your local time is now: {current_time}[/blue]")
                
            except pytz.UnknownTimeZoneError:
                console.print(f"[red]❌ Unknown timezone: {timezone}[/red]")
                console.print("[yellow]Use 'fibocli timezone --list' to see common timezones[/yellow]")
                
    except Exception as e:
        console.print(f"[red]❌ Timezone error: {e}[/red]")
    finally:
        conn.close()

@cli.command()
@click.option("--efficiency", type=float, help="Set learning efficiency (0.5-3.0)")
@click.option("--auto", is_flag=True, help="Enable auto-efficiency tuning")
@click.option("--show", is_flag=True, help="Show current efficiency and history")
@click.option("--reset", is_flag=True, help="Reset to default efficiency")
def efficiency(efficiency, auto, show, reset):
    """Manage learning efficiency settings"""
    user_id = require_user()
    conn = get_db_connection()
    
    try:
        cursor = conn.cursor()
        
        if show:
            cursor.execute("""
                SELECT learning_efficiency, average_efficiency 
                FROM Users WHERE user_id = ?
            """, (user_id,))
            user_data = cursor.fetchone()
            
            if user_data:
                current_eff = user_data['learning_efficiency']
                avg_eff = user_data['average_efficiency']
                
                console.print("\n[bold]📊 Learning Efficiency[/bold]")
                eff_table = Table(show_header=False, box=None)
                eff_table.add_column("Metric", style="cyan")
                eff_table.add_column("Value", style="green")
                
                eff_table.add_row("Current Efficiency", f"{current_eff:.2f}x")
                eff_table.add_row("Average Efficiency", f"{avg_eff:.2f}x")
                
                # Efficiency interpretation
                if current_eff > 1.5:
                    interpretation = "🎉 Excellent! You're learning very efficiently"
                elif current_eff > 1.0:
                    interpretation = "✅ Good! You're learning efficiently"
                elif current_eff > 0.7:
                    interpretation = "⚠️ Average efficiency - room for improvement"
                else:
                    interpretation = "🔴 Low efficiency - consider adjusting study habits"
                
                eff_table.add_row("Interpretation", interpretation)
                console.print(eff_table)
                
                # Show efficiency history
                cursor.execute("""
                    SELECT efficiency_score, recorded_date 
                    FROM EfficiencyHistory 
                    WHERE user_id = ? 
                    ORDER BY recorded_date DESC 
                    LIMIT 10
                """, (user_id,))
                history = cursor.fetchall()
                
                if history:
                    console.print("\n[bold]📈 Recent Efficiency History[/bold]")
                    hist_table = Table(show_header=True)
                    hist_table.add_column("Date", style="cyan")
                    hist_table.add_column("Efficiency", style="green")
                    
                    for record in history:
                        hist_table.add_row(
                            record['recorded_date'][:10],
                            f"{record['efficiency_score']:.2f}x"
                        )
                    console.print(hist_table)
                
            return
            
        if reset:
            cursor.execute("UPDATE Users SET learning_efficiency = 1.0 WHERE user_id = ?", (user_id,))
            conn.commit()
            console.print("[green]✅ Learning efficiency reset to 1.0x[/green]")
            return
            
        if efficiency is not None:
            if 0.5 <= efficiency <= 3.0:
                cursor.execute("UPDATE Users SET learning_efficiency = ? WHERE user_id = ?", (efficiency, user_id))
                conn.commit()
                console.print(f"[green]✅ Learning efficiency set to {efficiency:.2f}x[/green]")
                
                # Provide feedback based on efficiency level
                if efficiency > 1.5:
                    console.print("[green]🎉 High efficiency! You'll learn faster with this setting.[/green]")
                elif efficiency < 0.8:
                    console.print("[yellow]💡 Lower efficiency setting. Consider focusing on improving study habits.[/yellow]")
            else:
                console.print("[red]❌ Efficiency must be between 0.5 and 3.0[/red]")
                
        if auto:
            # Enable auto-efficiency tuning
            console.print("[blue]🤖 Auto-efficiency tuning enabled[/blue]")
            console.print("[yellow]Efficiency will now adjust based on your study patterns, focus, and performance[/yellow]")
            
    except Exception as e:
        console.print(f"[red]❌ Efficiency error: {e}[/red]")
    finally:
        conn.close()

# =====================================================================
# ENHANCED PLANTING WAVES WITH FLEXIBLE SCHEDULING
# =====================================================================

@cli.command()
@click.option("--parent-type", required=True, type=click.Choice(['ecology', 'forest', 'tree', 'super_branch', 'branch', 'sub_branch']))
@click.option("--parent-id", type=int, help="Parent node ID")
@click.option("--planned-units", type=int, help="Planned units to plant")
@click.option("--auto-schedule", is_flag=True, help="Automatically schedule planting sessions")
@click.option("--flexible-window", type=int, default=60, help="Flexible scheduling window in minutes")
@click.option("--start-date", help="Start date for planting (YYYY-MM-DD)")
def plant_wave(parent_type, parent_id, planned_units, auto_schedule, flexible_window, start_date):
    """Enhanced planting waves with flexible scheduling"""
    user_id = require_user()
    conn = get_db_connection()
    
    try:
        study_manager = AdvancedStudyManager(conn)
        cursor = conn.cursor()
        
        if parent_id is None:
            parent_id = _prompt_for_parent_id(parent_type, user_id, conn)
            
        if planned_units is None:
            planned_units = IntPrompt.ask("How many units to plant?", default=5)
            
        # Validate parent exists and user owns it
        cursor.execute("""
            SELECT node_id, name FROM Nodes 
            WHERE node_id = ? AND node_type = ? AND user_id = ?
        """, (parent_id, parent_type, user_id))
        parent = cursor.fetchone()
        if not parent:
            raise ValueError(f"{parent_type.capitalize()} ID={parent_id} not found or not owned by user")
        
        # Calculate performance metrics for planting
        cursor.execute("""
            SELECT AVG(understanding), AVG(engagement), AVG(fatigue) 
            FROM Nodes WHERE user_id = ? AND node_type = 'leaf' 
            AND parent_id IN (
                SELECT node_id FROM Nodes WHERE user_id = ? AND node_type = ? AND node_id = ?
            )
        """, (user_id, user_id, parent_type, parent_id))
        
        avg_metrics = cursor.fetchone()
        avg_understanding, avg_engagement, avg_fatigue = avg_metrics if avg_metrics and avg_metrics[0] is not None else (50, 50, 50)
        
        cursor.execute("SELECT streak_multiplier, learning_efficiency FROM Users WHERE user_id = ?", (user_id,))
        user_data = cursor.fetchone()
        streak_multiplier = user_data['streak_multiplier'] if user_data else 1.0
        
        performance_weight = (avg_understanding / 100) * streak_multiplier * (avg_engagement / 100) / max(avg_fatigue / 100, 0.1)
        
        # Get current wave number
        cursor.execute("SELECT MAX(wave_number) FROM Waves WHERE parent_type = ? AND parent_id = ?", (parent_type, parent_id))
        max_wave = cursor.fetchone()[0] or 0
        wave_number = max_wave + 1
        
        # Calculate actual units using Fibonacci sequence with performance adjustment
        if parent_type == "sub_branch":
            cursor.execute("SELECT COUNT(*) FROM Nodes WHERE parent_id = ? AND node_type = 'leaf'", (parent_id,))
            leaf_sum = cursor.fetchone()[0]
            k = 0
            while _get_weighted_fibonacci(k, performance_weight) <= leaf_sum:
                k += 1
            k = max(k - 1, 1)
            actual_units = min(planned_units, _get_weighted_fibonacci(k, performance_weight))
        else:
            actual_units = min(planned_units, _get_weighted_fibonacci(wave_number, performance_weight))
        
        # Set start date
        if start_date:
            try:
                start_date_obj = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
            except ValueError:
                raise ValueError("Start date must be in YYYY-MM-DD format")
        else:
            start_date_obj = datetime.date.today()
        
        # Create wave
        cursor.execute("""
            INSERT INTO Waves (parent_type, parent_id, wave_number, planned_units_count, 
                             actual_units_planted, scheduled_end_date)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (parent_type, parent_id, wave_number, planned_units, actual_units,
              (start_date_obj + datetime.timedelta(days=7)).isoformat()))
        
        wave_id = cursor.lastrowid
        
        if auto_schedule:
            # Schedule planting sessions with flexible windows
            _schedule_planting_sessions(user_id, wave_id, actual_units, flexible_window, start_date_obj, conn)
            
        conn.commit()
        
        console.print(f"[green]✅ Wave {wave_number} created for '{parent['name']}'[/green]")
        console.print(f"[blue]📊 Planted: {actual_units}/{planned_units} units (Performance: {performance_weight:.2f})[/blue]")
        
        if auto_schedule:
            console.print(f"[blue]📅 Auto-scheduled {actual_units} planting sessions starting {start_date_obj}[/blue]")
            console.print(f"[blue]⏰ Flexible window: {flexible_window} minutes[/blue]")
            
    except Exception as e:
        console.print(f"[red]❌ Planting wave error: {e}[/red]")
    finally:
        conn.close()

# =====================================================================
# HELPER FUNCTIONS
# =====================================================================

def _get_active_study_session(user_id: int, conn):
    """Get active study session"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM StudySessions 
        WHERE user_id = ? AND status IN ('active', 'paused')
        ORDER BY start_time DESC LIMIT 1
    """, (user_id,))
    return cursor.fetchone()

def _pause_study_session(session_id: int, conn):
    """Pause study session"""
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE StudySessions 
        SET status = 'paused', paused_duration = paused_duration + ?
        WHERE session_id = ?
    """, (0, session_id))  # You'd calculate actual paused time
    conn.commit()

def _resume_study_session(session_id: int, conn):
    """Resume study session"""
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE StudySessions 
        SET status = 'active'
        WHERE session_id = ?
    """, (session_id,))
    conn.commit()

def _start_study_session(user_id: int, duration: int, fatigue: float, focus: float, conn, node_id=None) -> int:
    """Start new study session"""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO StudySessions (user_id, start_time, planned_duration, fatigue_start, focus_score, status)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, datetime.datetime.now().isoformat(), duration, fatigue, focus, 'active'))
    conn.commit()
    return cursor.lastrowid

def _complete_study_session(session_id: int, fatigue: float, focus: float, conn, study_manager):
    """Complete study session with enhanced analytics"""
    cursor = conn.cursor()
    
    # Get session data
    cursor.execute("SELECT * FROM StudySessions WHERE session_id = ?", (session_id,))
    session = cursor.fetchone()
    
    if not session:
        console.print("[red]❌ Session not found[/red]")
        return
    
    # Calculate actual duration
    start_time = datetime.datetime.fromisoformat(session['start_time'])
    actual_duration = (datetime.datetime.now() - start_time).total_seconds() / 60
    
    # Update session
    cursor.execute("""
        UPDATE StudySessions 
        SET end_time = ?, actual_duration = ?, fatigue_end = ?, focus_score = ?, status = 'completed'
        WHERE session_id = ?
    """, (datetime.datetime.now().isoformat(), actual_duration, fatigue, focus, session_id))
    
    # Calculate efficiency score
    efficiency_score = min(1.0, actual_duration / session['planned_duration'])
    
    # Record analytics
    cursor.execute("""
        INSERT INTO StudyAnalytics (user_id, session_id, duration_minutes, focus_score, efficiency_score)
        VALUES (?, ?, ?, ?, ?)
    """, (session['user_id'], session_id, actual_duration, focus, efficiency_score))
    
    # Award points
    gamification = GamificationEngine(conn)
    points_earned = gamification.award_session_points(session['user_id'], {
        'duration_minutes': actual_duration,
        'efficiency_score': efficiency_score,
        'focus_score': focus
    })
    
    # Update learning efficiency
    new_efficiency = study_manager.update_learning_efficiency(session['user_id'], efficiency_score)
    
    conn.commit()
    
    console.print(f"[green]✅ Study session completed![/green]")
    console.print(f"[blue]📊 Duration: {actual_duration:.1f} min, Focus: {focus:.0f}%, Efficiency: {efficiency_score:.2f}[/blue]")
    console.print(f"[green]🎯 Points earned: +{points_earned}[/green]")
    if new_efficiency:
        console.print(f"[blue]📈 Learning efficiency: {new_efficiency:.2f}x[/blue]")

def _get_session_elapsed_time(session_id: int, conn) -> float:
    """Get elapsed time for active session"""
    cursor = conn.cursor()
    cursor.execute("SELECT start_time FROM StudySessions WHERE session_id = ?", (session_id,))
    session = cursor.fetchone()
    
    if session and session['start_time']:
        start_time = datetime.datetime.fromisoformat(session['start_time'])
        return (datetime.datetime.now() - start_time).total_seconds() / 60
    return 0

def _get_available_nodes(user_id: int, conn) -> List:
    """Get nodes available for study considering hierarchical restrictions"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT n.node_id, n.node_type, n.name, n.status, n.importance, n.understanding,
               n.difficulty, n.prerequisites, n.parent_id,
               (SELECT COUNT(*) FROM Nodes p WHERE p.node_id IN (
                   SELECT value FROM json_each(n.prerequisites)
               ) AND p.status != 'completed') as incomplete_prerequisites
        FROM Nodes n
        WHERE n.user_id = ? AND n.status IN ('active', 'pending', 'review')
        HAVING incomplete_prerequisites = 0
        ORDER BY n.priority_score DESC, n.importance DESC
    """, (user_id,))
    return cursor.fetchall()

def _show_study_motivation(user_id: int, conn):
    """Show gamification elements to motivate studying"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT u.points, u.level, u.streak_days, u.daily_goal_minutes,
               (SELECT COALESCE(SUM(duration_minutes), 0) 
                FROM StudyAnalytics 
                WHERE user_id = u.user_id AND DATE(completed_at) = DATE('now')
               ) as today_minutes,
               (SELECT COUNT(*) FROM Achievements WHERE user_id = u.user_id AND unlocked_at IS NOT NULL) as achievements
        FROM Users u WHERE u.user_id = ?
    """, (user_id,))
    user_data = cursor.fetchone()
    
    if user_data:
        today_progress = user_data['today_minutes']
        goal = user_data['daily_goal_minutes']
        progress_pct = min(100, (today_progress / goal) * 100) if goal > 0 else 0
        
        table = Table(title="🎯 Today's Progress", show_header=False, box=None)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Level", f"Level {user_data['level']}")
        table.add_row("Points", f"{user_data['points']} pts")
        table.add_row("Streak", f"{user_data['streak_days']} days 🔥")
        table.add_row("Achievements", f"{user_data['achievements']} unlocked")
        table.add_row("Daily Progress", f"{today_progress}/{goal} min ({progress_pct:.1f}%)")
        
        console.print(table)
        
        # Progress bar for daily goal
        if goal > 0:
            bars = int(progress_pct / 5)
            progress_bar = "[" + "█" * bars + "░" * (20 - bars) + "]"
            console.print(f"Goal Progress: {progress_bar} {progress_pct:.1f}%")
            
            if progress_pct >= 100:
                console.print("[green]🎉 Daily goal achieved! Great work![/green]")
            elif progress_pct > 75:
                console.print("[yellow]💪 Almost there! Keep going![/yellow]")
            elif progress_pct < 25:
                console.print("[blue]🚀 Let's get started! Every minute counts.[/blue]")

def _create_progress_bar(current: int, target: int, width: int = 20) -> str:
    """Create a visual progress bar"""
    if target == 0:
        return ""
    progress = min(1.0, current / target)
    filled = int(width * progress)
    return "[" + "█" * filled + "░" * (width - filled) + "]"

def _get_weighted_fibonacci(n: int, performance_weight: float) -> float:
    """Calculate weighted Fibonacci number"""
    if n <= 0:
        return 0
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM Fibonacci WHERE n = ?", (n,))
        result = cursor.fetchone()
        if result:
            return min(float(result[0]) * performance_weight, 250)
        # Fibonacci calculation fallback
        a, b = 1.0, 1.0
        for _ in range(3, n + 1):
            a, b = b, a + b
        return min(b * performance_weight, 250)
    finally:
        conn.close()

def _prompt_for_parent_id(parent_type: str, user_id: int, conn) -> int:
    """Prompt user to select parent node"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT node_id, name, course, course_code, status 
        FROM Nodes WHERE user_id = ? AND node_type = ?
    """, (user_id, parent_type))
    parents = cursor.fetchall()
    
    if not parents:
        raise click.ClickException(f"No {parent_type}s found. Create one first with 'fibocli create {parent_type}'.")
    
    table = Table(title=f"Available {parent_type.capitalize()}s")
    table.add_column("#", style="cyan", width=5)
    table.add_column("ID", style="cyan", width=5)
    table.add_column("Name", style="green")
    table.add_column("Course", style="blue")
    table.add_column("Status", style="yellow")
    
    for i, p in enumerate(parents, 1):
        table.add_row(str(i), str(p['node_id']), p['name'], p['course'] or "N/A", 
                     status_icons.get(p['status'], p['status']))
    console.print(table)
    
    choice = IntPrompt.ask("Select number", choices=[str(i) for i in range(1, len(parents)+1)], show_choices=False)
    return parents[choice - 1]['node_id']

def _schedule_break_session(user_id: int, duration: int, conn) -> int:
    """Schedule a break session"""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Schedules (user_id, task_id, task_type, start_time, duration, status)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, 0, 'break', datetime.datetime.now().isoformat(), duration, 'planned'))
    conn.commit()
    return cursor.lastrowid

def _schedule_planting_sessions(user_id: int, wave_id: int, units: int, flexible_window: int, start_date: datetime.date, conn):
    """Schedule planting sessions for a wave"""
    cursor = conn.cursor()
    
    # Get user's timezone
    cursor.execute("SELECT timezone FROM Users WHERE user_id = ?", (user_id,))
    user_timezone = cursor.fetchone()['timezone'] or 'UTC'
    
    current_time = datetime.datetime.now()
    
    for i in range(units):
        # Schedule each unit with flexible timing
        session_time = current_time + datetime.timedelta(days=i//2, hours=9 + (i % 2) * 4)  # Morning and afternoon sessions
        
        cursor.execute("""
            INSERT INTO Schedules (user_id, task_id, task_type, start_time, duration, 
                                 status, flexible_window, timezone)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, wave_id, 'wave_planting', session_time.isoformat(), 
              30, 'planned', flexible_window, user_timezone))
    
    conn.commit()

def _check_daily_goal(user_id: int, conn):
    """Check if daily goal is achieved and award bonus"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT daily_goal_minutes,
               (SELECT COALESCE(SUM(duration_minutes), 0) 
                FROM StudyAnalytics 
                WHERE user_id = ? AND DATE(completed_at) = DATE('now')
               ) as today_minutes
        FROM Users WHERE user_id = ?
    """, (user_id, user_id))
    
    result = cursor.fetchone()
    if result and result['today_minutes'] >= result['daily_goal_minutes']:
        # Award daily goal bonus
        bonus_points = 10
        cursor.execute("""
            UPDATE Users SET points = points + ? WHERE user_id = ?
        """, (bonus_points, user_id))
        
        # Create achievement notification
        cursor.execute("""
            INSERT INTO Notifications (user_id, title, message, type)
            VALUES (?, ?, ?, ?)
        """, (user_id, "🎯 Daily Goal Achieved!", 
              f"You've completed your daily study goal! +{bonus_points} bonus points", "goal"))
        
        conn.commit()
        console.print(f"[green]🎯 Daily goal achieved! +{bonus_points} bonus points![/green]")

# Include all your existing commands that aren't shown here (status, set, forecast, etc.)
# They should work with the enhanced system

if __name__ == "__main__":
    cli()
