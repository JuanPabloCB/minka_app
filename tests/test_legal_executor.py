from app.analysts.legal_analyst.legal_task_planner import LegalTaskPlanner
from app.analysts.legal_analyst.legal_executor import LegalExecutor


def run_test():
    planner = LegalTaskPlanner()
    executor = LegalExecutor()

    goal = "Highlight critical clauses and generate a report"
    plan = planner.create_plan(goal)

    print("\nLEGAL TASK PLANNER TEST\n")
    print("GOAL:", goal)
    print("PLAN:", plan)

    result = executor.execute(plan, "sample_contract.txt")

    print("\nLEGAL EXECUTOR TEST\n")
    print("STATUS:", result["status"])
    print("DOCUMENT:", result["document_name"])
    print("PLAN:", result["plan"])
    print("AVAILABLE KEYS:", list(result.keys()))

    if "report" in result:
        print("\nREPORT:")
        print(result["report"])

    if "clauses" in result:
        print("\nTOTAL CLAUSES IN CONTEXT:", len(result["clauses"]))
        print("\nFIRST CLAUSE SAMPLE:")
        print(result["clauses"][0])


if __name__ == "__main__":
    run_test()