import sys
import re
from collections import defaultdict

def main():
    if len(sys.argv) < 2:
        print("Usage: python check_onboarding_metrics.py <path_to_log_file>")
        print("Or pipe logs: cat app.log | python check_onboarding_metrics.py -")
        sys.exit(1)

    log_file = sys.argv[1]
    
    # Tracking counts
    accepted = defaultdict(int)
    rejected = defaultdict(int)
    
    # Regex to match the telemetry lines
    # Example lines:
    # [TELEMETRY-ONBOARDING] FIELD_ACCEPTED: field=pandit-phone | val=9876543210
    # [TELEMETRY-ONBOARDING] FIELD_REJECTED: field=pandit-phone | reason=invalid_format_digits | val=98765
    
    pattern = re.compile(r'\[TELEMETRY-ONBOARDING\] FIELD_(ACCEPTED|REJECTED): field=([a-zA-Z0-9-]+)')
    
    def process_file(f):
        for line in f:
            match = pattern.search(line)
            if match:
                status = match.group(1)
                field = match.group(2)
                
                if status == "ACCEPTED":
                    accepted[field] += 1
                elif status == "REJECTED":
                    rejected[field] += 1

    try:
        if log_file == "-":
            process_file(sys.stdin)
        else:
            with open(log_file, "r", encoding="utf-8", errors="replace") as f:
                process_file(f)
    except FileNotFoundError:
        print(f"Error: Log file '{log_file}' not found.")
        sys.exit(1)

    print("="*50)
    print("ONBOARDING FIELD TELEMETRY METRICS")
    print("="*50)
    
    fields = set(list(accepted.keys()) + list(rejected.keys()))
    if not fields:
        print("No telemetry logs found.")
        return

    for field in sorted(fields):
        acc = accepted[field]
        rej = rejected[field]
        total = acc + rej
        rej_rate = (rej / total * 100) if total > 0 else 0.0
        
        print(f"Field: {field}")
        print(f"  Accepted: {acc}")
        print(f"  Rejected: {rej}")
        print(f"  Total Attempts: {total}")
        print(f"  Rejection Rate: {rej_rate:.1f}%")
        print("-" * 50)
        
    print("Rollback Threshold Reminder: If Rejection Rate for phone/email > 25%, consider reverting DEFAULT_STT_PROVIDER.")
    print("="*50)

if __name__ == "__main__":
    main()
