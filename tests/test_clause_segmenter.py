from app.analysts.legal_analyst.clause_segmenter import ClauseSegmenter


def run_test():
    segmenter = ClauseSegmenter()

    sample_text = """
1. Scope of Services
The Service Provider shall provide consulting services.

2. Payment Terms
The Client shall pay invoices within thirty (30) days.

3. Termination
Either party may terminate with written notice.
"""

    clauses = segmenter.segment(sample_text)

    print("\nCLAUSE SEGMENTER TEST\n")
    for clause in clauses:
        print(clause)
        print("-" * 50)


if __name__ == "__main__":
    run_test()