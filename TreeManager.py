#I honestly have no idea how I wrote all this mess. But it works and that's what matters
import numpy as np
import itertools
from math import pi
from mathutils import Euler, Vector, geometry
import mathutils
from .utils_p3dxml import *
import bpy
import bmesh
import sys
from mathutils.bvhtree import BVHTree

def point_in_bound(a : Vector, bound_bl : Vector, bound_ur : Vector, ignore_z = True):
    if any([
        a.x < bound_bl.x, 
        a.y < bound_bl.y, 
        a.x > bound_ur.x, 
        a.y > bound_ur.y,
        ]):
            return False
    if not ignore_z:
        if any([
        a.z < bound_bl.z, 
        a.z > bound_ur.z,
        ]):
            return False
    return True

def snap_int_to_divisible(x, a, up = True):
    return x - (x % a) + a*int(up)

def snap_vector_to_divisible(x : Vector, a, up = True):
    x = x.copy()
    for i in range(len(x)):
        x[i] = snap_int_to_divisible(x[i], a, up)
    return x

class TreeNode:
    def __init__(self, parent = None, lc = None, rc = None, split_axis = None, split_pos = None, corner_bl = None, corner_ur = None):
        self.parent = parent
        self.lc = lc
        self.rc = rc
        self.split_axis = split_axis
        self.split_pos = split_pos
        self.corner_bl = corner_bl
        self.corner_ur = corner_ur
        # limit_SE    = 0
        # limit_SPE   = 0
        # limit_IE    = 0
        # limit_DPE   = 0
        # limit_FE    = 0
        # limit_RSE   = 0
        # limit_PSE   = 0
        # limit_AE    = 0

    def split(self, axis, pos):
        self.lc = TreeNode(parent=self, corner_bl=self.corner_bl, corner_ur=self.corner_ur)
        self.rc = TreeNode(parent=self, corner_bl=self.corner_bl, corner_ur=self.corner_ur)
        self.split_axis = axis
        self.split_pos = pos
        if axis == 0:
            self.lc.corner_ur = Vector((pos,self.corner_ur.y,self.corner_ur.z))
            self.rc.corner_bl = Vector((pos,self.corner_bl.y,self.corner_bl.z))
        if axis == 1:
            self.lc.corner_ur = Vector((self.corner_ur.x,pos,self.corner_ur.z))
            self.rc.corner_bl = Vector((self.corner_bl.x,pos,self.corner_bl.z))
        return self.lc,self.rc

    def children_count(self):
        x = 1
        if self.lc:
            x += self.lc.children_count()
        if self.rc:
            x += self.rc.children_count()
        return x
    
    def contains_vector(a : Vector):
        pass

    def dim(self):
        return (self.corner_ur-self.corner_bl).x,(self.corner_ur-self.corner_bl).y,(self.corner_ur-self.corner_bl).z

    # debug stuff
    def __str__(self):
        return f"TreeNode \t#{id(self)} parent = {id(self.parent) if self.parent else '       ROOT'}\tlc = {id(self.lc) if self.lc else None}, rc = {id(self.rc) if self.rc else None}\t split_axis = {self.split_axis}, split_pos = {self.split_pos}. \t children count = {self.children_count()}\t bounds = ({self.corner_bl},{self.corner_ur})"

    def str_inorder(self):
        if not(self.lc or self.rc):
            return ''
        a = str(self) + "\n"
        if self.lc: a = a + self.lc.str_inorder()
        if self.rc: a = a + self.rc.str_inorder()
        return a
    
    def print_inorder(self):
        if self.lc and self.rc:
            print(str(self))
        if self.lc: self.lc.print_inorder()
        if self.rc: self.rc.print_inorder()
    
    def list_preorder(self):
        output = [self]
        if self.lc: output += self.lc.list_preorder()
        if self.rc: output += self.rc.list_preorder()
        return output

class Tree:

    root = TreeNode()
    def __init__(self, min : Vector = Vector(), max  : Vector = Vector()):
        self.min = min
        self.max = max
        self.root.corner_bl = min
        self.root.corner_ur = max
    
    def __str__(self):
        return self.root.str_inorder()

