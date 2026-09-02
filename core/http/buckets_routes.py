from __future__ import annotations

from http import HTTPStatus


class BucketsRoutesMixin:
    def _handle_buckets_get(self, path: str, query: dict) -> None:
        from core.memory.bucket_classifier import _load_classifications
        from core.memory.buckets_service import (
            get_summary,
            get_taxonomy,
            get_tree_view,
            list_events_for_bucket,
            list_recent_classified_events,
        )

        if path == "/buckets":
            self._send_json(HTTPStatus.OK, _load_classifications())
            return
        if path == "/buckets/taxonomy":
            self._send_json(HTTPStatus.OK, get_taxonomy())
            return
        if path == "/buckets/summary":
            days = int(query.get("days", ["7"])[0])
            self._send_json(HTTPStatus.OK, get_summary(days=days))
            return
        if path == "/buckets/tree":
            days = int(query.get("days", ["7"])[0])
            self._send_json(HTTPStatus.OK, get_tree_view(days=days))
            return
        if path == "/buckets/events":
            bucket = query.get("bucket", [""])[0].strip()
            days = int(query.get("days", ["7"])[0])
            if not bucket:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "bucket is required"})
                return
            self._send_json(HTTPStatus.OK, {
                "events": list_events_for_bucket(bucket, days=days),
            })
            return
        if path == "/buckets/recent":
            days = int(query.get("days", ["7"])[0])
            limit = int(query.get("limit", ["30"])[0])
            self._send_json(HTTPStatus.OK, {
                "events": list_recent_classified_events(days=days, limit=limit),
            })
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
