class BaseAnalyst:
    name = "base_analyst"

    def run(self, inputs: dict):
        raise NotImplementedError("Analyst must implement run()")

    def validate_inputs(self, inputs: dict):
        return inputs

    def format_output(self, result: dict):
        return result