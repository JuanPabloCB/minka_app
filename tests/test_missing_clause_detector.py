from app.analysts.legal_analyst.missing_clause_detector import MissingClauseDetector


def run_test():
    detector = MissingClauseDetector()

    clauses = [
        {"classification": {"type": "scope_of_services", "confidence": 0.95}},
        {"classification": {"type": "payment", "confidence": 0.96}},
        {"classification": {"type": "duration", "confidence": 0.93}},
        {"classification": {"type": "termination", "confidence": 0.90}},
        {"classification": {"type": "liability", "confidence": 0.94}},
    ]

    result = detector.detect(clauses)

    print("\nMISSING CLAUSE DETECTOR TEST\n")
    print(result)


if __name__ == "__main__":
    run_test()