import json
import time
import random
import os

def mock_system_call(query):
    """
    Mocks a call to the FundersAI /api/chat endpoint.
    In a real implementation, this would make an HTTP request 
    and return the parsed response.
    """
    # Simulate network latency
    latency_ms = random.randint(300, 1500)
    time.sleep(latency_ms / 1000.0)
    
    # Mocked response structure
    return {
        "text": f"Mocked response for: {query}",
        "workflow_used": random.choice(["stock_fundamentals", "hybrid_retrieval", "structured_comparison", "refusal", "security_refusal"]),
        "facts_included": ["Reliance Industries P/E", "HDFC Bank 1-year performance"], 
        "numerical_values": True,
        "citations": ["Source: Official AMC Document"],
        "refused": random.choice([True, False]),
        "latency_ms": latency_ms
    }

def evaluate_case(test_case, response):
    """
    Evaluates the response against the test case criteria.
    In a real harness, this would use exact-match, regex, or an LLM-as-a-judge.
    """
    # 1. Routing Correct
    routing_correct = (response["workflow_used"] == test_case.get("expected_workflow"))
    
    # 2. Required Facts Present
    # Mock logic: true if no facts required, or if we mock a match
    required_facts = test_case.get("expected_facts", [])
    facts_present = True if not required_facts else random.choice([True, False])
    
    # 3. Numerical Values Correct
    # Mock logic: assume true if the response flagged numerical_values
    numerical_values_correct = response["numerical_values"]
    
    # 4. Citations Present
    citations_present = len(response["citations"]) > 0
    
    # 5. Refusal Correct
    expected_refusal = test_case.get("should_refuse", False)
    actual_refusal = response["refused"]
    refusal_correct = (expected_refusal == actual_refusal)
    
    return {
        "id": test_case["id"],
        "intent": test_case["intent"],
        "routing_correct": routing_correct,
        "required_facts_present": facts_present,
        "numerical_values_correct": numerical_values_correct,
        "citations_present": citations_present,
        "refusal_correct": refusal_correct,
        "latency_ms": response["latency_ms"]
    }

def print_results_table(results):
    """
    Prints a formatted ASCII table of the evaluation results.
    """
    print(f"{'ID':<4} | {'Intent':<20} | {'Routing':<8} | {'Facts':<6} | {'Numbers':<8} | {'Citations':<10} | {'Refusal':<8} | {'Latency (ms)':<12}")
    print("-" * 100)
    
    total = len(results)
    passed_routing = 0
    passed_facts = 0
    passed_refusal = 0
    total_latency = 0
    
    for r in results:
        print(f"{r['id']:<4} | {r['intent'][:18]:<20} | "
              f"{str(r['routing_correct']):<8} | "
              f"{str(r['required_facts_present']):<6} | "
              f"{str(r['numerical_values_correct']):<8} | "
              f"{str(r['citations_present']):<10} | "
              f"{str(r['refusal_correct']):<8} | "
              f"{r['latency_ms']:<12}")
        
        passed_routing += int(r['routing_correct'])
        passed_facts += int(r['required_facts_present'])
        passed_refusal += int(r['refusal_correct'])
        total_latency += r['latency_ms']
        
    print("-" * 100)
    print(f"Summary Metrics:")
    print(f"Total Queries: {total}")
    print(f"Routing Accuracy: {passed_routing/total*100:.1f}%")
    print(f"Fact Retrieval Accuracy: {passed_facts/total*100:.1f}%")
    print(f"Safety/Refusal Accuracy: {passed_refusal/total*100:.1f}%")
    print(f"Average Latency: {total_latency/total:.1f} ms")

def main():
    dataset_path = os.path.join(os.path.dirname(__file__), 'eval_dataset.json')
    
    if not os.path.exists(dataset_path):
        print(f"Error: Dataset not found at {dataset_path}")
        return
        
    with open(dataset_path, 'r') as f:
        test_cases = json.load(f)
        
    print(f"Loaded {len(test_cases)} test cases. Starting evaluation harness...\n")
    
    results = []
    for case in test_cases:
        # 1. Run the query
        response = mock_system_call(case["query"])
        
        # 2. Evaluate the response
        eval_result = evaluate_case(case, response)
        results.append(eval_result)
        
    # 3. Print the results table
    print_results_table(results)

if __name__ == "__main__":
    main()
