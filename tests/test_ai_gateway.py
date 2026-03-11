from app.core.ai_gateway import AIGateway


def run_test():

    gateway = AIGateway()

    prompt = """
    Explain this legal clause in simple language:

    Either party may terminate this agreement without prior notice.
    """

    result = gateway.generate(prompt)

    print("\nAI RESPONSE\n")
    print(result)


if __name__ == "__main__":
    run_test()