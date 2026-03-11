# Legal Analyst

## Canonical architecture

Main modules:
- parser.py
- clause_segmenter.py
- semantic_clause_classifier.py
- risk_clause_detector.py
- missing_clause_detector.py
- clause_explainer.py
- clause_highlighter.py
- contract_analysis_report.py
- prompt_framework.py
- schemas.py
- legal_analysis_engine.py
- legal_task_planner.py
- legal_executor.py

## Main entry points

- Full analysis:
  - `LegalAnalysisEngine.analyze_contract(file_path)`

- Dynamic execution:
  - `LegalTaskPlanner.create_plan(goal)`
  - `LegalExecutor.execute(plan, file_path)`

## Notes

- The current architecture prioritizes a balanced tradeoff between precision, speed, and cost.
- Risk detection uses a hybrid strategy: deterministic rules + selective AI analysis.
- Some old modules may still exist in this folder, but they are deprecated and should not be used as the primary path.