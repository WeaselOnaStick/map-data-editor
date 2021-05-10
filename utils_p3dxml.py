from xml.dom import minidom
import re
import os
from mathutils import Matrix, Vector
import xml.etree.cElementTree as ET
RDS = '0x3000009'  # Road Data Segment
INS = '0x3000004'  # Intersection
ROA = '0x3000003'  # Road (Node)
RSG = '0x3000002'  # Road Segment
PAT = '0x300000B'  # Path
FEN = '0x3F00007'  # Fence
FEN2 = '0x3000000'  # Fence 2
LOC = '0x3000005'  # Locator
VOL = '0x3000006'  # Trigger Volume
LOM = '0x300000C'  # Locator Matrix
# Only used in splitter operator (Deprecated soon)
RoadChunks = [RDS, INS, ROA, RSG, PAT, FEN, FEN2, LOC]


def p3d_et(ver=4.4):
    return ET.Element('Pure3DFile', LucasPure3DEditorVersion=(str(ver)))


def write_val(loc, name, value=None):
    """returns a value ET element with Name=name and Value=value at loc"""
    if (value is None):
        return ET.SubElement(loc, 'Value', Name=name)
    else:
        return ET.SubElement(loc, 'Value', Name=name, Value=(str(value)))


def write_xyz(loc, name, x, y, z, element='Value'):
    """returns a value ET element with Name=name and set XYZ at loc. SWAPS Y AND Z"""
    if name:
        ET.SubElement(loc, element, Name=name, X=(str(x)), Y=(str(z)), Z=(str(y)))
    else:
        ET.SubElement(loc, element, X=(str(x)), Y=(str(z)), Z=(str(y)))



def write_mat_xyz(loc, name, x=0, y=0, z=0):
    """returns a value ET element with Name=name and set XYZ as M41, M42 and M43 at loc. SWAPS Y AND Z"""
    mat = Matrix()
    if not (x == y == z == 0):
        mat[3][0] = x
        mat[3][2] = y
        mat[3][1] = z
    tran = ET.SubElement(loc, "Value", Name=name)
    for i, row in enumerate(mat):
        for j, cell in enumerate(row):
            tran.set(f"M{i + 1}{j + 1}", str(cell))
    return tran


def write_comment(loc, text):
    """writes a comment at loc"""
    loc.append(ET.Comment(text))


def write_chunk(loc, chunk_type: str):
    """returns a chunk ET element with Type=type at loc"""
    return ET.SubElement(loc, 'Chunk', Type=chunk_type)


def write_ET(root, filepath):
    """writes entire root ET element into a file at filepath"""
    with open(filepath, "w") as f:
        f.write('\n'.join([line for line in minidom.parseString(ET.tostring(
            root, 'unicode')).toprettyxml(indent='\t').split('\n') if line.strip()]))
        f.close()


def find_chunks(loc, chunktype):
    """returns all ET in loc of chunktype"""
    return loc.findall(f"*[@Type='{chunktype}']")


def find_val(loc, valname):
    """returns Value named valname in loc"""
    if 'Value' in loc.find(f"*[@Name='{valname}']").attrib:
        return loc.find(f"*[@Name='{valname}']").attrib['Value']


def chunks_to_dict_by_name(chunks):
    """Convert list of chunks with Name values into a dictionary { Name : Chunk }"""
    c_dict = {}
    for i in chunks:
        c_dict[find_val(i, 'Name')] = i
    return c_dict


def find_xyz(loc, valname):
    """returns vector named valname in loc"""
    v = Vector()
    values = loc.find(f"*[@Name='{valname}']").attrib
    v.x = float(values['X'])
    v.y = float(values['Z'])
    v.z = float(values['Y'])
    return v


def item_to_vector(item):
    """Converts XML item object to vector. SWAPS Y and Z"""
    v = Vector()
    v.x = float(item.attrib['X'])
    v.y = float(item.attrib['Z'])
    v.z = float(item.attrib['Y'])
    return v


def find_HalfExtent_scale(loc):
    scale = Vector()
    values = loc.find("*[@Name='HalfExtents']").attrib
    scale.x = float(values['X'])
    scale.y = float(values['Z'])
    scale.z = float(values['Y'])
    return scale


def write_scale_to_HalfExtent(loc, obj):
    write_xyz(loc, "HalfExtents", *obj.scale)


