from app.analysts.legal_analyst.clause_explainer import ClauseExplainer


def run_test():

    explainer = ClauseExplainer()

    clause = {
        "clause_id": 1,
        "text": "Either party may terminate this agreement without prior notice."
    }

    result = explainer.explain(clause)

    print("\nCLAUSE:")
    print(clause["text"])

    print("\nEXPLANATION:")
    print(result["explanation"])


if __name__ == "__main__":
    run_test()