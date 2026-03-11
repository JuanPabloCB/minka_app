from app.analysts.legal_analyst.semantic_clause_classifier import SemanticClauseClassifier


def run_test():
    classifier = SemanticClauseClassifier()

    test_cases = [
        "The Client shall pay all invoices within thirty (30) days from the invoice date.",
        "Either party may terminate this Agreement with thirty (30) days written notice.",
        "All confidential information shall remain strictly confidential.",
        "This Agreement shall be governed by the laws of New York.",
        "Neither party shall be liable for indirect or consequential damages.",
        "Any dispute shall be resolved by arbitration.",
        "The services to be provided are described in Annex A.",
        "This Agreement shall remain in force for twelve (12) months."
    ]

    print("\nSEMANTIC CLAUSE CLASSIFIER TEST\n")

    for i, clause in enumerate(test_cases, start=1):
        result = classifier.classify(clause)
        print(f"CASE {i}")
        print("CLAUSE:", clause)
        print("RESULT:", result)
        print("-" * 50)


if __name__ == "__main__":
    run_test()