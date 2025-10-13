# TERMINAL SESSION START

# 1. Initialize the database
fibocli init

# OUTPUT:
# ✅ Database initialized successfully with enhanced schema.

# 2. Create a new user account
fibocli signup

# PROMPTS & OUTPUT:
Username: john_developer
Password: **********
Confirm Password: **********
Email (optional): john@example.com
Your timezone: America/New_York

# OUTPUT:
# ✅ Created user ID=1 (john_developer)
# 🕐 Timezone set to: America/New_York
# 💡 Run 'fibocli create ecology' to start building your learning structure

# 3. Login to the system
fibocli login --username john_developer --password **********

# OUTPUT:
# ✅ Welcome back, john_developer!
# 
# Level    Level 1
# Points   0 pts  
# Streak   1 days 🔥
# Efficiency 1.00x

# 4. Check user profile
fibocli whoami

# OUTPUT:
# 👤 john_developer's Profile
# Attribute           Value
# Username           john_developer
# Level              Level 1 (0.0% to next)
# Experience         0 XP
# Points             0 pts
# Current Streak     1 days 🔥
# Longest Streak     1 days
# Learning Efficiency 1.00x
# Timezone           America/New_York
# Daily Goal         120 minutes
# Total Study Time   0 minutes
# Sessions Completed 0

# 5. Check notifications
fibocli notifications

# OUTPUT:
# 🔔 Notifications (1 unread)
# ID   Title                  Message                                  Type    Read Time
# 1    🎉 Welcome to FIBOCLI! Get started by creating your first e... system  🔴 2024-12-15 10:30

# 6. Check achievements (empty at start)
fibocli achievements

# OUTPUT:
# 🔒 Locked Achievements
# Achievement        Description                  Progress Points
# 🎯 First Steps     Complete your first study... 0/1 [░░░░░░░░░░░░░░░░░░░░] 10
# 🔥 Streak Starter  Maintain a 3-day study st... 1/3 [█████░░░░░░░░░░░░░░░] 25
# ⏱️ Dedicated Learner Complete 10 hours of to... 0/600 [░░░░░░░░░░░░░░░░░░░░] 50
# ... (more locked achievements)

# 7. Create first ecology
fibocli create ecology

# PROMPTS:
# Ecology name: Web Development Mastery
# Description: Full-stack web development journey from basics to advanced
# Course (optional): Web Development
# Course code (optional): WEB101
# Importance level (1-100): 85

# OUTPUT:
# ✅ Ecology created ID=1 (Web Development Mastery)
# 📊 Importance: 85.0, Points: 50

# 8. Create a forest under the ecology
fibocli create forest

# PROMPTS:
# Available Ecologies:
# #  ID  Name                  Course        Status
# 1  1   Web Development Ma... Web Develo... 🔒 Pending
# 
# Select number: 1
# Forest name: Frontend Technologies
# Description: Modern frontend frameworks and tools
# Course (optional): Frontend Development
# Course code (optional): FEND101
# Importance level (1-100): 80

# OUTPUT:
# ✅ Forest created ID=2 (Frontend Technologies)
# 📊 Importance: 80.0, Points: 40

# 9. Create a tree under the forest
fibocli create tree

# PROMPTS:
# Available Forests:
# #  ID  Name                  Course        Status
# 1  2   Frontend Technologies Frontend De... 🔒 Pending
# 
# Select number: 1
# Tree name: React Framework
# Description: React.js and ecosystem
# Course (optional): React Development
# Course code (optional): REACT201
# Importance level (1-100): 90

# OUTPUT:
# ✅ Tree created ID=3 (React Framework)
# 📊 Importance: 90.0, Points: 30

# 10. Create a super_branch-branch under the tree
fibocli create super_branch

# PROMPTS:
# Available Trees:
# #  ID  Name          Course        Status
# 1  3   React Framework React Devel... 🔒 Pending
# 
# Select number: 1
# super_branch-branch name: Core Concepts
# Description: Fundamental React concepts
# Course (optional): React Core
# Course code (optional): 
# Importance level (1-100): 85

# OUTPUT:
# ✅ super_branch-branch created ID=4 (Core Concepts)
# 📊 Importance: 85.0, Points: 25

# 11. Create a branch under the super_branch-branch
fibocli create branch

# PROMPTS:
# Available super_branch-branches:
# #  ID  Name          Course    Status
# 1  4   Core Concepts React C... 🔒 Pending
# 
# Select number: 1
# Branch name: Components
# Description: React component types and patterns
# Course (optional): 
# Course code (optional): 
# Importance level (1-100): 80

# OUTPUT:
# ✅ Branch created ID=5 (Components)
# 📊 Importance: 80.0, Points: 20

# 12. Create a sub-branch under the branch
fibocli create sub_branch

