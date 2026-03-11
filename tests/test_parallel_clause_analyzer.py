import time

from app.analysts.legal_analyst.parallel_clause_analyzer import ParallelClauseAnalyzer


def fake_analysis(clause):

    time.sleep(0.2)

    return {
        "clause_id": clause["clause_id"],
        "result": "analyzed"
    }


def run_test():

    clauses = []

    for i in range(20):
        clauses.append({"clause_id": i})

    analyzer = ParallelClauseAnalyzer(max_workers=5)

    start = time.time()

    results = analyzer.process(clauses, fake_analysis)

    end = time.time()

    print("\nRESULTS:")
    print(results)

    print("\nTIME:", end - start)


if __name__ == "__main__":
    run_test()