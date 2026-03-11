from app.analysts.legal_analyst.legal_analysis_engine import LegalAnalysisEngine


def run_test():
    engine = LegalAnalysisEngine()

    file_path = "sample_contract.txt"
    result = engine.analyze_contract(file_path)

    print("\nLEGAL ANALYSIS RESULT\n")
    print("STATUS:", result["status"])
    print("DOCUMENT:", result["document_name"])
    print("TOTAL CLAUSES:", result["total_clauses"])
    print("\nMISSING CLAUSE ANALYSIS:")
    print(result["missing_clause_analysis"])
    print("\nREPORT:")
    print(result["report"])

    print("\nCLAUSE DETAILS:\n")

    for clause in result["clauses"]:
        print("-----------------------------")
        print("CLAUSE ID:", clause["clause_id"])
        print("TITLE:", clause["title"])
        print("TEXT:", clause["text"])
        print("CLASSIFICATION:", clause["classification"])
        print("RISK:", clause["risk"])
        print("EXPLANATION:", clause["explanation"])
        print("HIGHLIGHT:", clause["highlight"])


if __name__ == "__main__":
    run_test()