# PROMPTS:
# Available Branches:
# #  ID  Name       Course Status
# 1  5   Components        🔒 Pending
# 
# Select number: 1
# Sub-branch name: Functional Components
# Description: Modern React function components with hooks
# Course (optional): 
# Course code (optional): 
# Importance level (1-100): 85

# OUTPUT:
# ✅ Sub-branch created ID=6 (Functional Components)
# 📊 Importance: 85.0, Points: 15

# 13. Create a leaf (actual study item)
fibocli create leaf

# PROMPTS:
# Available Sub-branches:
# #  ID  Name                Course Status
# 1  6   Functional Components      🔒 Pending
# 
# Select number: 1
# Leaf name: useState Hook
# Description: Managing state in functional components
# Course (optional): 
# Course code (optional): 
# Importance level (1-100): 90
# Difficulty level (1-100): 70
# Initial understanding level (1-100): 20
# Prerequisites (comma-separated node IDs): 
# Minimum study duration (minutes): 15
# Maximum study duration (minutes): 45

# OUTPUT:
# ✅ Leaf created ID=7 (useState Hook)
# 📊 Importance: 90, Difficulty: 70, Understanding: 20
# ⏱️ Duration: 15-45 min, Prerequisites: 0

# 14. View the learning hierarchy
fibocli hierarchy --tree

# OUTPUT:
# 🌳 Learning Hierarchy
# 🔒 Pending 🌍 Web Development Mastery (ID: 1)
# └── 🔒 Pending 🌲 Frontend Technologies (ID: 2)
#     └── 🔒 Pending 🎄 React Framework (ID: 3)
#         └── 🔒 Pending 🟢 Core Concepts (ID: 4)
#             └── 🔒 Pending 🔶 Components (ID: 5)
#                 └── 🔒 Pending 🔷 Functional Components (ID: 6)
#                     └── 🔒 Pending 🍃 useState Hook (ID: 7) 🔴20% ⚡90 🎯70

# 15. Start first study session with auto-duration
fibocli study --auto-duration

# OUTPUT:
# 🤖 Auto-duration: 32 minutes
# 📚 Study session started for 32 minutes
# 
# 🎯 Today's Progress
# Level    Level 1
# Points   0 pts
# Streak   1 days 🔥
# Achievements 0 unlocked
# Daily Progress 0/120 min (0.0%)
# 
# Goal Progress: [░░░░░░░░░░░░░░░░░░░░] 0.0%

# 16. Wait 32 minutes (simulating study time) then complete session
fibocli study --complete --focus 85 --fatigue 35

# OUTPUT:
# ✅ Study session completed!
# 📊 Duration: 32.1 min, Focus: 85%, Efficiency: 1.00
# 🎯 Points earned: +27
# 📈 Learning efficiency: 1.02x
# 🔥 Streak updated!
# 🎯 Daily goal achieved! +10 bonus points!
# 🏆 Achievement unlocked: First Steps (+10 points)!

# 17. Check updated achievements
fibocli achievements

# OUTPUT:
# 🏆 Unlocked Achievements
# Achievement    Description              Points Unlocked
# 🎯 First Steps Complete your first st... 10   2024-12-15

# 🔒 Locked Achievements
# Achievement    Description              Progress Points
# 🔥 Streak Starter Maintain a 3-day st... 1/3 [█████░░░░░░░░░░░░░░░] 25
# ... (other locked achievements)

# 18. Check updated profile
fibocli whoami

# OUTPUT:
# 👤 john_developer's Profile
# Attribute           Value
# Username           john_developer
# Level              Level 1 (37.0% to next)
# Experience         37 XP
# Points             37 pts
# Current Streak     1 days 🔥
# Longest Streak     1 days
# Learning Efficiency 1.02x
# Timezone           America/New_York
# Daily Goal         120 minutes
# Total Study Time   32 minutes
# Sessions Completed 1

# 19. Check updated hierarchy with progress
fibocli hierarchy --tree --detailed

# OUTPUT:
# 🌳 Learning Hierarchy
# 🔒 Pending 🌍 Web Development Mastery (ID: 1) 🟢50% ⚡85 🎯50
# └── 🔒 Pending 🌲 Frontend Technologies (ID: 2) 🟢50% ⚡80 🎯50
#     └── 🔒 Pending 🎄 React Framework (ID: 3) 🟢50% ⚡90 🎯50
#         └── 🔒 Pending 🟢 Core Concepts (ID: 4) 🟢50% ⚡85 🎯50
#             └── 🔒 Pending 🔶 Components (ID: 5) 🟢50% ⚡80 🎯50
#                 └── 🔒 Pending 🔷 Functional Components (ID: 6) 🟢50% ⚡85 🎯50
#                     └── ▶ Active 🍃 useState Hook (ID: 7) 🟡65% ⚡90 🎯70

# 20. Set timezone properly
fibocli timezone --show

# OUTPUT:
# 🕐 Current timezone: America/New_York
# ⏰ Local time: 2024-12-15 11:15:22

# 21. Check
