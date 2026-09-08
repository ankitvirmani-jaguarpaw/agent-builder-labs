"""knowledge-catalog-setup.py

First-time setup script to synchronize BigQuery Google Analytics metadata
and semantic definitions into Google Cloud Dataplex Universal Catalog.
"""

from __future__ import annotations

import os
import sys
from google.api_core.exceptions import AlreadyExists
from google.cloud import bigquery
from google.cloud import dataplex_v1
from google.protobuf import struct_pb2

# -----------------------------------------------------------------------------
# 1. Configuration & Validation
# -----------------------------------------------------------------------------
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")
ENTRY_GROUP_ID = "google-analytics-catalog"

if not PROJECT_ID:
    print("❌ Error: GOOGLE_CLOUD_PROJECT environment variable is required.")
    print("Run: export GOOGLE_CLOUD_PROJECT=$(gcloud config get-value project)")
    sys.exit(1)

print("===================================================================")
print(" Initializing Google Cloud Knowledge Catalog (Dataplex)")
print(f" Project:  {PROJECT_ID}")
print(f" Location: {LOCATION}")
print("===================================================================\n")

# Initialize Dataplex and BigQuery clients
dataplex_client = dataplex_v1.CatalogServiceClient()
bq_client = bigquery.Client(project=PROJECT_ID)

parent_location = f"projects/{PROJECT_ID}/locations/{LOCATION}"
entry_group_name = f"{parent_location}/entryGroups/{ENTRY_GROUP_ID}"

# Google Cloud's universal generic entry & aspect type
GENERIC_ENTRY_TYPE = "projects/dataplex-types/locations/global/entryTypes/generic"
GENERIC_ASPECT_TYPE = "projects/dataplex-types/locations/global/aspectTypes/generic"
ASPECT_KEY = "dataplex-types.global.generic"

# -----------------------------------------------------------------------------
# 2. Create the Dataplex Entry Group
# -----------------------------------------------------------------------------
print("=== Step 1: Ensuring Dataplex Entry Group Exists ===")
entry_group = dataplex_v1.EntryGroup(
    description="Houses GA semantic definitions, metric logic, and schema guides."
)

try:
    operation = dataplex_client.create_entry_group(
        parent=parent_location,
        entry_group=entry_group,
        entry_group_id=ENTRY_GROUP_ID,
    )
    print(f"[*] Provisioning Entry Group '{ENTRY_GROUP_ID}'...")
    if hasattr(operation, "result"):
        operation.result()
    print(f"[✓] Created Entry Group: {entry_group_name}")
except AlreadyExists:
    print(f"[*] Entry Group already exists: {entry_group_name}")
except Exception as e:
    print(f"[*] Note on Entry Group: {e}")

# -----------------------------------------------------------------------------
# 3. Read Live Schema from BigQuery Public Dataset
# -----------------------------------------------------------------------------
print("\n=== Step 2: Fetching Live Schema from BigQuery ===")
bq_source_table = "bigquery-public-data.google_analytics_sample.ga_sessions_20170801"
print(f"Connecting to BigQuery table: {bq_source_table}...")

try:
    bq_table = bq_client.get_table(bq_source_table)
    print(f"[✓] Table found: {len(bq_table.schema)} columns detected, {bq_table.num_rows:,} total rows.")
except Exception as e:
    print(f"❌ Failed to read from BigQuery: {e}")
    sys.exit(1)

# -----------------------------------------------------------------------------
# 4. Populate Knowledge Catalog Entries with Required Aspect
# -----------------------------------------------------------------------------
print("\n=== Step 3: Creating Semantic Entries in Dataplex Catalog ===")
ENTRIES_TO_CREATE = [
    {
        "entry_id": "ga-sessions-table-spec",
        "display_name": "GA Sessions Table Spec",
        "type": "table_specification",
        "description": (
            f"Synced from {bq_source_table}. "
            f"Partition Key: _TABLE_SUFFIX (format: YYYYMMDD). "
            f"Total rows in sample shard: {bq_table.num_rows:,}. "
            "Optimization: Always filter by _TABLE_SUFFIX to avoid costly full-table scans."
        ),
    },
    {
        "entry_id": "bounce-rate",
        "display_name": "Bounce Rate Metric",
        "type": "metric",
        "description": (
            "Definition: Percentage of visitors who enter the site and bounce without further actions. "
            "Calculation Formula: COUNTIF(totals.bounces = 1) / COUNT(totals.visits). "
            "Canonical SQL: SUM(IFNULL(totals.bounces, 0)) / COUNT(totals.visits)."
        ),
    },
    {
        "entry_id": "monthly-active-users",
        "display_name": "Monthly Active Users Metric",
        "type": "metric",
        "description": (
            "Definition: Count of unique active visitors over a rolling 30-day window. "
            "Calculation Formula: COUNT(DISTINCT fullVisitorId). "
            "Canonical SQL: COUNT(DISTINCT fullVisitorId) WHERE _TABLE_SUFFIX >= FORMAT_DATE('%Y%m%d', DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY))."
        ),
    },
]

for item in ENTRIES_TO_CREATE:
    # Build the required generic aspect
    required_aspect = dataplex_v1.Aspect(
        aspect_type=GENERIC_ASPECT_TYPE,
        data=struct_pb2.Struct(
            fields={
                "type": struct_pb2.Value(string_value=item["type"]),
                "system": struct_pb2.Value(string_value="bigquery"),
            }
        ),
    )

    entry = dataplex_v1.Entry(
        entry_type=GENERIC_ENTRY_TYPE,
        entry_source=dataplex_v1.EntrySource(
            display_name=item["display_name"],
            description=item["description"],
            system="bigquery_semantic_layer",
        ),
        aspects={
            ASPECT_KEY: required_aspect
        },
    )

    try:
        dataplex_client.create_entry(
            parent=entry_group_name,
            entry=entry,
            entry_id=item["entry_id"],
        )
        print(f"[✓] Created Entry: {item['entry_id']} -> {item['display_name']}")
    except AlreadyExists:
        print(f"[*] Entry already exists: {item['entry_id']}")
    except Exception as e:
        print(f"❌ Error creating entry '{item['entry_id']}': {e}")

print("\n===================================================================")
print(" 🎉 Knowledge Catalog initialization completed successfully!")
print("===================================================================")