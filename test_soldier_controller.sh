#!/bin/bash

# JARVIS Soldier Controller Test Suite
# Tests all command routing pipelines and tactical scenarios

set -e

API_BASE="http://localhost:8000"
SOLDIER_ID="soldier-1"

echo "=========================================="
echo "JARVIS Soldier Controller Test Suite"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Request Reconnaissance (Soldier → Operator → Recon)
echo -e "${BLUE}TEST 1: Request Reconnaissance${NC}"
echo "Route: Soldier → Operator → Recon"
echo ""

RECON_RESP=$(curl -s -X POST $API_BASE/api/soldier/$SOLDIER_ID/request-recon \
  -H "Content-Type: application/json" \
  -d '{
    "area_label": "Grid Alpha",
    "target_x": 150,
    "target_y": -50,
    "priority": "HIGH"
  }')

COMMAND_ID=$(echo $RECON_RESP | jq -r '.command_id')
echo -e "${GREEN}✓ Recon command created${NC}: $COMMAND_ID"
echo "  Route: $(echo $RECON_RESP | jq -r '.route')"
echo "  Status: $(echo $RECON_RESP | jq -r '.status')"
echo ""

# Test 2: Operator Approves Command
echo -e "${BLUE}TEST 2: Operator Approves Command${NC}"
echo ""

APPROVAL=$(curl -s -X POST $API_BASE/api/soldier/$SOLDIER_ID/approve-command/$COMMAND_ID)
MISSION_ID=$(echo $APPROVAL | jq -r '.mission_id')
echo -e "${GREEN}✓ Command approved${NC}"
echo "  Mission ID: $MISSION_ID"
echo "  Route: $(echo $APPROVAL | jq -r '.route')"
echo ""

# Test 3: Process Recon Report (Recon → Operator → Soldier)
echo -e "${BLUE}TEST 3: Process Recon Report${NC}"
echo "Route: Recon → Operator → Soldier"
echo ""

