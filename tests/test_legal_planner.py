from app.analysts.legal_analyst.legal_task_planner import LegalTaskPlanner


def run_test():

    planner = LegalTaskPlanner()

    goal = "highlight payment clauses"

    plan = planner.create_plan(goal)

    print("\nGOAL:")
    print(goal)

    print("\nPLAN:")
    for step in plan:
        print("-", step)


if __name__ == "__main__":
    run_test()