from app.analysts.legal_analyst.clause_segmenter import ClauseSegmenter


def run_test():
    segmenter = ClauseSegmenter()

    sample_text = """
SERVICES
The Provider shall perform the services described in Annex A.

PAYMENT TERMS
The Client shall pay all invoices within fifteen (15) days.

CONFIDENTIALITY
Both parties shall keep confidential all proprietary information.

Section 4 Termination
Either party may terminate this Agreement with thirty (30) days written notice.

LIMITATION OF LIABILITY
Neither party shall be liable for indirect or consequential damages.

Governing Law
This Agreement shall be governed by the laws of New York.
"""

    clauses = segmenter.segment(sample_text)

    print("\nADVANCED CLAUSE SEGMENTER TEST\n")
    print("TOTAL DETECTED:", len(clauses))
    print()

    for clause in clauses:
        print(clause)
        print("-" * 60)


if __name__ == "__main__":
    run_test()