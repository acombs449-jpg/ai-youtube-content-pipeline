"""One-off: generate a SINGLE AI B-roll clip to sanity-check quality and real
cost before committing to a full video (which uses 6-18 clips). Costs one
clip's worth: 8s x $0.12/s = ~$0.96.

Usage: python test_runway.py "person budgeting laptop"
"""
import sys
import config
from pipeline import runway

keyword = sys.argv[1] if len(sys.argv) > 1 else "person budgeting on laptop, cozy home office"
out = config.OUTPUT / "runway_test_clip.mp4"

print(f"Generating one test clip for: '{keyword}'")
print(f"Model: {runway.MODEL}  |  Expected cost: ~${8 * runway.PRICE_PER_SECOND:.2f} (8s)")
print("(this takes anywhere from ~30s to a few minutes)\n")

result = runway.generate_clip(keyword, out, orientation="landscape")
if result:
    print(f"\nSUCCESS -> {result}")
    print("Open it and check quality before enabling Runway for any format in config.py.")
else:
    print("\nFAILED — see the error above. Check RUNWAY_API_KEY in .env.")
