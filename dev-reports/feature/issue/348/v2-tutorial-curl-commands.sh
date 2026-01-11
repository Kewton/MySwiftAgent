#!/bin/bash
# V2 TaskFlow Tutorial - curl commands
#
# Prerequisites:
#   - graphAiServer: http://localhost:8000
#   - expertAgent: http://localhost:8104 (for Tutorial 6, 7)
#   - Environment variables: TASKFLOW_ALLOW_HTTP=true, TASKFLOW_ALLOW_LOCAL=true

set -e

BASE_URL="http://localhost:8000/api/v2/workflows"

echo "=== Tutorial 1: Hello (GET + Transform) ==="
curl -s -X POST "$BASE_URL" -H "Content-Type: application/json" -d '{"workflow_name":"tutorial_1_hello","inputs":{}}' | jq '.results["_output"]'
echo ""

echo "=== Tutorial 2: POST with Body ==="
curl -s -X POST "$BASE_URL" -H "Content-Type: application/json" -d '{"workflow_name":"tutorial_2_post_with_body","inputs":{"title":"Test Post","body":"Test body","userId":"42"}}' | jq '.results["_output"]'
echo ""

echo "=== Tutorial 3: Sequential Chain ==="
curl -s -X POST "$BASE_URL" -H "Content-Type: application/json" -d '{"workflow_name":"tutorial_3_sequential_chain","inputs":{"post_id":"1"}}' | jq '.results["_output"]'
echo ""

echo "=== Tutorial 4: Parallel Fetch ==="
curl -s -X POST "$BASE_URL" -H "Content-Type: application/json" -d '{"workflow_name":"tutorial_4_parallel_fetch","inputs":{}}' | jq '.results["_output"]'
echo ""

echo "=== Tutorial 5: Local API (graphAiServer health) ==="
curl -s -X POST "$BASE_URL" -H "Content-Type: application/json" -d '{"workflow_name":"tutorial_5_local_api","inputs":{}}' | jq '.results["_output"]'
echo ""

echo "=== Tutorial 6: Expert Agent (GET) ==="
curl -s -X POST "$BASE_URL" -H "Content-Type: application/json" -d '{"workflow_name":"tutorial_6_expert_agent","inputs":{}}' | jq '.results["_output"]'
echo ""

echo "=== Tutorial 7: Expert Agent Chat (POST with test_mode) ==="
curl -s -X POST "$BASE_URL" -H "Content-Type: application/json" -d '{"workflow_name":"tutorial_7_expert_agent_chat","inputs":{"user_input":"Hello, what is 2+2?"}}' | jq '.results["_output"]'
echo ""

echo "=== All tutorials completed ==="
