import requests
import random
from datetime import datetime, timedelta

BASE_URL = "http://localhost:5000"

def run_enhanced_fuzz_test():
    print("🧹 Clearing data and generating 100 workers...")
    requests.post(f"{BASE_URL}/api/clear-all")
    
    # Track rates locally to compare later
    all_rates = []
    skills_pool = ["ICU", "ER", "General"]

    for i in range(100):
        rate = float(random.randint(15, 60))
        all_rates.append(rate)
        worker = {
            "name": f"Worker_{i}",
            "staff_id": i + 1000,
            "seniority_level": 4 if rate > 45 else 1,
            "hourly_rate": rate,
            "skills": [random.choice(skills_pool)],
            "max_shifts_per_week": 5
        }
        requests.post(f"{BASE_URL}/api/workers", json=worker)

    # Generate 10 shifts
    for i in range(10):
        shift = {
            "date": "2026-04-01",
            "start_time": "08:00",
            "end_time": "16:00",
            "workers_required": 1,
            "required_skills": [random.choice(skills_pool)]
        }
        requests.post(f"{BASE_URL}/api/shifts", json=shift)

    print("🎯 Solving with high 'Minimize Compensation' weight...")
    payload = {
        "top_k": 1,
        "weights": {"minimize_compensation": 50.0, "reward_skill_matching": 10.0}
    }
    
    response = requests.post(f"{BASE_URL}/api/schedule", json=payload).json()
    workers_api = requests.get(f"{BASE_URL}/api/workers").json()
    rate_map = {w['id']: w['hourly_rate'] for w in workers_api}

    # --- COST REPORTING ---
    if "solutions" in response:
        sol = response['solutions'][0]
        assigned_rates = [rate_map[a['worker_id']] for a in sol['assignments']]
        
        avg_pool_rate = sum(all_rates) / len(all_rates)
        avg_assigned_rate = sum(assigned_rates) / len(assigned_rates)
        total_cost = sum(assigned_rates) * 8 # 8 hour shifts

        print("\n" + "="*30)
        print("💰 FINANCIAL COST REPORT")
        print("="*30)
        print(f"Global Avg Rate:   ${avg_pool_rate:.2f}/hr")
        print(f"AI Assigned Avg:   ${avg_assigned_rate:.2f}/hr")
        print(f"Total Daily Cost:  ${total_cost:.2f}")
        print("-" * 30)
        
        if avg_assigned_rate < avg_pool_rate:
            print("✅ SUCCESS: AI successfully prioritized cheaper workers.")
        else:
            print("⚠️ NOTE: Constraints (like skills) forced higher-cost assignments.")
        print("="*30)

if __name__ == "__main__":
    run_enhanced_fuzz_test()