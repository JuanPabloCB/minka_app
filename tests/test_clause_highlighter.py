from app.analysts.legal_analyst.clause_highlighter import ClauseHighlighter


def run_test():

    highlighter = ClauseHighlighter()

    clauses = [

        {
            "clause_id": 1,
            "text": "The client shall pay all invoices within 30 days.",
            "classification": {"type": "payment"},
            "risk": {"risk_level": "low"}
        },

        {
            "clause_id": 2,
            "text": "The provider shall not be liable for any damages.",
            "classification": {"type": "liability"},
            "risk": {"risk_level": "high"}
        }

    ]

    result = highlighter.highlight(clauses)

    print("\nHIGHLIGHT RESULTS\n")

    for clause in result:

        print("CLAUSE:", clause["clause_id"])
        print("COLOR:", clause["highlight"]["color"])
        print("REASON:", clause["highlight"]["reason"])
        print()


if __name__ == "__main__":
    run_test()