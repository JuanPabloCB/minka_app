from pprint import pprint

from app.services.legal_analyst_service import LegalAnalystService


def main():
    service = LegalAnalystService()

    result = service.execute_analysis(
        goal_type="critical_clause_detection",
        inputs={
            "document_id": "doc_service_001",
            "filename": "contrato_cliente.pdf",
            "source": "orchestrator",
        },
        assigned_macro_steps=[
            {"id": "macro_1", "name": "Analizar cláusulas críticas"},
            {"id": "macro_2", "name": "Preparar contrato marcado"},
        ],
    )

    print("\n=== RESULTADO DEL SERVICE ===")
    pprint(result)


if __name__ == "__main__":
    main()