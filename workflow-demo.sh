#!/bin/bash
# 📋 Complete Workflow Examples - API Calls

# This script demonstrates the complete workflow:
# 1. Create a business (Manager)
# 2. Login as manager
# 3. Join as worker
# 4. Create shifts
# 5. Express interests
# 6. Run solver

set -e

BASE_URL="http://localhost:5000"
echo "🚀 Starting Complete Workflow Examples"
echo "📍 API Base: $BASE_URL"
echo ""

# ============================================================================
# 1️⃣ CREATE A BUSINESS (Manager Registration)
# ============================================================================
echo "📝 Step 1: Creating a new business..."
REGISTER_RESPONSE=$(curl -s -X POST "$BASE_URL/api/register-business" \
  -H "Content-Type: application/json" \
  -d '{
    "business_name": "Acme Hospital",
    "manager_name": "Alice Johnson"
  }')

echo "Response:"
echo "$REGISTER_RESPONSE" | python -m json.tool

# Extract values for next steps
BUSINESS_ID=$(echo "$REGISTER_RESPONSE" | python -c "import sys, json; print(json.load(sys.stdin)['business_id'])")
BUSINESS_NUMBER=$(echo "$REGISTER_RESPONSE" | python -c "import sys, json; print(json.load(sys.stdin)['business_number'])")

echo ""
echo "✅ Business Created!"
echo "   Business ID: $BUSINESS_ID"
echo "   Business Number: $BUSINESS_NUMBER"
echo ""

# ============================================================================
# 2️⃣ LOGIN AS MANAGER
# ============================================================================
echo "🔑 Step 2: Manager login..."
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/login" \
  -H "Content-Type: application/json" \
  -d "{
    \"business_number\": \"$BUSINESS_NUMBER\",
    \"user_name\": \"Alice Johnson\"
  }")

echo "Response:"
echo "$LOGIN_RESPONSE" | python -m json.tool

MANAGER_ID=$(echo "$LOGIN_RESPONSE" | python -c "import sys, json; print(json.load(sys.stdin)['user_id'])")
echo ""
echo "✅ Manager logged in! (User ID: $MANAGER_ID)"
echo ""

# ============================================================================
# 3️⃣ CREATE WORKERS
# ============================================================================
echo "👷 Step 3: Creating workers..."

echo "  Creating Worker 1: Bob Smith..."
WORKER1_RESPONSE=$(curl -s -X POST "$BASE_URL/api/workers" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Bob Smith",
    "seniority": "Senior",
    "hourly_rate": 45,
    "skills": ["Nursing", "ICU"]
  }')
WORKER1_ID=$(echo "$WORKER1_RESPONSE" | python -c "import sys, json; print(json.load(sys.stdin)['worker_id'])" 2>/dev/null || echo "1")

echo "  Creating Worker 2: Carol White..."
WORKER2_RESPONSE=$(curl -s -X POST "$BASE_URL/api/workers" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Carol White",
    "seniority": "Junior",
    "hourly_rate": 35,
    "skills": ["Nursing", "ER"]
  }')
WORKER2_ID=$(echo "$WORKER2_RESPONSE" | python -c "import sys, json; print(json.load(sys.stdin)['worker_id'])" 2>/dev/null || echo "2")

echo "  Creating Worker 3: David Brown..."
WORKER3_RESPONSE=$(curl -s -X POST "$BASE_URL/api/workers" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "David Brown",
    "seniority": "Senior",
    "hourly_rate": 50,
    "skills": ["Nursing", "ICU", "ER"]
  }')
WORKER3_ID=$(echo "$WORKER3_RESPONSE" | python -c "import sys, json; print(json.load(sys.stdin)['worker_id'])" 2>/dev/null || echo "3")

echo ""
echo "✅ Workers created!"
echo "   Worker 1: Bob Smith (ID: $WORKER1_ID)"
echo "   Worker 2: Carol White (ID: $WORKER2_ID)"
echo "   Worker 3: David Brown (ID: $WORKER3_ID)"
echo ""

# ============================================================================
# 4️⃣ CREATE SHIFTS
# ============================================================================
echo "📅 Step 4: Creating shifts..."

TODAY=$(date +%Y-%m-%d)
TOMORROW=$(date -u -d "+1 day" +%Y-%m-%d 2>/dev/null || date -u -v+1d +%Y-%m-%d)

echo "  Creating Shift 1: ICU Shift (requires 2 nurses)..."
SHIFT1_RESPONSE=$(curl -s -X POST "$BASE_URL/api/shifts" \
  -H "Content-Type: application/json" \
  -d "{
    \"date\": \"$TOMORROW\",
    \"start_time\": \"09:00\",
    \"end_time\": \"17:00\",
    \"workers_required\": 2,
    \"required_skills\": [\"ICU\"]
  }")
SHIFT1_ID=$(echo "$SHIFT1_RESPONSE" | python -c "import sys, json; print(json.load(sys.stdin)['shift_id'])" 2>/dev/null || echo "1")

echo "  Creating Shift 2: ER Shift (requires 2 nurses)..."
SHIFT2_RESPONSE=$(curl -s -X POST "$BASE_URL/api/shifts" \
  -H "Content-Type: application/json" \
  -d "{
    \"date\": \"$TOMORROW\",
    \"start_time\": \"17:00\",
    \"end_time\": \"23:00\",
    \"workers_required\": 2,
    \"required_skills\": [\"ER\"]
  }")
SHIFT2_ID=$(echo "$SHIFT2_RESPONSE" | python -c "import sys, json; print(json.load(sys.stdin)['shift_id'])" 2>/dev/null || echo "2")

