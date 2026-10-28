"""Export a saved 1D PN state as real VTK_LINE cells, without solving again.

PointData: node quantities; CellData: raw edge quantities (no interpolation).
The 1D snapshot exporter uses XML directly, so native 2D/3D VTK export
availability does not change the PN physics or require an artificial extrusion.
"""
import argparse
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET


def export_vtm(state, prefix):
    prefix = Path(prefix)
    vtu, vtm = prefix.with_suffix('.vtu'), prefix.with_suffix('.vtm')
    if vtu.exists() or vtm.exists():
        raise FileExistsError('Refusing to overwrite VTK output')
    nodes, edges = state['nodes'], state['edges']
    x = nodes['x_cm']
    if len(x) < 2 or any(b<=a for a,b in zip(x,x[1:])):
        raise ValueError('Strictly increasing 1D coordinates required')
    for table, length in ((nodes,len(x)), (edges,len(x)-1)):
        if any(len(values)!=length or not all(math.isfinite(v) for v in values) for values in table.values()):
            raise ValueError('Invalid field size or non-finite field')
    if not state['solver_info']['converged']:
        raise ValueError('Only converged states can be exported')
    prefix.parent.mkdir(parents=True, exist_ok=True)
    root = ET.Element('VTKFile', type='UnstructuredGrid', version='0.1', byte_order='LittleEndian')
    grid = ET.SubElement(root, 'UnstructuredGrid')
    piece = ET.SubElement(grid, 'Piece', NumberOfPoints=str(len(x)), NumberOfCells=str(len(x)-1))

    def array(parent, name, values, dtype='Float64', components=None):
        attrs = dict(type=dtype, Name=name, format='ascii')
        if components:
            attrs['NumberOfComponents'] = str(components)
        item = ET.SubElement(parent, 'DataArray', attrs)
        item.text = ' '.join(format(v,'.17g') if dtype=='Float64' else str(v) for v in values)

    point_data = ET.SubElement(piece, 'PointData', Scalars='Potential_V')
    for name, values in nodes.items():
        array(point_data, name, values)
    cell_data = ET.SubElement(piece, 'CellData', Scalars='ElectricField_V_per_cm')
    for name, values in edges.items():
        array(cell_data, name, values)
    array(ET.SubElement(piece,'Points'), 'Coordinates_cm', [v for a in x for v in (a,0.0,0.0)], components=3)
    cells = ET.SubElement(piece,'Cells')
    array(cells,'connectivity',[v for i in range(len(x)-1) for v in (i,i+1)],'Int64')
    array(cells,'offsets',[2*(i+1) for i in range(len(x)-1)],'Int64')
    array(cells,'types',[3]*(len(x)-1),'UInt8')  # VTK_LINE
    multiblock = ET.Element('VTKFile', type='vtkMultiBlockDataSet', version='1.0', byte_order='LittleEndian')
    blocks = ET.SubElement(multiblock,'vtkMultiBlockDataSet')
    ET.SubElement(blocks,'DataSet', index='0', name='Silicon_PN', file=vtu.name)
    ET.ElementTree(root).write(vtu, encoding='utf-8', xml_declaration=True)
    ET.ElementTree(multiblock).write(vtm, encoding='utf-8', xml_declaration=True)
    return [vtu.name,vtm.name]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', required=True, help='Existing mesh JSON; no new solve')
    parser.add_argument('--prefix', required=True, help='New output prefix, without extension')
    args = parser.parse_args()
    state = json.loads(Path(args.state).read_text(encoding='utf-8'))
    print(export_vtm(state, args.prefix))


if __name__ == '__main__':
    main()