def grid_generate(gridsize = 20, marker_set = []):
    treemin = Vector((min([x[0] for x in marker_set]),min([x[1] for x in marker_set]),min([x[2] for x in marker_set])))
    treemax = Vector((max([x[0] for x in marker_set]),max([x[1] for x in marker_set]),max([x[2] for x in marker_set])))
    treemin = snap_vector_to_divisible(treemin, gridsize, up = False)
    treemax = snap_vector_to_divisible(treemax, gridsize, up = True)

    def QuadTree(treenode : TreeNode, marker_set):
        if not treenode:
            return
        if (treenode.dim()[0] <= gridsize) and (treenode.dim()[1] <= gridsize):
            return
        if not (any([point_in_bound(x, treenode.corner_bl, treenode.corner_ur, ignore_z=True) for x in marker_set])):
            return
        
        #Chopping rectangles with 1 side ~= gridsize
        
        if (treenode.dim()[0] <= gridsize) != (treenode.dim()[1] <= gridsize):
            if treenode.dim()[0] <= gridsize : shortcut = 1 
            if treenode.dim()[1] <= gridsize : shortcut = 0 

            a,b = treenode.split(shortcut, snap_int_to_divisible(treenode.corner_bl[shortcut] + treenode.dim()[shortcut]/2, gridsize, False))
            QuadTree(a, marker_set)
            QuadTree(b, marker_set)
            return
        
        #Actual QuadTree magic
        a,b = treenode.split(0, snap_int_to_divisible(treenode.corner_bl[0] + (treenode.dim()[0]/2.),gridsize, False))
        marker_set_a = [m for m in marker_set if m.x<=treenode.split_pos]    
        marker_set_b = [m for m in marker_set if m.x>treenode.split_pos]    
        if a.dim()[1] > gridsize and any([point_in_bound(x, a.corner_bl, a.corner_ur, ignore_z=True) for x in marker_set_a]):

            new_split_pos = snap_int_to_divisible(a.corner_bl[1] + (a.dim()[1]/2.), gridsize, False)
            aa,ab = a.split(1, new_split_pos)
            marker_set_aa = [m for m in marker_set_a if m.y<=new_split_pos]
            marker_set_ab = [m for m in marker_set_a if m.y>new_split_pos]
            QuadTree(aa, marker_set_aa)
            QuadTree(ab, marker_set_ab)
        else:
            QuadTree(a, marker_set_a)

        if b.dim()[1] > gridsize and any([point_in_bound(x, b.corner_bl, b.corner_ur, ignore_z=True) for x in marker_set_b]):
            
            new_split_pos = snap_int_to_divisible(b.corner_bl[1] + (b.dim()[1]/2.), gridsize, False)
            ba,bb = b.split(1, new_split_pos)
            marker_set_ba = [m for m in marker_set_b if m.y<=new_split_pos]
            marker_set_bb = [m for m in marker_set_b if m.y>new_split_pos]
            QuadTree(ba, marker_set_ba)
            QuadTree(bb, marker_set_bb)
        else:
            QuadTree(b, marker_set_b)
            
    T = Tree(treemin, treemax)
    
    QuadTree(T.root, marker_set)
    return T

def import_tree(filepath):
    t = Tree()
    return t

def export_tree(Tree : Tree, filepath):
    root = p3d_et()
    tree_chunk = write_chunk(root, "0x3F00004")
    write_xyz(tree_chunk, "WorldBoundsMinimum", *Tree.min)
    write_xyz(tree_chunk, "WorldBoundsMaximum", *Tree.max)
    tree_list = Tree.root.list_preorder()
    for i,node in enumerate(tree_list):
        TN = write_chunk(tree_chunk, "0x3F00005")
        write_val(TN, "ChildCount", node.children_count() - 1)
        if node.parent:
            write_val(TN, "ParentOffset", tree_list.index(node.parent) - i)
        else:
            write_val(TN, "ParentOffset", 0)
        TN2 = write_chunk(TN, "0x3F00006")
        if node.split_axis is None:
            write_val(TN2, "Axis", -1)
            write_val(TN2, "Position", -1)
        else:
            #axis swap
            if node.split_axis == 0:
                write_val(TN2, "Axis", 0)
            if node.split_axis == 1:
                write_val(TN2, "Axis", 2)
            if node.split_axis == 2:
                write_val(TN2, "Axis", 1)
            write_val(TN2, "Position", node.split_pos)
        # write_val(TN2, "StaticWorldMeshLimit", 0)
        # write_val(TN2, "StaticWorldPropLimit", 0)
        # write_val(TN2, "GroundCollisionLimit", 0)
        # write_val(TN2, "CharactersCarsAndBreakableWorldPropLimit", 0)
        # write_val(TN2, "WallCollisionLimit", 0)
        # write_val(TN2, "RoadNodeSegmentLimit", 0)
        # write_val(TN2, "PedNodeSegmentLimit", 0)
        # write_val(TN2, "WorldMeshLimit", 0)

    write_ET(root, filepath)

