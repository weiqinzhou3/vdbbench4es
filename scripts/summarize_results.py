import json
from pathlib import Path

def summarize():
    project_root = Path(__file__).parent.parent.resolve()
    results_path = project_root / "outputs" / "results" / "smoke_results.json"
    if not results_path.exists():
        print("No results found.")
        return
    
    with open(results_path, "r") as f:
        results = json.load(f)
    
    print("\n" + "="*50)
    print("VDBBench Smoke Test Summary")
    print("="*50)
    
    for name, metric in results.items():
        if metric is None:
            print(f"Dataset: {name} -> FAILED")
            continue
            
        print(f"Dataset: {name}")
        print(f"  Load Duration:    {metric.get('load_duration')}s")
        print(f"  Recall:           {metric.get('recall')}")
        print(f"  P99 Latency:      {metric.get('serial_latency_p99')}s")
        print(f"  QPS:              {metric.get('qps')}")
        print("-" * 30)

if __name__ == "__main__":
    summarize()
