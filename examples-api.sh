#!/bin/bash
# Example API Calls for Shift Scheduler SaaS
# Run these commands to test the full workflow

BASE_URL="http://localhost:5000"

echo "🎯 Shift Scheduler SaaS - Full Workflow Example"
echo "=============================================="
echo ""

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Step 1: Register Business
echo -e "${BLUE}Step 1: Register Business${NC}"
REGISTER_RESPONSE=$(curl -s -X POST "$BASE_URL/api/register-business" \
  -H "Content-Type: application/json" \
  -d '{
    "business_name": "Acme Hospital",
    "manager_name": "Dr. Smith"
  }')

echo "Response:"
echo "$REGISTER_RESPONSE" | jq .

# Extract business number for join link
BUSINESS_NUMBER=$(echo "$REGISTER_RESPONSE" | jq -r '.business_number // empty')
echo -e "${GREEN}✓ Business created with number: $BUSINESS_NUMBER${NC}"
echo ""

# Step 2: Add Workers
echo -e "${BLUE}Step 2: Add Workers (Manager Only)${NC}"

WORKER_1=$(curl -s -X POST "$BASE_URL/api/workers" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Alice Johnson",
    "seniority_level": 3,
    "hourly_rate": 28.50,
    "skills": ["ICU", "Critical Care"]
  }')

echo "Worker 1 (Alice):"
echo "$WORKER_1" | jq .

WORKER_2=$(curl -s -X POST "$BASE_URL/api/workers" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Bob Smith",
    "seniority_level": 2,
    "hourly_rate": 22.00,
    "skills": ["General Care"]
  }')

echo "Worker 2 (Bob):"
echo "$WORKER_2" | jq .

WORKER_3=$(curl -s -X POST "$BASE_URL/api/workers" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Carol Davis",
    "seniority_level": 4,
    "hourly_rate": 32.00,
    "skills": ["Surgery", "Critical Care"]
  }')

echo "Worker 3 (Carol):"
echo "$WORKER_3" | jq .

echo -e "${GREEN}✓ 3 workers added${NC}"
echo ""

# Step 3: Get All Workers
echo -e "${BLUE}Step 3: List All Workers${NC}"
curl -s -X GET "$BASE_URL/api/workers" | jq .
echo ""

# Step 4: Create Shifts
echo -e "${BLUE}Step 4: Create Shifts (Manager Only)${NC}"

SHIFT_1=$(curl -s -X POST "$BASE_URL/api/shifts" \
  -H "Content-Type: application/json" \
  -d '{
    "date": "2025-04-01",
    "start_time": "08:00",
    "end_time": "16:00",
    "workers_required": 2,
    "required_skills": "ICU",
    "hourly_rate_multiplier": 1.0
  }')

echo "Shift 1 (ICU 8am-4pm):"
echo "$SHIFT_1" | jq .

SHIFT_2=$(curl -s -X POST "$BASE_URL/api/shifts" \
  -H "Content-Type: application/json" \
  -d '{
    "date": "2025-04-01",
    "start_time": "16:00",
    "end_time": "00:00",
    "workers_required": 1,
    "required_skills": "Critical Care",
    "hourly_rate_multiplier": 1.5
  }')

echo "Shift 2 (Night Critical Care 4pm-12am):"
echo "$SHIFT_2" | jq .

SHIFT_3=$(curl -s -X POST "$BASE_URL/api/shifts" \
  -H "Content-Type: application/json" \
  -d '{
    "date": "2025-04-02",
    "start_time": "08:00",
    "end_time": "16:00",
    "workers_required": 3,
    "hourly_rate_multiplier": 1.0
  }')

echo "Shift 3 (General 8am-4pm):"
echo "$SHIFT_3" | jq .

echo -e "${GREEN}✓ 3 shifts created (all Open by default)${NC}"
echo ""

# Step 5: Get All Shifts
echo -e "${BLUE}Step 5: List All Shifts${NC}"
curl -s -X GET "$BASE_URL/api/shifts" | jq .
echo ""

