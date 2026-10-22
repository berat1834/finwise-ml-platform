import hashlib
import uuid

# Test route_key generation and bucketing
print("Testing SHA256 bucketing distribution:\n")
print(f"{'Request':<10} {'route_key':<40} {'bucket':<10}")
print("=" * 60)

for i in range(20):
    # Simple key
    key1 = f"user_{i:03d}"
    bucket1 = int(hashlib.sha256(key1.encode()).hexdigest()[:8], 16) % 100
    
    # With UUID (simulating per-request)
    key2 = f"user_{i:03d}_{uuid.uuid4().hex[:8]}"
    bucket2 = int(hashlib.sha256(key2.encode()).hexdigest()[:8], 16) % 100
    
    print(f"{i:<10} {key1:<40} {bucket1:<10}")
    print(f"{'':10} {key2:<40} {bucket2:<10}")

# Analysis
buckets_simple = []
buckets_uuid = []

for i in range(100):
    key = f"user_{i:03d}"
    b = int(hashlib.sha256(key.encode()).hexdigest()[:8], 16) % 100
    buckets_simple.append(b)
    
    key_uuid = f"user_{i:03d}_{uuid.uuid4().hex[:8]}"
    b_uuid = int(hashlib.sha256(key_uuid.encode()).hexdigest()[:8], 16) % 100
    buckets_uuid.append(b_uuid)

print("\n" + "=" * 60)
print("Analysis of 100 requests:")
print(f"Simple key - Min: {min(buckets_simple)}, Max: {max(buckets_simple)}, Avg: {sum(buckets_simple)/len(buckets_simple):.1f}")
print(f"UUID key   - Min: {min(buckets_uuid)}, Max: {max(buckets_uuid)}, Avg: {sum(buckets_uuid)/len(buckets_uuid):.1f}")
print(f"\nCanary-eligible (<50) with CANARY_PERCENT=50:")
print(f"Simple key: {sum(1 for b in buckets_simple if b < 50)}/100 = {sum(1 for b in buckets_simple if b < 50)}%")
print(f"UUID key:   {sum(1 for b in buckets_uuid if b < 50)}/100 = {sum(1 for b in buckets_uuid if b < 50)}%")
