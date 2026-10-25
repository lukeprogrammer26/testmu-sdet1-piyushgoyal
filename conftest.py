import os
import pytest
from google import genai
from dotenv import load_dotenv

load_dotenv()

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Pytest hook to capture test failures, query LLM API, and attach explanation."""
    outcome = yield
    report = outcome.get_result()
    
    if report.when == "call" and report.failed:
        # Extract test failure information
        error_message = str(report.longrepr)
        test_name = item.name
        
        # Capture page state or snippet if Playwright page fixture is available
        page_content = "DOM state unavailable"
        if "page" in item.funcargs:
            page = item.funcargs["page"]
            try:
                page_content = page.content()[:3000] # Truncate for token efficiency
            except Exception:
                pass

        # Real LLM API Call (Google GenAI SDK)
        try:
            client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
            prompt = f"""
            You are an expert AI SDET failure analyzer. A Playwright test failed.
            Test Name: {test_name}
            Error Trace: {error_message}
            Page HTML Snippet: {page_content}
            
            Provide:
            1. Plain English explanation of what broke.
            2. A suggested code or locator fix.
            Keep it concise and actionable for QA engineers.
            """
            
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            llm_analysis = response.text
        except Exception as e:
            llm_analysis = f"Failed to fetch LLM analysis due to API error: {str(e)}"

        # Attach analysis to test report extra info
        report.sections.append(("🤖 AI Failure Explainer Analysis", llm_analysis))