def write_locrot_to_mat(loc, obj, name="Matrix"):
    obj_loc = obj.matrix_world.to_translation().copy()
    obj_loc.y, obj_loc.z = obj_loc.z, obj_loc.y
    obj_rot = obj.matrix_world.to_quaternion().copy()
    obj_rot.y, obj_rot.z = obj_rot.z, obj_rot.y
    mat = obj_rot.to_matrix().to_4x4()
    mat[3] = obj_loc.to_4d()
    mat_el = ET.SubElement(loc, "Value", {"Name": name})
    for i in range(4):
        for j in range(4):
            mat_el.attrib[f"M{i+1}{j+1}"] = str(mat[i][j])


def find_xyz_from_mat(loc, mat_name):
    """returns xyz from matrix named mat_name in loc"""
    a = Vector()
    values = loc.find(f"*[@Name='{mat_name}']").attrib
    a.x = float(values['M41'])
    a.y = float(values['M43'])
    a.z = float(values['M42'])
    return a


def find_xyz_from_transform_mat(loc):
    return find_xyz_from_mat(loc, "Transform")


def find_euler_from_mat(loc, mat_name):
    rot_mat = Matrix()
    values = loc.find(f"*[@Name='{mat_name}']").attrib
    for i in range(3):
        for j in range(3):
            rot_mat[i][j] = float(values[f'M{i+1}{j+1}'])
    q = rot_mat.to_quaternion()
    q.y, q.z = q.z, q.y
    return q.to_euler()


def terra_read(fp):
    """reads ENTIRE TERRA, returns ET"""
    with open(fp, 'r') as (f):
        Text = f.read()
        Text = re.sub('&#x0;.+?"', '"', Text)
        return ET.fromstring(Text)


def split_terra(input_file, already_split=False):
    fp, fn = os.path.split(input_file)
    fn = os.path.splitext(fn)[0]
    roads_path = fp + '\\' + fn + '_roads.p3dxml'
    paths_path = fp + '\\' + fn + '_paths.p3dxml'
    fences_path = fp + '\\' + fn + '_fences.p3dxml'
    locators_path = fp + '\\' + fn + '_locators.p3dxml'
    others_path = fp + '\\' + fn + '_others.p3dxml'

    roads_file = p3d_et()
    paths_file = p3d_et()
    fences_file = p3d_et()
    locators_file = p3d_et()
    others_file = p3d_et()
    root = terra_read(input_file)
    for item in root:
        if item.attrib['Type'] in [RDS, INS, ROA, RSG]:
            roads_file.append(item)
        elif item.attrib['Type'] == PAT:
            paths_file.append(item)
        elif item.attrib['Type'] == FEN:
            fences_file.append(item)
        elif item.attrib['Type'] == LOC:
            locators_file.append(item)
        else:
            others_file.append(item)
    write_ET(roads_file, roads_path)
    write_ET(paths_file, paths_path)
    write_ET(fences_file, fences_path)
    write_ET(locators_file, locators_path)
    write_ET(others_file, others_path)
    return roads_path


def find_volumes(loc):
    """Returnes list of dictionaries (name, is_rect, location, rotation, scale)"""
    vol_chunks = find_chunks(loc, VOL)
    if not vol_chunks:
        return []
    vol_list = []
    for vol in vol_chunks:
        vol_name = find_val(vol, "Name")
        vol_is_rect = bool(int(find_val(vol, "IsRect")))
        vol_loc = find_xyz_from_mat(vol, "Matrix")
        vol_rot = find_euler_from_mat(vol, "Matrix")
        vol_scale = find_HalfExtent_scale(vol)
        vol_list.append({"name": vol_name, "is_rect": vol_is_rect,
                         "location": vol_loc, "rotation": vol_rot, "scale": vol_scale})
    return vol_list


def write_volume(loc, vol_obj):
    volume = write_chunk(loc, VOL)
    write_val(volume, "Name", vol_obj.name)
    if vol_obj.empty_display_type == 'CUBE':
        write_val(volume, "IsRect", "1")
    else:
        write_val(volume, "IsRect", "0")
    write_xyz(volume, "HalfExtents", *vol_obj.scale)
    write_locrot_to_mat(volume, vol_obj)


def find_locrot_LOM(loc):
    """finds a Locator Matrix (0x300000C) inside loc, returns a tuple (location, rotation(Euler XYZ))"""
    if not find_chunks(loc, LOM):
        return
    lm = find_chunks(loc, LOM)[0]
    lm = lm.find("*[@Name='Matrix']").attrib
    tran_mat = Matrix()
    for i in range(4):
        for j in range(4):
            tran_mat[i][j] = float(lm[f'M{i+1}{j+1}'])
    location = tran_mat[3].to_3d()
    location.y, location.z = location.z, location.y
    q = tran_mat.to_quaternion()
    q.y, q.z = q.z, q.y
    return location, q.to_euler()
