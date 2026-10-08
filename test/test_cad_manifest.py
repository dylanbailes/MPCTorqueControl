"""Keep the custom-CAD publication exception narrow and tied to reviewed bytes."""
import hashlib
import json

from scripts import check_repo


def write_manifest(tmp_path, monkeypatch, *, filename='step/custom.step', digest=None):
    monkeypatch.setattr(check_repo, 'ROOT', tmp_path)
    root = tmp_path / 'hardware/cad/custom'
    root.mkdir(parents=True)
    asset = root / 'step/custom.step'
    asset.parent.mkdir()
    asset.write_bytes(b'custom prototype geometry')
    data = {'parts': [{'slug': 'custom',
        'provenance': 'Project-authored custom geometry; linked supplier children omitted',
        'files': [filename],
        'sha256': {filename: digest or hashlib.sha256(asset.read_bytes()).hexdigest()}}]}
    (root / 'manifest.json').write_text(json.dumps(data), encoding='utf-8')
    return asset


def test_only_documented_custom_asset_is_cleared(tmp_path, monkeypatch):
    asset = write_manifest(tmp_path, monkeypatch)
    supplier = asset.with_name('downloaded_supplier.step')
    supplier.write_bytes(b'supplier reference')
    errors = []
    assert check_repo.cleared_custom_cad(errors) == {asset}
    assert not errors


def test_changed_geometry_requires_manifest_review(tmp_path, monkeypatch):
    asset = write_manifest(tmp_path, monkeypatch)
    asset.write_bytes(b'changed or replaced geometry')
    errors = []
    assert not check_repo.cleared_custom_cad(errors)
    assert any('hash differs' in error for error in errors)


def test_manifest_cannot_clear_supplier_directory(tmp_path, monkeypatch):
    write_manifest(tmp_path, monkeypatch, filename='../step/supplier.step')
    errors = []
    assert not check_repo.cleared_custom_cad(errors)
    assert any('Invalid custom CAD manifest path' in error for error in errors)
