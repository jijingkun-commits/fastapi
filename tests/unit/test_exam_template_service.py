from __future__ import annotations

from app.services import exam_template_service


class _Resp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_list_available_datasets_should_use_ragflow_dataset_name(monkeypatch) -> None:
    monkeypatch.setattr(exam_template_service.app_config, 'RAGFLOW_DATASET_IDS', ['kb-a', 'kb-b'], raising=False)
    monkeypatch.setattr(exam_template_service.app_config, 'RAGFLOW_DATASET_ID', 'kb-a', raising=False)
    monkeypatch.setattr(exam_template_service.app_config, 'RAGFLOW_API_KEY', 'demo', raising=False)
    monkeypatch.setattr(
        exam_template_service.requests,
        'get',
        lambda *args, **kwargs: _Resp({'code': 0, 'data': [{'id': 'kb-a', 'name': '网络金融部'}, {'id': 'kb-b', 'name': '零售条线'}]}),
    )

    datasets = exam_template_service.list_available_datasets()

    assert [item.label for item in datasets] == ['网络金融部', '零售条线']


def test_resolve_dataset_labels_should_fallback_to_dataset_id(monkeypatch) -> None:
    monkeypatch.setattr(exam_template_service.app_config, 'RAGFLOW_API_KEY', 'demo', raising=False)
    monkeypatch.setattr(
        exam_template_service.requests,
        'get',
        lambda *args, **kwargs: _Resp({'code': 0, 'data': [{'id': 'kb-a', 'name': '网络金融部'}]}),
    )

    labels = exam_template_service.resolve_dataset_labels(['kb-a', 'kb-missing'])

    assert labels == ['网络金融部', 'kb-missing']
