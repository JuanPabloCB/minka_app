from app.analysts.legal_analyst.semantic_clause_classifier import SemanticClauseClassifier


def run_test():

    classifier = SemanticClauseClassifier()

    classifier.initialize_reference_embeddings()

    clause = """
    The client agrees to pay all outstanding invoices within thirty days.
    """

    result = classifier.classify(clause)

    print("\nCLAUSE:")
    print(clause)

    print("\nCLASSIFICATION RESULT:")
    print(result)


if __name__ == "__main__":
    run_test()