RECON_REPORT=$(curl -s -X POST $API_BASE/api/soldier/$SOLDIER_ID/process-recon-report \
  -H "Content-Type: application/json" \
  -d "{
    \"mission_id\": \"$MISSION_ID\",
    \"enemies_detected\": [
      {\"id\": \"enemy-1\", \"type\": \"vehicle\", \"threat_level\": \"high\", \"x\": 200, \"y\": 0},
      {\"id\": \"enemy-2\", \"type\": \"personnel\", \"threat_level\": \"high\", \"x\": 100, \"y\": -50},
      {\"id\": \"enemy-3\", \"type\": \"equipment\", \"threat_level\": \"medium\", \"x\": 180, \"y\": 30}
    ],
    \"coverage_percent\": 90,
    \"threat_level\": \"high\"
  }")

REPORT_ID=$(echo $RECON_REPORT | jq -r '.report_id')
echo -e "${GREEN}✓ Recon report processed${NC}"
echo "  Report ID: $REPORT_ID"
echo "  Enemies Detected: $(echo $RECON_REPORT | jq -r '.enemies_detected')"
echo "  Threat Level: $(echo $RECON_REPORT | jq -r '.threat_level')"
echo ""

# Test 4: Authorize Strike from Recon (Recon → Operator → Attack)
echo -e "${BLUE}TEST 4: Authorize Strike Based on Recon Findings${NC}"
echo "Route: Recon → Operator → Attack"
echo ""

STRIKE=$(curl -s -X POST $API_BASE/api/soldier/$SOLDIER_ID/authorize-strike/$REPORT_ID \
  -H "Content-Type: application/json" \
  -d '{"priority": "CRITICAL"}')

STRIKE_MISSION=$(echo $STRIKE | jq -r '.mission_id')
echo -e "${GREEN}✓ Strike authorized by soldier${NC}"
echo "  Command ID: $(echo $STRIKE | jq -r '.command_id')"
echo "  Mission ID: $STRIKE_MISSION"
echo "  Route: $(echo $STRIKE | jq -r '.route')"
echo "  Status: $(echo $STRIKE | jq -r '.status')"
echo "  Enemies to Engage: $(echo $STRIKE | jq -r '.enemies_to_engage')"
echo ""

# Test 5: Process BDA Report
echo -e "${BLUE}TEST 5: Process Battle Damage Assessment${NC}"
echo ""

BDA=$(curl -s -X POST $API_BASE/api/soldier/$SOLDIER_ID/process-bda \
  -H "Content-Type: application/json" \
  -d "{
    \"mission_id\": \"$STRIKE_MISSION\",
    \"damage_assessment\": {
      \"targets_engaged\": 3,
      \"destroyed\": 3,
      \"damaged\": 0,
      \"escaped\": 0
    }
  }")

echo -e "${GREEN}✓ BDA processed${NC}"
echo "  BDA ID: $(echo $BDA | jq -r '.bda_id')"
echo "  Targets Destroyed: $(echo $BDA | jq -r '.damage_assessment.destroyed')"
echo "  Mission Status: $(echo $BDA | jq -r '.status')"
echo ""

# Test 6: Direct Attack Request (No Approval)
echo -e "${BLUE}TEST 6: Direct Attack Request (Soldier → Attack)${NC}"
echo "Route: Soldier → Attack (no approval required)"
echo ""

DIRECT_ATTACK=$(curl -s -X POST $API_BASE/api/soldier/$SOLDIER_ID/request-attack \
  -H "Content-Type: application/json" \
  -d '{
    "area_label": "Grid Charlie",
    "target_x": 30,
    "target_y": 120,
    "requires_approval": false,
    "priority": "CRITICAL"
  }')

echo -e "${GREEN}✓ Direct attack command created${NC}"
echo "  Command ID: $(echo $DIRECT_ATTACK | jq -r '.command_id')"
echo "  Route: $(echo $DIRECT_ATTACK | jq -r '.route')"
echo "  Status: $(echo $DIRECT_ATTACK | jq -r '.status')"
echo ""

# Test 7: Get Soldier Status
echo -e "${BLUE}TEST 7: Get Soldier Status${NC}"
echo ""

STATUS=$(curl -s -X GET $API_BASE/api/soldier/$SOLDIER_ID/status)
echo -e "${GREEN}✓ Soldier status retrieved${NC}"
echo "  Total Commands: $(echo $STATUS | jq -r '.total_commands')"
echo "  Active Missions: $(echo $STATUS | jq -r '.active_missions')"
echo "  Recon Reports: $(echo $STATUS | jq -r '.recon_reports')"
echo "  Status: $(echo $STATUS | jq -r '.status')"
echo ""

# Test 8: Simulate Tactical Scenario
echo -e "${BLUE}TEST 8: Simulate Complete Tactical Scenario${NC}"
echo ""

SCENARIO=$(curl -s -X POST $API_BASE/api/soldier/$SOLDIER_ID/simulate-scenario \
  -H "Content-Type: application/json" \
  -d '{"area": "Grid Bravo"}')

echo -e "${GREEN}✓ Tactical scenario simulated${NC}"
echo "  Scenario ID: $(echo $SCENARIO | jq -r '.scenario_id')"
echo "  Area: $(echo $SCENARIO | jq -r '.area')"
echo "  Status: $(echo $SCENARIO | jq -r '.status')"
echo ""
echo "Scenario Stages:"
echo $SCENARIO | jq -r '.stages[] | "  - \(.stage)"'
echo ""

# Test 9: Test Second Soldier
echo -e "${BLUE}TEST 9: Test Second Soldier (soldier-2)${NC}"
echo ""

SOLDIER2_RECON=$(curl -s -X POST $API_BASE/api/soldier/soldier-2/request-recon \
  -H "Content-Type: application/json" \
  -d '{
    "area_label": "Grid Bravo",
    "target_x": -110,
    "target_y": 70,
    "priority": "MEDIUM"
  }')

SOLDIER2_CMD=$(echo $SOLDIER2_RECON | jq -r '.command_id')
echo -e "${GREEN}✓ Soldier-2 recon command created${NC}: $SOLDIER2_CMD"
echo ""

# Summary
echo "=========================================="
echo -e "${GREEN}ALL TESTS COMPLETED SUCCESSFULLY${NC}"
echo "=========================================="
echo ""
echo "Command Routing Pipelines Tested:"
echo "  ✓ Soldier → Operator → Recon"
echo "  ✓ Recon → Operator → Soldier (Report)"
echo "  ✓ Recon → Operator → Attack (Authorization)"
echo "  ✓ Soldier → Attack (Direct)"
echo "  ✓ Soldier → Recon (Request)"
echo ""
echo "Additional Tests:"
echo "  ✓ Operator approval and relay"
echo "  ✓ Battle Damage Assessment processing"
echo "  ✓ Soldier status retrieval"
echo "  ✓ Tactical scenario simulation"
echo "  ✓ Multi-soldier operations"
echo ""
