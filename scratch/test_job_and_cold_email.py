#!/usr/bin/env python3
"""
Test suite for Jarvis Cold Outreach & Job Search Suite.
Validates profile manager, LinkedIn live search, Web job search,
contact finder, cold email draft synthesis, confirmation safety,
application tracking, and Brain tool registration.
"""

import sys
import os

# Add jarvis-2.0 to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from skills.profile_manager import get_user_profile, update_user_profile, view_candidate_profile
from skills.linkedin_jobs import search_linkedin_jobs_data, get_linkedin_job_details, get_cached_jobs
from skills.job_search import search_web_jobs, find_company_contacts, get_cached_web_jobs
from skills.email_sender import (
    draft_cold_email,
    preview_pending_cold_email,
    confirm_send_cold_email,
    cancel_send_cold_email,
    has_pending_cold_email,
    get_pending_cold_email,
)
from skills.cold_outreach_tracker import (
    log_cold_application,
    list_cold_applications,
    get_outreach_analytics,
)
from brain import Brain


def test_profile_manager():
    print("\n--- 1. Testing Candidate Profile Manager ---")
    profile = get_user_profile()
    assert "full_name" in profile, "Profile must have full_name"
    assert "skills" in profile, "Profile must have skills"
    print("✅ Profile loaded successfully:", profile.get("full_name"))

    update_res = update_user_profile(skills="Python, FastAPI, React, AI/LLMs, Docker")
    assert "successfully" in update_res
    print("✅ Profile updated successfully")

    view = view_candidate_profile()
    assert "Candidate Profile" in view
    print("✅ Profile view output formatted properly")


def test_linkedin_job_search():
    print("\n--- 2. Testing LinkedIn Job Search & Detail Extraction ---")
    res = search_linkedin_jobs_data(job_title="Python Developer", location="Remote", max_results=3)
    print("Search Result Preview:\n", res[:250], "...\n")
    assert "LinkedIn Job Opportunities" in res

    cached = get_cached_jobs()
    print(f"✅ Cached {len(cached)} LinkedIn jobs")
    if cached:
        first_job = cached[0]
        print(f"First Job: {first_job['title']} at {first_job['company']}")
        # Test detail fetching
        details = get_linkedin_job_details("#1")
        print("Details Preview:\n", details[:200], "...\n")
        assert "Job Specifications" in details or "Unable to fetch" in details
        print("✅ LinkedIn detail extraction tested")


def test_web_job_search():
    print("\n--- 3. Testing Web Job Search & Contact Finder ---")
    web_res = search_web_jobs(job_title="Full Stack Engineer", location="India", max_results=3)
    print("Web Search Result Preview:\n", web_res[:250], "...\n")
    assert "Web Job Search Results" in web_res or "No job postings found" in web_res
    print("✅ Web job search executed")

    contact_res = find_company_contacts("Postman", "postman.com")
    print("Contact Finder Preview:\n", contact_res[:200], "...\n")
    assert "Contact & Email Intelligence" in contact_res
    print("✅ Contact finder executed")


def test_cold_email_workflow():
    print("\n--- 4. Testing Cold Email Drafting & Safety Workflow ---")
    draft_res = draft_cold_email(
        to_email="recruiting@exampletech.com",
        recipient_name="Sarah",
        company="ExampleTech",
        job_title="Senior Python & AI Engineer",
        custom_notes="I have built an autonomous Iron Man Jarvis assistant with real-time multi-agent workflows.",
        attach_resume=False,
    )
    print("Draft Output Preview:\n", draft_res[:300], "...\n")
    assert has_pending_cold_email() is True
    pending = get_pending_cold_email()
    assert pending["to_email"] == "recruiting@exampletech.com"
    assert pending["company"] == "ExampleTech"
    assert "ExampleTech" in pending["body"]
    print("✅ Cold email successfully drafted and staged in memory")

    preview = preview_pending_cold_email()
    assert "recruiting@exampletech.com" in preview
    print("✅ Draft preview verified")

    # Test cancel safety flow
    cancel_res = cancel_send_cold_email()
    assert has_pending_cold_email() is False
    assert "cancelled" in cancel_res
    print("✅ Cold email cancellation verified")


def test_outreach_tracker():
    print("\n--- 5. Testing Outreach Tracker ---")
    entry = log_cold_application(
        company="TestCorp",
        job_title="Backend Developer",
        recipient_email="jobs@testcorp.com",
        recipient_name="Alex",
        subject="Application: Backend Developer",
        body="Sample body content",
        status="SENT",
    )
    assert entry["id"].startswith("app_")
    print("✅ Application logged with ID:", entry["id"])

    log_view = list_cold_applications(limit=5)
    assert "Cold Outreach Log" in log_view
    assert "TestCorp" in log_view
    print("✅ Tracker listing verified")

    analytics = get_outreach_analytics()
    assert "Cold Outreach Performance" in analytics
    print("✅ Analytics calculation verified")


def test_brain_tool_registration():
    print("\n--- 6. Testing Brain Tool Registration ---")
    brain = Brain()
    tool_names = [t["name"] for t in brain._all_tools]
    print(f"Total tools registered in Brain: {len(tool_names)}")

    required_tools = [
        "search_linkedin_jobs_data",
        "get_linkedin_job_details",
        "search_web_jobs",
        "find_company_contacts",
        "view_candidate_profile",
        "update_user_profile",
        "draft_cold_email",
        "confirm_send_cold_email",
        "cancel_send_cold_email",
        "preview_pending_cold_email",
        "list_cold_applications",
        "get_outreach_analytics",
    ]

    for req in required_tools:
        assert req in tool_names, f"Missing tool in Brain: {req}"
        assert req in brain._function_map, f"Missing function mapping for {req}"

    print(f"✅ All {len(required_tools)} new tools successfully registered and mapped in Brain!")


if __name__ == "__main__":
    print("=" * 60)
    print("🚀 RUNNING JARVIS JOB SEARCH & COLD MAILING TEST SUITE")
    print("=" * 60)

    test_profile_manager()
    test_linkedin_job_search()
    test_web_job_search()
    test_cold_email_workflow()
    test_outreach_tracker()
    test_brain_tool_registration()

    print("\n" + "=" * 60)
    print("🎉 ALL TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)
