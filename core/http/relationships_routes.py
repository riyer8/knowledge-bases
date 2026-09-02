from __future__ import annotations

from http import HTTPStatus


class RelationshipsRoutesMixin:
    def _handle_relationships_get(self, path: str) -> None:
        from core.memory.relationships import get_profile, list_profiles

        if path == "/relationships":
            self._send_json(HTTPStatus.OK, {"profiles": list_profiles()})
            return
        if path.startswith("/relationships/"):
            person_hash = path.split("/relationships/", 1)[1].strip("/")
            profile = get_profile(person_hash)
            if not profile:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "profile not found"})
                return
            self._send_json(HTTPStatus.OK, {"profile": profile})
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
