from math import *
from mathutils import *
import numpy as np


def build_arc(angle, radius, resolution, width, scale, direction, offset, origin):
    """builds a 2D arc with given angle, radius, resolution and scale"""
    points = []
    origin = Vector(origin.location + offset)
    for i in np.arange(resolution):
        a = Vector()
        b = Vector()
        c = Vector()
        d = Vector()
        a.x = origin.x + cos(i * angle / resolution) * radius * scale.x
        a.y = origin.y + sin(i * angle / resolution) * radius * scale.y
        a.z = origin.z + i * scale.z / resolution
        d.x = origin.x + cos(i * angle / resolution) * (radius + width) * scale.x
        d.y = origin.y + sin(i * angle / resolution) * (radius + width) * scale.y
        d.z = origin.z + i * scale.z / resolution
        b.x = origin.x + cos((i + 1) * angle / resolution) * radius * scale.x
        b.y = origin.y + sin((i + 1) * angle / resolution) * radius * scale.y
        b.z = origin.z + (i + 1) * scale.z / resolution
        c.x = origin.x + cos((i + 1) * angle / resolution) * (radius + width) * scale.x
        c.y = origin.y + sin((i + 1) * angle / resolution) * (radius + width) * scale.y
        c.z = origin.z + (i + 1) * scale.z / resolution
        if direction:
            a, b = b, a
            d, c = c, d
        points.append((a, b, c, d))

    return points


def build_circle(radius: float, resolution: int, origin: Vector, offset: Vector, rotation: Euler, scale: Vector):
    """builds a circle (list of verts) with repeating start/end point. used for path curves"""
    points = []
    origin += offset
    for i in range(resolution):
        p = Vector()
        p = Vector((cos(i*2*pi/resolution)*scale.x, sin(i*2*pi/resolution)*scale.y, 0))
        p *= radius
        p.rotate(rotation)
        p += origin
        points.append(p)
    points.append(points[0])
    return points


def curve_mesh_to_road(indices: list):
    shapes = []
    for i in range(int((len(indices) - 1) / 2)):
        w = [
            indices[(2 * i)], indices[(2 * i + 1)], indices[(2 * i + 2)], indices[(2 * i + 3)]]
        w[1], w[3] = w[3], w[1]
        w[1], w[2] = w[2], w[1]
        shapes.append(w)

    return shapes


def create_adjacent(a: Vector, b: Vector, c: Vector, d: Vector, right):
    if right:
        return (d, c, 2 * c - b, 2 * d - a)
    return (
        2 * a.copy() - d.copy(), 2 * b.copy() - c.copy(), b, a)


def create_shifted(a: Vector, b: Vector, c: Vector, d: Vector, distance):
    step_up = (c - b).normalized() * distance
    step_down = (d - a).normalized() * distance
    return (
        a + step_down, b + step_up, c + step_up, d + step_down)


def edit_width(a: Vector, b: Vector, c: Vector, d: Vector, delta, pivot):
    if pivot == 'LEFT':
        c = c + delta*(c-b)/(c-b).length
        d = d + delta*(d-a)/(d-a).length
    elif pivot == 'CENTER':
        b = b + delta*(b-c)/(b-c).length
        c = c + delta*(c-b)/(c-b).length
        a = a + delta*(a-d)/(a-d).length
        d = d + delta*(d-a)/(d-a).length
    elif pivot == 'RIGHT':
        a = a + delta*(a-d)/(a-d).length
        b = b + delta*(b-c)/(b-c).length
    return (a, b, c, d)


def create_straight(start, rotation, resolution, width, length):
    points = []
    step = Vector()
    step.y = length / resolution
    print(step)
    step.rotate(rotation)
    sidestep = Vector((width / 2, 0, 0))
    sidestep.rotate(rotation)
    a = start + sidestep
    b = a + step
    d = start - sidestep
    c = d + step
    points.append((a, b, c, d))
    for i in list(range(resolution))[1:]:
        a = b
        d = c
        b = b + step
        c = c + step
        points.append((a, b, c, d))

    return points


def dfs(graph, start):
    visited, stack = set(), [start]
    while stack:
        vertex = stack.pop()
        if vertex not in visited:
            visited.add(vertex)
            stack.extend(graph[vertex] - visited)

    return visited


def is_connected(graph):
    island = dfs(graph, list(graph)[0])
    if len(island) == len(graph):
        return True
    else:
        return set(graph).difference(set(island))
