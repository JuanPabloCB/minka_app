from app.analysts.legal_analyst.risk_clause_detector import RiskClauseDetector


def run_test():
    detector = RiskClauseDetector()

    test_cases = [
        {
            "clause_text": "The Service Provider shall be liable for any damages without limitation.",
            "clause_type": "liability"
        },
        {
            "clause_text": "Either party may terminate this Agreement with thirty (30) days written notice.",
            "clause_type": "termination"
        },
        {
            "clause_text": "The Client may terminate this Agreement at any time without notice.",
            "clause_type": "termination"
        },
        {
            "clause_text": "All intellectual property created during the course of the services shall belong to the Client.",
            "clause_type": "intellectual_property"
        },
        {
            "clause_text": "This Agreement shall be governed by the laws of the jurisdiction where the Client's headquarters are located.",
            "clause_type": "governing_law"
        },
        {
            "clause_text": "Payments shall be made within fifteen (15) days after receipt of the invoice. Late payments may be subject to interest at a rate of 1.5% per month.",
            "clause_type": "payment"
        }
    ]

    print("\nRISK CLAUSE DETECTOR TEST\n")

    for i, case in enumerate(test_cases, start=1):
        result = detector.detect(case["clause_text"], case["clause_type"])
        print(f"CASE {i}")
        print("CLAUSE TYPE:", case["clause_type"])
        print("CLAUSE:", case["clause_text"])
        print("RESULT:", result)
        print("-" * 50)


if __name__ == "__main__":
    run_test()