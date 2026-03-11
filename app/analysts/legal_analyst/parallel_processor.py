"""
DEPRECATED:
This module belongs to an older legal analysis flow and should not be used
as the main path for the current Legal Analyst architecture.
"""


from concurrent.futures import ThreadPoolExecutor


class ParallelClauseProcessor:

    def __init__(self, max_workers: int = 10):
        self.max_workers = max_workers

    def process(self, clauses, process_function):

        results = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:

            futures = [
                executor.submit(process_function, clause)
                for clause in clauses
            ]

            for future in futures:
                results.append(future.result())

        return results