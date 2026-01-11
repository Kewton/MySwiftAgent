#!/bin/bash
# V2 TaskFlow Tutorial - Simple curl commands (no jq required)
#
# Prerequisites:
#   - graphAiServer: http://localhost:8000
#   - expertAgent: http://localhost:8104 (for Tutorial 6, 7)
#   - Environment variables: TASKFLOW_ALLOW_HTTP=true, TASKFLOW_ALLOW_LOCAL=true

BASE_URL="http://localhost:8000/api/v2/workflows"

echo "=== Tutorial 1: Hello ==="
curl -s -X POST "$BASE_URL" -H "Content-Type: application/json" -d '{"workflow_name":"tutorial_1_hello","inputs":{}}'
echo -e "\n"

echo "=== Tutorial 2: POST with Body ==="
curl -s -X POST "$BASE_URL" -H "Content-Type: application/json" -d '{"workflow_name":"tutorial_2_post_with_body","inputs":{"title":"Test Post","body":"Test body","userId":"42"}}'
echo -e "\n"

echo "=== Tutorial 3: Sequential Chain ==="
curl -s -X POST "$BASE_URL" -H "Content-Type: application/json" -d '{"workflow_name":"tutorial_3_sequential_chain","inputs":{"post_id":"1"}}'
echo -e "\n"

echo "=== Tutorial 4: Parallel Fetch ==="
curl -s -X POST "$BASE_URL" -H "Content-Type: application/json" -d '{"workflow_name":"tutorial_4_parallel_fetch","inputs":{}}'
echo -e "\n"

echo "=== Tutorial 5: Local API ==="
curl -s -X POST "$BASE_URL" -H "Content-Type: application/json" -d '{"workflow_name":"tutorial_5_local_api","inputs":{}}'
echo -e "\n"

echo "=== Tutorial 6: Expert Agent ==="
curl -s -X POST "$BASE_URL" -H "Content-Type: application/json" -d '{"workflow_name":"tutorial_6_expert_agent","inputs":{}}'
echo -e "\n"

echo "=== Tutorial 7: Expert Agent Chat ==="
curl -s -X POST "$BASE_URL" -H "Content-Type: application/json" -d '{"workflow_name":"tutorial_7_expert_agent_chat","inputs":{"user_input":"Hello, what is 2+2?"}}'
echo -e "\n"

echo "=== Done ==="