def add_salt(x : Vector, salt_amount = 3):
    """returns 4 vectors with salt_amount added in 4 XY directions"""
    return [
        x + Vector((salt_amount,0,0)),
        x + Vector((-salt_amount,0,0)),
        x + Vector((0,salt_amount,0)),
        x + Vector((0,-salt_amount,0)),
    ]

def create_markers_grid_from_meshes(objects, individual = True) -> list:
    """Return 20x20 XY grid within bounds of all objects."""
    marker_locs = []
    tminX,tminY,tmaxX,tmaxY = None,None,None,None
    for o in objects:
        mw  = o.matrix_world        
        #get object bounds
        corners = [mw @ Vector(x) for x in o.bound_box]
        
        minX = snap_int_to_divisible(min([c.x for c in corners]),20,False)
        minY = snap_int_to_divisible(min([c.y for c in corners]),20,False)
        maxX = snap_int_to_divisible(max([c.x for c in corners]),20,True)
        maxY = snap_int_to_divisible(max([c.y for c in corners]),20,True)

        if individual:
            marker_locs += list(itertools.product(np.arange(minX,maxX+20,20),np.arange(minY,maxY+20,20)))
        else:
            if tminX is None or minX < tminX:
                tminX = minX
            if tminY is None or minY < tminY:
                tminY = minY
            if tmaxX is None or maxX > tmaxX:
                tmaxX = maxX
            if tmaxY is None or maxY > tmaxY:
                tmaxY = maxY

    if not individual:
        marker_locs = list(itertools.product(np.arange(tminX,tmaxX+20,20),np.arange(tminY,tmaxY+20,20)))

    return marker_locs

def create_markers_from_meshes(objects,depsgraph) -> list:
    """Return 20x20 XY grid Raycast hits + Vertices"""

    marker_locs = []

    for o in objects:
        bvh = BVHTree.FromObject(o,depsgraph,epsilon=0.0)
        mw  = o.matrix_world
        mwi = o.matrix_world.inverted()
        
        #get object bounds
        corners = [mw @ Vector(x) for x in o.bound_box]

        #get min/max X/Y bound values
        
        minX = snap_int_to_divisible(min([c.x for c in corners]),20,False)
        minY = snap_int_to_divisible(min([c.y for c in corners]),20,False)
        maxX = snap_int_to_divisible(max([c.x for c in corners]),20,True)
        maxY = snap_int_to_divisible(max([c.y for c in corners]),20,True)

        minV = Vector((minX,minY,0))
        maxV = Vector((maxX,maxY,0))
        height = max([c.z for c in corners])+5

        #cast rays from square centers and add marker to Vector List on hit
        i,j = minV.x,minV.y
        while i<maxV.x or j<maxV.y:       
            ray_origin = mwi @ Vector((i,j,height))
            ray_direction = mwi @ Vector((0,0,-sys.maxsize))
            #bpy.ops.object.empty_add(location=(mw @ ray_origin))
            
            hit_loc = bvh.ray_cast(ray_origin,ray_direction)[0]
            if hit_loc:
                #print("hit!")
                hit_loc = mw @ Vector(hit_loc)
                #append actual object.data.vertices to Vector List
                marker_locs = marker_locs + add_salt(hit_loc)
            i = i + 20
            if i>maxV.x:
                j = j + 20
                i = minV.x
        
        
        marker_locs = marker_locs + [mw @ x.co for x in o.data.vertices]
    #repeat for all mesh objects

    #reduce Vector List to only one per 20x20 square(?)
    return marker_locs