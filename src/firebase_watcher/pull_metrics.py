import time
from collections import defaultdict
from google.cloud import monitoring_v3

PROJECT_ID = 'hugging-app'
project_name = f"projects/{PROJECT_ID}"
METRIC= "firestore.googleapis.com/document/read_ops_count"

client = monitoring_v3.MetricServiceClient();

now = int(time.time())

interval = monitoring_v3.TimeInterval({
    "end_time":   {"seconds": now},
    "start_time": {"seconds": now - 86400},
})

def read_ops(hours=24, bucket_seconds=3600):
   now = int(time.time())
   interval = monitoring_v3.TimeInterval({
      "end_time": {"seconds": now},
      "start_time": {"seconds": now - hours * 3600},
   })
   aggregation = monitoring_v3.Aggregation({
      "alignment_period": {"seconds": bucket_seconds},
      "per_series_aligner": monitoring_v3.Aggregation.Aligner.ALIGN_SUM,
      "cross_series_reducer": monitoring_v3.Aggregation.Reducer.REDUCE_SUM,
      "group_by_fields": ["metric.labels.type"],
   })
   series = client.list_time_series(request={
      "name": f"projects/{PROJECT_ID}",
      "filter": f'metric.type = "{METRIC}" AND resource.type = "firestore.googleapis.com/Database"',
      "interval": interval,
      "aggregation": aggregation,
      "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL
   })

   buckets = defaultdict(dict)
   for s in series:
      op = s.metric.labels.get("type", "UNKNOWN")
      for p in s.points:
         buckets[op][p.interval.end_time] = p.value.int64_value
   return buckets


# result = read_ops(hours=24, bucket_seconds=3600)

# assert result is not None
# for op, points in sorted(result.items(), key=lambda kv: -sum(kv[1].values())):
#     print(f"\n{op}: {sum(points.values()):,} reads")
#     for ts, v in sorted(points.items()):
#         if v:
#             print(f"  {ts:%m-%d %H:%M}  {v:>6,}  {'!!' * min(40, v // 25)}")