from app.analysts.legal_analyst.pipeline import LegalAnalysisPipeline


def run_test():

    pipeline = LegalAnalysisPipeline()

    result = pipeline.run("sample_contract.txt")

    print("\n===================================")
    print("LEGAL ANALYSIS RESULT")
    print("===================================")

    print("\nTOTAL CLAUSES:", result["total_clauses"])

    for clause in result["clauses"]:

        print("\n-----------------------------------")
        print("CLAUSE ID:", clause["clause_id"])

        if "classification" in clause:
            print("TYPE:", clause["classification"])

        print("TEXT:")
        print(clause["text"])


if __name__ == "__main__":
    run_test()