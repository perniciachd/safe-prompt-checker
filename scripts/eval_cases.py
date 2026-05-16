"""
Eval test cases for SAFE detection.

Each case is a dict with:
- id: unique identifier for the test
- name: human-readable name
- prompt: the user prompt to send to /analyse
- expected_categories: set of category strings the detector SHOULD flag
- expected_risk_score: integer risk score from PROMPT_DESIGN.md ground truth

Cases sourced from docs/PROMPT_DESIGN.md sections 6.1, 6.2, 6.3.

Note: These ground truths were established against Claude. The current
production model is gpt-4.1-mini. Score gaps vs ground truth are expected
and should be recorded as the baseline, not retrofitted.
"""

EVAL_CASES = [
    {
        "id": "test_1_wealth_mgmt",
        "name": "Wealth Management Portfolio Review",
        "prompt": (
            "Help me draft a quarterly portfolio review note for our client "
            "Anand Sharma, account number WM-44721. His current AUM is 18.5 "
            "crores, with 62% in mid-cap equity, 23% in debt, and 15% in "
            "alternatives. He's expressed concern about the recent drawdown "
            "in his Kotak Emerging Equity allocation which is down 14% YTD. "
            "Suggest a rebalancing approach for our next review meeting on "
            "the 18th."
        ),
        "expected_categories": {
            "personal_identifiers",
            "client_account_information",
        },
        "expected_risk_score": 9,
    },
    {
        "id": "test_2_ma_advisory",
        "name": "M&A Deal Advisory",
        "prompt": (
            "Draft a confidential information memorandum section on synergies "
            "for Project Tigris. The acquirer is Tata Consumer Products and "
            "the target is Hatsun Agro. Deal size is approximately 8,400 "
            "crores at an EV/EBITDA of 22x. We expect to announce on November "
            "14th. Focus on distribution synergies in South India and "
            "procurement consolidation."
        ),
        "expected_categories": {
            "deal_and_corporate_finance_information",
        },
        "expected_risk_score": 10,
    },
    {
        "id": "test_3_compensation",
        "name": "Compensation Analysis",
        "prompt": (
            "I need to prepare a compensation benchmarking analysis for our "
            "equity research team. Specifically: Rohan Iyer (VP, Auto Sector) "
            "currently at 1.85 cr fixed plus 60 lakh variable; Meera Krishnan "
            "(AVP, Banking) at 1.2 cr fixed plus 45 lakh variable; and our "
            "new senior hire from Morgan Stanley joining at 2.4 cr fixed. "
            "Compare to market data and suggest revised bands."
        ),
        "expected_categories": {
            "personal_identifiers",
            "compensation_data",
        },
        "expected_risk_score": 9,
    },
]