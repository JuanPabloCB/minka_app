from app.analysts.legal_analyst.document_structure_analyzer import DocumentStructureAnalyzer


def run_test():

    analyzer = DocumentStructureAnalyzer()

    sample = """
1. Definitions
2. Scope of Services
3. Payment
3.1 Fees
3.2 Invoicing
4. Termination
4.1 Termination for Cause
4.2 Termination for Convenience
"""

    structure = analyzer.detect_structure(sample)

    print("\nDETECTED STRUCTURE\n")

    for item in structure:
        print(item)


if __name__ == "__main__":
    run_test()