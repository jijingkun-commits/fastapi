"""上传接口文案回归测试。"""

from io import BytesIO

import pytest
from fastapi import HTTPException
from starlette.datastructures import Headers, UploadFile

from app.api.v1.endpoints import upload_api


@pytest.mark.asyncio
async def test_upload_should_return_convert_hint_for_legacy_doc() -> None:
    upload = UploadFile(
        file=BytesIO(b"legacy-doc"),
        filename="legacy.doc",
        headers=Headers({"content-type": "application/msword"}),
    )

    with pytest.raises(HTTPException) as exc_info:
        await upload_api.upload_image(
            file=upload,
            thread_id=None,
            current_user=None,
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "暂不支持 .doc，请先转换为 .docx"
