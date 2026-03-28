from pprint import pprint

from app.analysts.legal_analyst.runtime_adapter import LegalAnalystRuntimeAdapter


def main():
    adapter = LegalAnalystRuntimeAdapter()

    result = adapter.execute(
        goal_type="critical_clause_detection",
        inputs={
            "document_id": "doc_test_001",
            "filename": "contrato_proveedor.pdf",
            "source": "orchestrator",
        },
        assigned_macro_steps=[
            {"id": "macro_1", "name": "Analizar cláusulas críticas"},
            {"id": "macro_2", "name": "Preparar contrato marcado"},
        ],
    )

    print("\n=== RESULTADO GENERAL ===")
    print("Analyst ID:", result.analyst_id)
    print("Goal Type:", result.goal_type)
    print("Selected Steps:", result.selected_steps)
    print("Ordered Steps:", result.ordered_steps)
    print("Planning Reasoning:")
    pprint(result.planning_reasoning)

    if result.dependency_errors:
        print("\n=== ERRORES DE DEPENDENCIAS ===")
        pprint(result.dependency_errors)

    if result.missing_dependencies:
        print("\n=== DEPENDENCIAS FALTANTES ===")
        pprint(result.missing_dependencies)

    if result.runtime_context:
        print("\n=== STEP RESULTS ===")
        for step_result in result.runtime_context.step_results:
            print(f"\n--- Step: {step_result.step_id} ---")
            print("Status:", step_result.status)
            print("Error:", step_result.error)
            pprint(step_result.output)

        print("\n=== SHARED STATE FINAL ===")
        pprint(result.runtime_context.shared_state)


if __name__ == "__main__":
    main()