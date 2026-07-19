#!/usr/bin/env python3
"""Test script for team member profile auto-discovery."""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import json
import sqlite3
from backend.api.source_enrichment import enrich_team_members_from_deck

def test_discovery():
    """Test auto-discovery on the Jvala application."""
    print("=" * 60)
    print("Testing Team Member Profile Auto-Discovery")
    print("=" * 60)

    # Get the application from database
    conn = sqlite3.connect('backend/data/founderscore.sqlite3')
    cursor = conn.cursor()
    cursor.execute("SELECT signal_json, company_name FROM applications WHERE company_id = 'app-c07538e3e2'")
    row = cursor.fetchone()

    if not row:
        print("❌ Application not found")
        return

    signal = json.loads(row[0])
    company_name = row[1]

    print(f"\n📌 Company: {company_name}")

    # Extract team claims
    team_claims = [c for c in signal.get('deck_claims', []) if c.get('field') == 'team']

    if not team_claims:
        print("❌ No team claims found")
        return

    print(f"\n📋 Team claim found:")
    print(f"   {team_claims[0].get('value')}")

    # Run auto-discovery
    print(f"\n🔍 Running Tavily auto-discovery...")
    print(f"   (This will make API calls and may take 10-30 seconds)")

    discovered_team = enrich_team_members_from_deck(team_claims, company_name)

    print(f"\n✅ Discovered {len(discovered_team)} team members:")
    print()

    for member in discovered_team:
        print(f"👤 {member['name']} - {member['role']}")
        if member.get('linkedin'):
            print(f"   🔗 LinkedIn: {member['linkedin']}")
        else:
            print(f"   ⚠️  LinkedIn: Not found")
        if member.get('github'):
            print(f"   🔗 GitHub: {member['github']}")
        else:
            print(f"   ⚠️  GitHub: Not found")
        print()

    # Update database
    cursor.execute("SELECT profile_json FROM applications WHERE company_id = 'app-c07538e3e2'")
    profile_row = cursor.fetchone()

    if profile_row:
        profile = json.loads(profile_row[0])
        profile['team_members'] = discovered_team

        cursor.execute(
            "UPDATE applications SET profile_json = ? WHERE company_id = 'app-c07538e3e2'",
            (json.dumps(profile),)
        )
        conn.commit()
        print("✅ Database updated with discovered profiles")

    conn.close()
    print("\n" + "=" * 60)
    print("Test complete! Restart your backend to see the changes.")
    print("=" * 60)

if __name__ == "__main__":
    test_discovery()
