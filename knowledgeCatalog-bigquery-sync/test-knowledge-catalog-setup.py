"""test-knowledge-catalog-setup.py

Validates that knowledge-catalog-setup.py successfully created the Entry Group,
Entries, and Aspects in Google Cloud Dataplex Universal Catalog.
"""

from __future__ import annotations

import os
import sys
from google.cloud import dataplex_v1
from google.api_core.exceptions import NotFound

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")
ENTRY_GROUP_ID = "google-analytics-catalog"

if not PROJECT_ID:
    print("❌ Error: Set the GOOGLE_CLOUD_PROJECT environment variable.")
    print("Run: export GOOGLE_CLOUD_PROJECT=$(gcloud config get-value project)")
    sys.exit(1)

client = dataplex_v1.CatalogServiceClient()
parent_location = f"projects/{PROJECT_ID}/locations/{LOCATION}"
entry_group_path = f"{parent_location}/entryGroups/{ENTRY_GROUP_ID}"

print(f"Starting verification against GCP project: {PROJECT_ID} [{LOCATION}]\n")
failures = 0

# -----------------------------------------------------------------------------
# 1. Test Entry Group Existence
# -----------------------------------------------------------------------------
print("Test 1: Verifying Dataplex Entry Group...")
try:
    group = client.get_entry_group(name=entry_group_path)
    print(f"  ✅ Found Entry Group: {group.name.split('/')[-1]}")
    if group.description:
        print(f"     • Description: {group.description}")
except NotFound:
    print(f"  ❌ FAILED: Entry Group '{ENTRY_GROUP_ID}' does not exist.")
    failures += 1
except Exception as e:
    print(f"  ❌ Error reading Entry Group: {e}")
    failures += 1

# -----------------------------------------------------------------------------
# 2. Test Catalog Entries, Descriptions & Required Aspects
# -----------------------------------------------------------------------------
print("\nTest 2: Verifying Seeded Dataplex Entries & Aspects...")
expected_entries = [
    "ga-sessions-table-spec",
    "bounce-rate",
    "monthly-active-users",
]

for entry_id in expected_entries:
    entry_path = f"{entry_group_path}/entries/{entry_id}"
    try:
        request = dataplex_v1.GetEntryRequest(
            name=entry_path,
            view=dataplex_v1.EntryView.FULL,
        )
        entry = client.get_entry(request=request)
        print(f"\n  ✅ Found Entry: {entry_id}")
        
        # Verify entry_source metadata
        if entry.entry_source:
            print(f"     • Display Name: {entry.entry_source.display_name}")
            print(f"     • System:       {entry.entry_source.system}")
            print(f"     • Description:  {entry.entry_source.description[:75]}...")
        else:
            print(f"     ❌ FAILED: Missing entry_source on '{entry_id}'.")
            failures += 1

        # Check for the generic aspect (using either canonical project number or alias)
        matched_key = None
        for key in ["655216118709.global.generic", "dataplex-types.global.generic"]:
            if key in entry.aspects:
                matched_key = key
                break

        if matched_key:
            aspect_data = entry.aspects[matched_key].data
            # Treat MapComposite as a Python dictionary
            type_val = aspect_data.get("type", "N/A") if hasattr(aspect_data, "get") else "N/A"
            system_val = aspect_data.get("system", "N/A") if hasattr(aspect_data, "get") else "N/A"
            print(f"     • Aspect '{matched_key}': OK (type='{type_val}', system='{system_val}')")
        else:
            print(f"     ❌ FAILED: Missing generic aspect. Found: {list(entry.aspects.keys())}")
            failures += 1

    except NotFound:
        print(f"  ❌ FAILED: Entry '{entry_id}' was not found in Dataplex.")
        failures += 1
    except Exception as e:
        print(f"  ❌ Error reading entry '{entry_id}': {e}")
        failures += 1

# -----------------------------------------------------------------------------
# Summary Report
# -----------------------------------------------------------------------------
print("\n" + "=" * 60)
if failures == 0:
    print("🎉 ALL TESTS PASSED! Knowledge Catalog is ready for the MCP Server.")
    sys.exit(0)
else:
    print(f"❌ Completed with {failures} error(s). Please review the logs above.")
    sys.exit(1)