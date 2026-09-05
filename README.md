TRACK_ID=PS04
# SupportPilot AI

SupportPilot AI is a hackathon project for PS04 — Customer Support Resolution Assistant.

It helps a support agent analyze a customer issue using:

- Local sample account data
- Local support articles
- Deterministic keyword-based retrieval
- Safety and escalation rules
- Gemini only when a request is appropriate for AI-assisted drafting

## Architecture

```text
Customer message
        ↓
Flask POST /analyze
        ↓
Input validation
        ↓
Local account lookup
        ↓
Deterministic local article retrieval
        ↓
Safety and routing decision
        ↓
Gemini only when appropriate
        ↓
Response and evidence validation
        ↓
Structured JSON response
        ↓
Frontend support-agent dashboard