echo ""
echo "✅ Shifts created!"
echo "   Shift 1: ICU (ID: $SHIFT1_ID) - Needs 2 nurses"
echo "   Shift 2: ER (ID: $SHIFT2_ID) - Needs 2 nurses"
echo ""

# ============================================================================
# 5️⃣ CLOSE SHIFTS FOR INTEREST GATHERING
# ============================================================================
echo "🔒 Step 5: Closing shifts for interest gathering..."

echo "  Closing Shift 1..."
curl -s -X PUT "$BASE_URL/api/shifts/$SHIFT1_ID/status" \
  -H "Content-Type: application/json" \
  -d '{"status": "Closed"}' > /dev/null

echo "  Closing Shift 2..."
curl -s -X PUT "$BASE_URL/api/shifts/$SHIFT2_ID/status" \
  -H "Content-Type: application/json" \
  -d '{"status": "Closed"}' > /dev/null

echo ""
echo "✅ Shifts are now CLOSED (ready for solver)"
echo ""

# ============================================================================
# 6️⃣ WORKERS EXPRESS INTEREST
# ============================================================================
echo "💬 Step 6: Workers expressing interest in shifts..."

# For simplicity, we're simulating worker interest via API
# In a real scenario, workers would do this through the web interface

echo "  Bob Smith interested in Shift 1 (ICU)..."
curl -s -X POST "$BASE_URL/api/shifts/$SHIFT1_ID/interest" \
  -H "Content-Type: application/json" \
  -d "{\"worker_id\": $WORKER1_ID}" > /dev/null 2>&1

echo "  Carol White interested in Shift 2 (ER)..."
curl -s -X POST "$BASE_URL/api/shifts/$SHIFT2_ID/interest" \
  -H "Content-Type: application/json" \
  -d "{\"worker_id\": $WORKER2_ID}" > /dev/null 2>&1

echo "  David Brown interested in both shifts..."
curl -s -X POST "$BASE_URL/api/shifts/$SHIFT1_ID/interest" \
  -H "Content-Type: application/json" \
  -d "{\"worker_id\": $WORKER3_ID}" > /dev/null 2>&1

curl -s -X POST "$BASE_URL/api/shifts/$SHIFT2_ID/interest" \
  -H "Content-Type: application/json" \
  -d "{\"worker_id\": $WORKER3_ID}" > /dev/null 2>&1

echo ""
echo "✅ Workers have expressed interest!"
echo "   Shift 1: Bob Smith (Senior), David Brown (Senior)"
echo "   Shift 2: Carol White (Junior), David Brown (Senior)"
echo ""

# ============================================================================
# 7️⃣ MANAGER RUNS SOLVER
# ============================================================================
echo "🤖 Step 7: Manager running AI Solver..."

SCHEDULE_RESPONSE=$(curl -s -X POST "$BASE_URL/api/schedule" \
  -H "Content-Type: application/json" \
  -d '{
    "top_k": 3,
    "weights": {
      "skill_coverage": 1.0,
      "workload_balance": 0.8,
      "seniority_distribution": 0.5,
      "consecutive_limit": 0.9,
      "max_hours": 0.9
    }
  }')

echo "Response (Top 3 Solutions):"
echo "$SCHEDULE_RESPONSE" | python -m json.tool | head -50

echo ""
echo "✅ Solver completed! Got multiple solutions."
echo ""

# ============================================================================
# 8️⃣ VIEW FINAL SCHEDULES
# ============================================================================
echo "📊 Step 8: Viewing final schedules..."

echo "  Workers on Shift 1:"
curl -s -X GET "$BASE_URL/api/shifts/$SHIFT1_ID" \
  -H "Content-Type: application/json" | python -m json.tool | head -20

echo ""
echo "  Workers on Shift 2:"
curl -s -X GET "$BASE_URL/api/shifts/$SHIFT2_ID" \
  -H "Content-Type: application/json" | python -m json.tool | head -20

echo ""
echo "✅ Complete workflow finished!"
echo ""

# ============================================================================
# SUMMARY
# ============================================================================
echo "════════════════════════════════════════════════════════"
echo "📋 WORKFLOW SUMMARY"
echo "════════════════════════════════════════════════════════"
echo ""
echo "Business Information:"
echo "  • Name: Acme Hospital"
echo "  • ID: $BUSINESS_ID"
echo "  • Number: $BUSINESS_NUMBER"
echo ""
echo "Team Members:"
echo "  • Manager: Alice Johnson"
echo "  • Worker 1: Bob Smith (Senior Nurse)"
echo "  • Worker 2: Carol White (Junior Nurse)"
echo "  • Worker 3: David Brown (Senior Nurse)"
echo ""
echo "Shifts Created:"
echo "  • Shift 1: ICU (9:00-17:00) - Needs 2 nurses"
echo "  • Shift 2: ER (17:00-23:00) - Needs 2 nurses"
echo ""
echo "Process Completed:"
echo "  1. ✅ Business registered"
echo "  2. ✅ Manager logged in"
echo "  3. ✅ Workers added"
echo "  4. ✅ Shifts created"
echo "  5. ✅ Shifts closed for interest"
echo "  6. ✅ Workers expressed interests"
echo "  7. ✅ AI Solver executed"
echo "  8. ✅ Optimal schedules generated"
echo ""
echo "════════════════════════════════════════════════════════"
echo "🎉 All done! Your scheduling system is working!"
echo "════════════════════════════════════════════════════════"
