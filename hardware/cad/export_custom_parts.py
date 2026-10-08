"""Export the custom parts from the open SEA Fusion assembly.

Run in Fusion's Python environment. Archives with linked supplier children
are replaced by isolated solid snapshots; leaf archives retain native history.
This never saves or changes the source design. STL coordinates are millimeters.
"""
import hashlib
import json
from pathlib import Path

import adsk.core
import adsk.fusion

OUTPUT = Path('D:/Project/hardware/cad/custom')
PARTS = {
    'Torsion bar': ('torsion_bar', False),
    '8mm shaft': ('load_shaft_8mm', False),
    'Hub for Motor': ('motor_hub', True),
    'Hub for Load Disc': ('load_hub', True),
    'Motor Mount': ('motor_mount', True),
    'Bearing Bloc 1': ('bearing_block', True),
    '20x20 Bracket': ('extrusion_bracket', True),
    'inertial disc': ('inertial_disk', True),
}


def box_mm(body):
    box = body.boundingBox
    return [[v * 10 for v in p.asArray()] for p in (box.minPoint, box.maxPoint)]


def export_stl(manager, bodies, slug):
    files = []
    for index, body in enumerate(bodies, 1):
        suffix = '' if len(bodies) == 1 else f'_body_{index}'
        path = OUTPUT / 'stl' / f'{slug}{suffix}.stl'
        options = manager.createSTLExportOptions(body, str(path))
        options.unitType = adsk.fusion.DistanceUnits.MillimeterDistanceUnits
        options.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementHigh
        options.isBinaryFormat = True
        options.sendToPrintUtility = False
        if not manager.execute(options):
            raise RuntimeError(f'STL export failed: {slug}')
        files.append(path.relative_to(OUTPUT).as_posix())
    return files


def run(_context: str):
    app = adsk.core.Application.get()
    source_doc = next((doc for doc in app.documents if doc.dataFile and doc.dataFile.name == 'Full Assembly FOR SEA'), None)
    if source_doc is None:
        raise RuntimeError('Open the Full Assembly FOR SEA design before exporting')
    source = adsk.fusion.Design.cast(source_doc.products.itemByProductType('DesignProductType'))
    was_modified = source_doc.isModified
    components = {c.name: c for c in source.allComponents if c.name in PARTS}
    if set(components) != set(PARTS):
        raise RuntimeError(f'Missing parts: {set(PARTS) - set(components)}')
    for folder in ('fusion', 'step', 'stl'):
        (OUTPUT / folder).mkdir(parents=True, exist_ok=True)
    manifest = {
        'source_document': source_doc.name,
        'source_version': source_doc.dataFile.versionNumber,
        'export_date': '2026-10-07',
        'units': 'mm',
        'status': 'as-modeled prototype; not validated manufacturing releases',
        'supplier_reference_policy': 'No supplier geometry exported. Parts with supplier children use isolated body copies.',
        'parts': [],
    }
    for name, (slug, printable) in PARTS.items():
        component = components[name]
        bodies = list(component.bRepBodies)
        if not bodies:
            raise RuntimeError(f'No custom bodies: {name}')
        children = [o.component.name for o in component.occurrences]
        record = {
            'source_name': name,
            'provenance': 'Project-authored custom geometry; linked supplier children omitted',
            'slug': slug,
            'source_sketches': component.sketches.count,
            'source_features': component.features.count,
            'native_history': 'parametric' if not children else 'geometry_only',
            'omitted_linked_children': children,
            'bodies': [{'name': b.name, 'volume_mm3': b.getPhysicalProperties(adsk.fusion.CalculationAccuracy.VeryHighCalculationAccuracy).volume * 1000,
                        'bbox_mm': box_mm(b), 'cad_material': b.material.name} for b in bodies],
            'files': [],
        }
        work_doc = None
        try:
            if children:
                # A component archive with external references cannot be opened
                # independently. Copy only the custom solids to a clean document.
                work_doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
                target = adsk.fusion.Design.cast(work_doc.products.itemByProductType('DesignProductType'))
                target.designType = adsk.fusion.DesignTypes.DirectDesignType
                temp = adsk.fusion.TemporaryBRepManager.get()
                export_bodies = []
                for body in bodies:
                    copied = target.rootComponent.bRepBodies.add(temp.copy(body))
                    copied.name = body.name
                    copied.material = body.material
                    export_bodies.append(copied)
                export_component = target.rootComponent
            else:
                target = source
                export_component = component
                export_bodies = bodies
            manager = target.exportManager
            f3d = OUTPUT / 'fusion' / f'{slug}.f3d'
            step = OUTPUT / 'step' / f'{slug}.step'
            if not manager.execute(manager.createFusionArchiveExportOptions(str(f3d), export_component)):
                raise RuntimeError(f'Fusion archive export failed: {name}')
            if not manager.execute(manager.createSTEPExportOptions(str(step), export_component)):
                raise RuntimeError(f'STEP export failed: {name}')
            record['files'] += [f3d.relative_to(OUTPUT).as_posix(), step.relative_to(OUTPUT).as_posix()]
            if printable:
                record['files'] += export_stl(manager, export_bodies, slug)
            record['sha256'] = {f: hashlib.sha256((OUTPUT / f).read_bytes()).hexdigest() for f in record['files']}
            manifest['parts'].append(record)
        finally:
            if work_doc:
                work_doc.close(False)
            source_doc.activate()
    placements = []
    for o in source.rootComponent.allOccurrences:
        if o.component.name in PARTS:
            placements.append({'part': PARTS[o.component.name][0], 'occurrence': o.fullPathName,
                               'transform_row_major': o.transform2.asArray(),
                               'transform_translation_units': 'cm (Fusion internal)',
                               'visible': o.isVisible})
    (OUTPUT / 'assembly_layout.json').write_text(json.dumps({'source_document': source_doc.name,
        'source_version': source_doc.dataFile.versionNumber, 'placements': placements}, indent=2) + '\n', encoding='utf-8')
    manifest['source_modified_before'] = was_modified
    manifest['source_modified_after'] = source_doc.isModified
    if source_doc.isModified != was_modified:
        raise RuntimeError('Source modified state changed during export')
    (OUTPUT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'parts': len(manifest['parts']), 'files': sum(len(p['files']) for p in manifest['parts']),
                      'source_modified': source_doc.isModified, 'output': str(OUTPUT)}))