# Step 6: Close Shifts to Gather Interest
echo -e "${BLUE}Step 6: Close Shifts (Begin Interest Gathering)${NC}"

echo "Closing Shift 1..."
curl -s -X PUT "$BASE_URL/api/shifts/1/status" \
  -H "Content-Type: application/json" \
  -d '{"status": "Closed"}' | jq .

echo "Closing Shift 2..."
curl -s -X PUT "$BASE_URL/api/shifts/2/status" \
  -H "Content-Type: application/json" \
  -d '{"status": "Closed"}' | jq .

echo "Closing Shift 3..."
curl -s -X PUT "$BASE_URL/api/shifts/3/status" \
  -H "Content-Type: application/json" \
  -d '{"status": "Closed"}' | jq .

echo -e "${GREEN}✓ All shifts closed for interest gathering${NC}"
echo ""

# Step 7: Workers Express Interest
echo -e "${BLUE}Step 7: Workers Express Interest${NC}"

echo "Alice expressing interest in Shift 1..."
curl -s -X POST "$BASE_URL/api/shifts/1/interest" | jq .

echo "Alice expressing interest in Shift 2..."
curl -s -X POST "$BASE_URL/api/shifts/2/interest" | jq .

echo "Bob expressing interest in Shift 1..."
curl -s -X POST "$BASE_URL/api/shifts/1/interest" | jq .

echo "Bob expressing interest in Shift 3..."
curl -s -X POST "$BASE_URL/api/shifts/3/interest" | jq .

echo "Carol expressing interest in Shift 1..."
curl -s -X POST "$BASE_URL/api/shifts/1/interest" | jq .

echo "Carol expressing interest in Shift 2..."
curl -s -X POST "$BASE_URL/api/shifts/2/interest" | jq .

echo "Carol expressing interest in Shift 3..."
curl -s -X POST "$BASE_URL/api/shifts/3/interest" | jq .

echo -e "${GREEN}✓ Workers have expressed interests${NC}"
echo ""

# Step 8: Manager Views Interest Dashboard
echo -e "${BLUE}Step 8: Manager Views Interest Dashboard${NC}"
echo "Interest counts per shift:"
curl -s -X GET "$BASE_URL/api/shift-interests" | jq .
echo ""

# Step 9: Get Business Statistics
echo -e "${BLUE}Step 9: View Business Statistics${NC}"
curl -s -X GET "$BASE_URL/api/stats" | jq .
echo ""

# Step 10: Run Solver
echo -e "${BLUE}Step 10: Run Solver to Generate Schedules${NC}"
SCHEDULE=$(curl -s -X POST "$BASE_URL/api/schedule" \
  -H "Content-Type: application/json" \
  -d '{
    "top_k": 3,
    "weights": {
      "time_off_request_weight": 10.0,
      "seniority_reward_weight": 8.0,
      "weekend_balance_weight": 6.0,
      "skill_matching_weight": 9.0,
      "workload_balance_weight": 7.0,
      "compensation_minimization_weight": 3.0,
      "overstaffing_penalty_weight": 5.0
    }
  }')

echo "$SCHEDULE" | jq .

echo ""
echo -e "${GREEN}✅ Full workflow complete!${NC}"
echo ""
echo "Summary:"
echo "--------"
echo "✓ Business registered"
echo "✓ 3 Workers added"
echo "✓ 3 Shifts created"
echo "✓ Shifts closed for interest gathering"
echo "✓ Workers expressed interests"
echo "✓ Manager viewed interest dashboard"
echo "✓ Solver generated 3 schedule options"
echo ""

# Step 11: Worker Testing (Optional)
echo -e "${BLUE}Step 11: Worker Views Their Interests (Optional)${NC}"
echo "Note: This would require worker session. Format:"
echo 'curl -X GET "$BASE_URL/api/shift-interests/me"'
echo ""

echo "---"
echo "To run this script:"
echo "  1. Start the server: python web_interface.py"
echo "  2. In another terminal: bash examples-api.sh"
echo ""
echo "Note: Replace 'localhost:5000' with your server URL for remote servers"
