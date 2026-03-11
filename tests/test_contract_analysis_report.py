from app.analysts.legal_analyst.contract_analysis_report import ContractAnalysisReport


def run_test():

    clauses = [

        {
            "clause_id": 1,
            "text": "Client shall pay within 30 days",
            "classification": {"type": "payment"},
            "risk": {"risk_level": "low"}
        },

        {
            "clause_id": 2,
            "text": "Provider is not liable for damages",
            "classification": {"type": "liability"},
            "risk": {"risk_level": "high"}
        }

    ]

    report_generator = ContractAnalysisReport()

    report = report_generator.generate(clauses)

    print("\nCONTRACT ANALYSIS REPORT\n")

    print(report)


if __name__ == "__main__":
    run_test()