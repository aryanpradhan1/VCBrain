#!/bin/bash
# Quick API test script

echo "🧪 Testing FounderScore API"
echo "================================"

BASE_URL="http://localhost:8000"

echo ""
echo "1️⃣  Health Check"
curl -s $BASE_URL/health | python3 -m json.tool
echo ""

echo "2️⃣  List Opportunities"
curl -s $BASE_URL/opportunities | python3 -m json.tool | head -20
echo "... (truncated)"
echo ""

echo "3️⃣  Get Opportunity Details (opp_1)"
curl -s $BASE_URL/opportunities/opp_1 | python3 -m json.tool | head -30
echo "... (truncated)"
echo ""

echo "4️⃣  Get Founder Results (f001)"
curl -s $BASE_URL/founders/f001/results | python3 -m json.tool
echo ""

echo "5️⃣  Query: 'technical founder'"
curl -s "$BASE_URL/opportunities?query=technical%20founder" | python3 -m json.tool | head -20
echo "... (truncated)"
echo ""

echo "6️⃣  Record Decision (approve)"
curl -s -X POST $BASE_URL/opportunities/opp_1/decision \
  -H "Content-Type: application/json" \
  -d '{"decision": "approve"}' | python3 -m json.tool
echo ""

echo "✅ All API tests complete!"
echo ""
echo "💡 For interactive testing, visit: http://localhost:8000/docs"
