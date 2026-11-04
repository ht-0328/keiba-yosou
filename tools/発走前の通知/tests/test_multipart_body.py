"""MultipartBody（multipart/form-data の本文）のテスト。"""

from __future__ import annotations

from 発走前の通知.multipart_body import MultipartBody


def test_欄と添付を区切りで並べて閉じる() -> None:
    body = MultipartBody("B0UNDARY")
    data = body.encode({"payload_json": '{"content": "文"}'}, [("files[0]", "根拠.md", b"abc")])
    assert body.content_type == "multipart/form-data; boundary=B0UNDARY"
    assert data.startswith(b'--B0UNDARY\r\nContent-Disposition: form-data; name="payload_json"\r\n\r\n')
    assert '{"content": "文"}'.encode("utf-8") + b"\r\n--B0UNDARY\r\n" in data
    assert 'name="files[0]"; filename="根拠.md"\r\nContent-Type: application/octet-stream\r\n\r\nabc\r\n'.encode("utf-8") in data
    assert data.endswith(b"--B0UNDARY--\r\n")


def test_区切りを省くと毎回違う() -> None:
    assert MultipartBody().content_type != MultipartBody().content_type
