from minio import Minio
from minio.error import S3Error

candidates = [
    ("admin", "12345678", "Configured in .env"),
    ("minioadmin", "minioadmin", "Default MinIO"),
    ("QfIx8FgdpgKtmbFMbKVb", "DsitWZJT3pecrg020Y2NKCETVpsIc3h2PrKTqONA", "Docker Compose Fallback"),
]

endpoint = "localhost:19000"

print(f"Testing MinIO connection at {endpoint}...")

for ak, sk, desc in candidates:
    print(f"\nTesting credentials: {desc} ({ak} / ***)")
    client = Minio(
        endpoint,
        access_key=ak,
        secret_key=sk,
        secure=False
    )
    try:
        buckets = client.list_buckets()
        print(f"✅ SUCCESS! Found {len(buckets)} buckets.")
        for b in buckets:
            print(f" - {b.name}")
    except S3Error as e:
        print(f"❌ FAILED (S3Error): {e}")
    except Exception as e:
        # print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
