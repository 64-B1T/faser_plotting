import math
import matplotlib.pyplot

from faser_math import fsr
#import Arm as Arm
import numpy as np
import scipy.linalg as ling
import glob
#from faserlib.tm import tm

from faser_utils.disp.disp import *
from stl import mesh
import copy
import matplotlib.pyplot as plt
from mpl_toolkits import mplot3d
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection, Line3DCollection
# Get lighting object for shading surface plots.
from matplotlib.colors import LightSource
from collections import defaultdict
from scipy.spatial import Delaunay
from descartes import PolygonPatch
import alphashape
# Get colormaps to use with lighting object.
from matplotlib import cm
from scipy.special import jn

import random

import os
# Create an instance of a LightSource and use it to illuminate the surface.

def alpha_shape_3D(pos, alpha):
    """
    Compute the alpha shape (concave hull) of a set of 3D points.
    Parameters:
        pos - np.array of shape (n,3) points.
        alpha - alpha value.
    return
        outer surface vertex indices, edge indices, and triangle indices
    """
    #Function found here https://stackoverflow.com/questions/26303878/alpha-shapes-in-3d
    tetra = Delaunay(pos)
    # Find radius of the circumsphere.
    # By definition, radius of the sphere fitting inside the tetrahedral needs
    # to be smaller than alpha value
    # http://mathworld.wolfram.com/Circumsphere.html
    tetrapos = np.take(pos,tetra.vertices,axis=0)
    normsq = np.sum(tetrapos**2,axis=2)[:,:,None]
    ones = np.ones((tetrapos.shape[0],tetrapos.shape[1],1))
    a = np.linalg.det(np.concatenate((tetrapos,ones),axis=2))
    Dx = np.linalg.det(np.concatenate((normsq,tetrapos[:,:,[1,2]],ones),axis=2))
    Dy = -np.linalg.det(np.concatenate((normsq,tetrapos[:,:,[0,2]],ones),axis=2))
    Dz = np.linalg.det(np.concatenate((normsq,tetrapos[:,:,[0,1]],ones),axis=2))
    c = np.linalg.det(np.concatenate((normsq,tetrapos),axis=2))
    r = np.sqrt(Dx**2+Dy**2+Dz**2-4*a*c)/(2*np.abs(a))

    # Find tetrahedrals
    tetras = tetra.vertices[r<alpha,:]
    # triangles
    TriComb = np.array([(0, 1, 2), (0, 1, 3), (0, 2, 3), (1, 2, 3)])
    Triangles = tetras[:,TriComb].reshape(-1,3)
    Triangles = np.sort(Triangles,axis=1)
    # Remove triangles that occurs twice, because they are within shapes
    TrianglesDict = defaultdict(int)
    for tri in Triangles:TrianglesDict[tuple(tri)] += 1
    Triangles=np.array([tri for tri in TrianglesDict if TrianglesDict[tri] ==1])
    #edges
    EdgeComb=np.array([(0, 1), (0, 2), (1, 2)])
    Edges=Triangles[:,EdgeComb].reshape(-1,2)
    Edges=np.sort(Edges,axis=1)
    Edges=np.unique(Edges,axis=0)

    Vertices = np.unique(Edges)
    return Vertices,Edges,Triangles
    
def DrawManipulability(J, tm, lenfactor):
    p = tm[0:3,3]
    R = tm[0:3,2]

    Aw = J[0:3,:] @ J[0:3,:].conj().transpose()
    Av = J[3:6,:] @ J[3:6,:].conj().transpose()

    weigv, weigd = ling.eig(Aw)
    weig = math.sqrt(np.diag(weigd))
    [veigv, veigd] = eig(Av)
    veig = math.sqrt(np.diag(veigd))

    weigvs = weigv.copy()
    veigvs = veigv.copy()

    for i in range(0,3):
        weigvs[0:3,i] = R @ weigv[0:3,i]
        veigvs[0:3,i] = R @ veigv[0:3,i]

    for i in range(0,3):
        pw = p + lenfactor * weigvs[0:3,i] * weig[i]
        pv = p + lenfactor * veigvs[0:3,i] * veig[i]

        plot3D(p,pw)
        plot3D(p, pv)

def drawROM(arm, ares,  ax):
    farthestx = []
    farthesty = []
    farthestz = []
    lmin = -180
    lmax = 180

    for i in range(50000):
        print(i/50000*100)
        t = arm.FK(np.random.rand(7) * 2 * np.pi - np.pi)
        ta = fsr.TMtoTAA(t)
        farthestx.append(ta[0])
        farthesty.append(ta[1])
        farthestz.append(ta[2])

    ax.scatter3D(farthestx, farthesty, farthestz, s = 2)

def DrawSTL(tm, fname, ax, scale = 1.0):
    #make sure to install nuumpy-stl and not stl


    t_mesh = mesh.Mesh.from_file(fname)
    for i in range(len(t_mesh.x)):
        for j in range(3):
            t_mesp = fsr.TAAtoTM(np.array([t_mesh.x[i,j], t_mesh.y[i,j], t_mesh.z[i,j], 0, 0, 0]))
            #disp(t_mesh.x[i,j])
            t_new = tm @ t_mesp
            mesp_aa = fsr.TMtoTAA(t_new)
            t_mesh.x[i,j] = mesp_aa[0] * scale
            t_mesh.y[i,j] = mesp_aa[1] * scale
            t_mesh.z[i,j] = mesp_aa[2] * scale


    X = t_mesh.x
    Y = t_mesh.y
    Z = t_mesh.z

    light = LightSource(90, 45)
    illuminated_surface = light.shade(Z, cmap=cm.coolwarm)

    ax.plot_surface(t_mesh.x, t_mesh.y, t_mesh.z, rstride=1, cstride=1, linewidth=0, antialiased=False,
                    facecolors=illuminated_surface)
    #ax.add_collection3d(mplot3d.art3d.Poly3DCollection(t_mesh.vectors))
    #ax.auto_scale_xyz(scale, scale, scale)

def getSTLProps(fname):
    #Return center of Mass, inertia, etc
    mesh = mesh.Mesh.from_file(fname)

    return mesh.get_mass_properties()

def QuadPlot(p1, p2, dim, ax, c = 'b'):
    bl = p1.spawnNew([0, -dim[0]/2, -dim[1]/2, 0, 0, 0])
    br = p1.spawnNew([0, -dim[0]/2, dim[1]/2, 0,  0, 0])
    tl = p1.spawnNew([0, dim[0]/2, -dim[1]/2, 0,  0, 0])
    tr = p1.spawnNew([0, dim[0]/2, dim[1]/2, 0,  0, 0])
    p1a = p1
    p2a = p2
    p1bl = p1 @ bl
    p2bl = p2 @ bl
    p1br = p1 @ br
    p2br = p2 @ br
    p1tl = p1 @ tl
    p2tl = p2 @ tl
    p1tr = p1 @ tr
    p2tr = p2 @ tr
    #Core
    ax.plot3D((p1bl[0], p2bl[0]),(p1bl[1], p2bl[1]),(p1bl[2], p2bl[2]), c)
    ax.plot3D((p1br[0], p2br[0]),(p1br[1], p2br[1]),(p1br[2], p2br[2]), c)
    ax.plot3D((p1tl[0], p2tl[0]),(p1tl[1], p2tl[1]),(p1tl[2], p2tl[2]), c)
    ax.plot3D((p1tr[0], p2tr[0]),(p1tr[1], p2tr[1]),(p1tr[2], p2tr[2]), c)

    #End
    ax.plot3D((p2tl[0], p2bl[0]),(p2tl[1], p2bl[1]),(p2tl[2], p2bl[2]), c)
    ax.plot3D((p2tr[0], p2br[0]),(p2tr[1], p2br[1]),(p2tr[2], p2br[2]), c)
    ax.plot3D((p2bl[0], p2br[0]),(p2bl[1], p2br[1]),(p2bl[2], p2br[2]), c)
    ax.plot3D((p2tl[0], p2tr[0]),(p2tl[1], p2tr[1]),(p2tl[2], p2tr[2]), c)

    #ax.plot3D((p1tl[0], p1bl[0]),(p1tl[1], p1bl[1]),(p1tl[2], p1bl[2]), c)
    #ax.plot3D((p1tr[0], p1br[0]),(p1tr[1], p1br[1]),(p1tr[2], p1br[2]), c)
    #ax.plot3D((p1bl[0], p1br[0]),(p1bl[1], p1br[1]),(p1bl[2], p1br[2]), c)
    #ax.plot3D((p1tl[0], p1tr[0]),(p1tl[1], p1tr[1]),(p1tl[2], p1tr[2]), c)


def DrawArm(arm, ax, jrad = .1, jdia = .3, lens = 1, c = 'grey', forces = np.zeros((1))):
    startind = 0

    while (sum(arm.S[3:6,startind]) == 1):
        startind = startind + 1
    poses = arm.getJointTransforms()
    p = np.zeros((3,len(poses[startind:])))
    for i in range(startind, len(poses[startind:])):
        if poses[i] == None:
            continue
        p[0,i] = (poses[i].TAA[0])
        p[1,i] = (poses[i].TAA[1])
        p[2,i] = (poses[i].TAA[2])
    ax.scatter3D(p[0,:], p[1,:], p[2,:])
    ax.plot3D(p[0,:], p[1,:], p[2,:])
    Dims = np.copy(arm._Dims).T
    dofs = arm.S.shape[1]
    yrot = poses[0].spawnNew([0,0,0,0,np.pi/2,0])
    xrot = poses[0].spawnNew([0,0,0,np.pi/2,0,0])
    zrot = poses[0].spawnNew([0,0,0,0,0,np.pi])
    for i in range(startind, dofs):
        zed = poses[i]
        DrawAxes(zed, lens, ax)

        try:
            #Tp = fsr.tmInterpMidpoint(poses[i], poses[i+1])
            #T = fsr.adjustRotationToMidpoint(Tp ,poses[i], poses[i+1], mode = 1)
            #disp(T)

            #DrawRectangle(T, Dims[i+1,0:3], ax, c = c)
            QuadPlot(poses[i], poses[i+1], Dims[i+1,0:3], ax, c = c)
            if len(forces) != 1:
                label = '%.1fNm' % (forces[i])
                ax.text(poses[i][0], poses[i][1], poses[i][2], label)
            if (arm._jaxes[0,i] == 1):
                if len(forces) != 1:
                    DrawTube(zed @ yrot, jrad, forces[i]/300, ax)
                else:
                    DrawTube(zed @ yrot, jrad, jdia, ax)
            elif (arm._jaxes[1,i] == 1):
                if len(forces) != 1:
                    DrawTube(zed @ xrot, jrad, forces[i]/300, ax)
                else:
                    DrawTube(zed @ xrot, jrad, jdia, ax)
            else:
                if len(forces) != 1:
                    DrawTube(zed @ zrot, jrad, forces[i]/300, ax)
                else:
                    DrawTube(zed @ zrot, jrad, jdia, ax)
        except:
            pass
    zed = poses[0].gTAA()
    if startind ==0:
        DrawRectangle(arm.baseT @ fsr.TAAtoTM(np.array([0, 0, Dims[len(Dims)-1,2]/2, 0, 0, 0])), Dims[len(Dims)-1,0:3], ax, c = c)
    for i in range(len(arm.cameras)):
        DrawCamera(arm.cameras[i][0], 1, ax)

def DrawLine(tf1, tf2, ax, col = 'blue'):
    ax.plot3D([tf1[0], tf2[0]], [tf1[1], tf2[1]], [tf1[2], tf2[2]], col)

def DrawMobilePlatform(pl, ax, col = 'blue'):
    DrawTube(pl.loc @ pl.fl, pl.wrad, .3, ax)
    DrawTube(pl.loc @ pl.fr, pl.wrad, .3, ax)
    DrawTube(pl.loc @ pl.bl, pl.wrad, .3, ax)
    DrawTube(pl.loc @ pl.br, pl.wrad, .3, ax)
    DrawRectangle(pl.loc, pl.dims, ax, col)

def DrawSP(sp, ax, col = 'green', forces = 1):
    for i in range(6):

        ax.plot3D([sp._bJS[0,i], sp._bJS[0,(i+1)%6]],[sp._bJS[1,i], sp._bJS[1,(i+1)%6]], [sp._bJS[2,i],sp._bJS[2,(i+1)%6]], 'blue')
        ax.plot3D([sp._tJS[0,i], sp._tJS[0,(i+1)%6]],[sp._tJS[1,i], sp._tJS[1,(i+1)%6]], [sp._tJS[2,i],sp._tJS[2,(i+1)%6]], 'blue')
        if i == 0:
            ax.plot3D([sp._bJS[0,i], sp._tJS[0,i]],[sp._bJS[1,i], sp._tJS[1,i]], [sp._bJS[2,i], sp._tJS[2,i]], 'darkred')
        elif i == 1:
            ax.plot3D([sp._bJS[0,i], sp._tJS[0,i]],[sp._bJS[1,i], sp._tJS[1,i]], [sp._bJS[2,i], sp._tJS[2,i]], 'salmon')
        else:
            ax.plot3D([sp._bJS[0,i], sp._tJS[0,i]],[sp._bJS[1,i], sp._tJS[1,i]], [sp._bJS[2,i], sp._tJS[2,i]], col)
        if(sp.plateThickness != 0):
            aa = sp.plateTransform.spawnNew([sp._bJS[0,i], sp._bJS[1,i], sp._bJS[2,i], sp.gbottomT()[3], sp.gbottomT()[4], sp.gbottomT()[5]]) @ (-1 * sp.plateTransform)
            ab = sp.plateTransform.spawnNew([sp._bJS[0,(i+1)%6], sp._bJS[1,(i+1)%6], sp._bJS[2,(i+1)%6], sp.gbottomT()[3], sp.gbottomT()[4], sp.gbottomT()[5]]) @ (-1 * sp.plateTransform)
            ba = sp.plateTransform.spawnNew([sp._tJS[0,i], sp._tJS[1,i], sp._tJS[2,i], sp.gtopT()[3], sp.gtopT()[4], sp.gtopT()[5]]) @ (sp.plateTransform)
            bb = sp.plateTransform.spawnNew([sp._tJS[0,(i+1)%6], sp._tJS[1,(i+1)%6], sp._tJS[2,(i+1)%6], sp.gtopT()[3], sp.gtopT()[4], sp.gtopT()[5]]) @ (sp.plateTransform)
            ax.plot3D([aa[0], ab[0]],[aa[1], ab[1]],[aa[2], ab[2]], 'blue')
            ax.plot3D([ba[0], bb[0]],[ba[1], bb[1]],[ba[2], bb[2]], 'blue')
            ax.plot3D([sp._bJS[0,i], aa[0]],[sp._bJS[1,i], aa[1]],[sp._bJS[2,i], aa[2]], 'blue')
            ax.plot3D([sp._tJS[0,i], ba[0]],[sp._tJS[1,i], ba[1]],[sp._tJS[2,i], ba[2]], 'blue')

    if forces == 1 and sp.legForces.size > 1:
        for i in range(6):
            label = '%.1fN' % (sp.legForces[i])
            if i % 2 == 0:
                pos = sp.getActuatorLoc(i, 'b')
            else:
                pos = sp.getActuatorLoc(i, 't')
            ax.text(pos[0], pos[1], pos[2], label)

def DrawInterPlate(sp1, sp2, ax, col):

        for i in range(6):
            aa = sp1.plateTransform.spawnNew([sp1._tJS[0,i], sp1._tJS[1,i], sp1._tJS[2,i], sp1.gtopT()[3], sp1.gtopT()[4], sp1.gtopT()[5]]) @ (sp1.plateTransform)
            ab = sp1.plateTransform.spawnNew([sp1._tJS[0,(i+1)%6], sp1._tJS[1,(i+1)%6], sp1._tJS[2,(i+1)%6], sp1.gtopT()[3], sp1.gtopT()[4], sp1.gtopT()[5]]) @ (sp1.plateTransform)
            ba = sp2.plateTransform.spawnNew([sp2._bJS[0,i], sp2._bJS[1,i], sp2._bJS[2,i], sp2.gbottomT()[3], sp2.gbottomT()[4], sp2.gbottomT()[5]]) @ (-1 * sp2.plateTransform)
            bb = sp2.plateTransform.spawnNew([sp2._bJS[0,(i+1)%6], sp2._bJS[1,(i+1)%6], sp2._bJS[2,(i+1)%6], sp2.gbottomT()[3], sp2.gbottomT()[4], sp2.gbottomT()[5]]) @ (-1 * sp2.plateTransform)
            #ax.plot3D([aa[0], ab[0]],[aa[1], ab[1]],[aa[2], ab[2]], 'g')
            #ax.plot3D([ba[0], bb[0]],[ba[1], bb[1]],[ba[2], bb[2]], 'g')
            ax.plot3D([sp2._bJS[0,i], aa[0]],[sp2._bJS[1,i], aa[1]],[sp2._bJS[2,i], aa[2]], 'g')
            ax.plot3D([sp1._tJS[0,i], ba[0]],[sp1._tJS[1,i], ba[1]],[sp1._tJS[2,i], ba[2]], 'g')
            #ax.plot3D([sp2._bJS[0,i], ab[0]],[sp2._bJS[1,i], ab[1]],[sp2._bJS[2,i], ab[2]], 'g')
            #ax.plot3D([sp1._tJS[0,i], bb[0]],[sp1._tJS[1,i], bb[1]],[sp1._tJS[2,i], bb[2]], 'g')

def DrawAssembler(spl, ax, col = 'green', forces = 1):
    for i in range(spl.numsp):
        DrawSP(spl.splist[i], ax , col, forces)
        if i + 1 < spl.numsp:
            DrawInterPlate(spl.splist[i], spl.splist[i+1], ax, col)

def DrawCamera(cam, size, ax):
    DrawAxes(cam.CamT, size/2, ax)
    ScreenLoc = cam.CamT @ fsr.TAAtoTM(np.array([0, 0, size, 0, 0, 0]))
    imgT = cam.getFrameSize(size)
    print(imgT)
    Scr = np.zeros((4,3))
    t = ScreenLoc @ fsr.TAAtoTM(np.array([-imgT[0], imgT[1], 0, 0, 0, 0]))
    Scr[0,0:3] = t[0:3].flatten()
    t = ScreenLoc @ fsr.TAAtoTM(np.array([imgT[0], imgT[1], 0, 0, 0, 0]))
    Scr[1,0:3] = t[0:3].flatten()
    t = ScreenLoc @ fsr.TAAtoTM(np.array([-imgT[0], -imgT[1], 0, 0, 0, 0]))
    Scr[3,0:3] = t[0:3].flatten()
    t = ScreenLoc @ fsr.TAAtoTM(np.array([imgT[0], -imgT[1], 0, 0, 0, 0]))
    Scr[2,0:3] = t[0:3].flatten()
    for i in range(4):
        ax.plot3D((cam.CamT[0],Scr[i, 0]), (cam.CamT[1],Scr[i, 1]),(cam.CamT[2],Scr[i, 2]), 'green')
    ax.plot3D(np.hstack((Scr[0:4,0], Scr[0,0])), np.hstack((Scr[0:4,1], Scr[0,1])), np.hstack((Scr[0:4,2], Scr[0,2])), 'red')

def DrawAxes(zed, lv, ax, makelegend = None, zdir = None):
    zx, zy, zz = zed.tripleUnit(lv)
    poses = zed.gTAA().flatten()
    if makelegend is not None:
        if zdir is not None:
            zed = zed @ zdir
        ax.text(zed[0],zed[1],zed[2], makelegend)
    ax.plot3D([poses[0], zx[0]], [poses[1], zx[1]], [poses[2], zx[2]], 'red')
    ax.plot3D([poses[0], zy[0]], [poses[1], zy[1]], [poses[2], zy[2]], 'blue')
    ax.plot3D([poses[0], zz[0]], [poses[1], zz[1]], [poses[2], zz[2]], 'green')

def DrawTrussElement(T, L, R, ax, c='blue', c2 = 'blue', hf = False, delt = .5, RB = .1):
    if hf == True:
        R1 = T @ T.spawnNew([R, 0, 0, 0, 0, 0])
        R2 = T @ T.spawnNew([0, 0, 0, 0, 0, 2*np.pi/3]) @ T.spawnNew([R, 0, 0, 0, 0, 0])
        R3 = T @ T.spawnNew([0, 0, 0, 0, 0, 4*np.pi/3]) @ T.spawnNew([R, 0, 0, 0, 0, 0])
        R1 = R1 @ T.spawnNew([0, 0, -L/2, 0, 0, 0])
        R2 = R2 @ T.spawnNew([0, 0, -L/2, 0, 0, 0])
        R3 = R3 @ T.spawnNew([0, 0, -L/2, 0, 0, 0])
        for i in range(int(L/delt)):
            R1A = R1 @ T.spawnNew([0, 0, delt, 0, 0, 0])
            R2A = R2 @ T.spawnNew([0, 0, delt, 0, 0, 0])
            R3A = R3 @ T.spawnNew([0, 0, delt, 0, 0, 0])
            if cycle ==1:
                DrawTube(fsr.adjustRotationToMidpoint(
                    fsr.tmInterpMidpoint(R1, R2A), R1, R2A, mode=1),
                    fsr.distance(R1, R2A)-RB, RB/3, ax, c2, res = 3)
                DrawTube(fsr.adjustRotationToMidpoint(
                    fsr.tmInterpMidpoint(R2, R3A), R2, R3A, mode=1),
                    fsr.distance(R2, R3A)-RB, RB/3, ax, c2, res = 3)
                DrawTube(fsr.adjustRotationToMidpoint(
                    fsr.tmInterpMidpoint(R3, R1A), R3, R1A, mode=1),
                    fsr.distance(R3, R1A)-RB, RB/3, ax, c2, res = 3)
                R1 = R1A
                R2 = R2A
                R3 = R3A
            else:
                DrawTube(fsr.adjustRotationToMidpoint(
                    fsr.tmInterpMidpoint(R1, R3A), R1, R3A, mode=1),
                    fsr.distance(R1, R3A)-RB, RB/3, ax, c2, res = 3)
                DrawTube(fsr.adjustRotationToMidpoint(
                    fsr.tmInterpMidpoint(R2, R1A), R2, R1A, mode=1),
                    fsr.distance(R2, R1A)-RB, RB/3, ax, c2, res = 3)
                DrawTube(fsr.adjustRotationToMidpoint(
                    fsr.tmInterpMidpoint(R3, R2A), R3, R2A, mode=1),
                    fsr.distance(R3, R2A)-RB, RB/3, ax, c2, res = 3)
                R1 = R1A
                R2 = R2A
                R3 = R3A
            cycle*=-1
        DrawTube(fsr.adjustRotationToMidpoint(fsr.tmInterpMidpoint(R1, R2), R1, R2, mode=1),
            fsr.distance(R1, R2)-RB, RB/3, ax, 'r', res = 3)
        DrawTube(fsr.adjustRotationToMidpoint(fsr.tmInterpMidpoint(R2, R3), R2, R3, mode=1),
            fsr.distance(R2, R3)-RB, RB/3, ax, 'r', res = 3)
        DrawTube(fsr.adjustRotationToMidpoint(fsr.tmInterpMidpoint(R3, R1), R3, R1, mode=1),
            fsr.distance(R3, R1)-RB, RB/3, ax, 'r', res = 3)
    R1 = T @ T.spawnNew([R, 0, 0, 0, 0, 0])
    R2 = T @ T.spawnNew([0, 0, 0, 0, 0, 2*np.pi/3]) @ T.spawnNew([R, 0, 0, 0, 0, 0])
    R3 = T @ T.spawnNew([0, 0, 0, 0, 0, 4*np.pi/3]) @ T.spawnNew([R, 0, 0, 0, 0, 0])
    DrawTube(R1, L, RB, ax, c, res = 3)
    DrawTube(R2, L, RB, ax, c, res = 3)
    DrawTube(R3, L, RB, ax, c, res = 3)

def DrawQTrussElement(T, L, R, ax, c='blue', c2 = 'blue', hf = False, delt = .5, RB = .1):
    R1 = T @ T.spawnNew([0, 0, 0, 0, 0, np.pi/4]) @ T.spawnNew([R, 0, 0, 0, 0, 0])
    R2 = T @ T.spawnNew([0, 0, 0, 0, 0, np.pi/2+np.pi/4]) @ T.spawnNew([R, 0, 0, 0, 0, 0])
    R3 = T @ T.spawnNew([0, 0, 0, 0, 0, np.pi+np.pi/4]) @ T.spawnNew([R, 0, 0, 0, 0, 0])
    R4 = T @ T.spawnNew([0, 0, 0, 0, 0, -np.pi/4]) @ T.spawnNew([R, 0, 0, 0, 0, 0])
    DrawTube(R1, L, RB, ax, c, res = 3)
    DrawTube(R2, L, RB, ax, c, res = 3)
    DrawTube(R3, L, RB, ax, c, res = 3)
    DrawTube(R4, L, RB, ax, c, res = 3)

def DrawRectangle(T, dims, ax, c='grey', a = 0.1):
    dx = dims[0]
    dy = dims[1]
    dz = dims[2]
    #                         BBL            BBR             BFL           BFR            TBL            TBR            TFL           TFR
    corners = .5 * np.array([[-dx,-dy,-dz],[dx, -dy, -dz],[-dx, dy, -dz],[dx, dy, -dz],[-dx, -dy, dz],[dx, -dy, dz],[-dx, dy, dz],[dx, dy, dz]]).T
    Tc = np.zeros((3,8))
    for i in range(0,8):
        h = T.gTM() @ np.array([corners[0,i],corners[1,i],corners[2,i],1]).T
        Tc[0:3,i] = np.squeeze(h[0:3])
    #segs = np.array([[1, 2],[1, 3],[2, 4],[3, 4],[1, 5],[2, 6],[3, 7],[4, 8],[5, 6],[5, 7],[6, 8],[7,8]])-1
    #disp(Tc[0,(0,1,4,5)])
    #disp(Tc[0,(0,1,4,5)])
    #disp(Tc[2,(0,1,4,5)])
    #randomarr = np.random.rand(4)/100
    #print(randomarr)
    verts = [Tc[:,(0, 1, 3, 2)].T, Tc[:,(4, 5, 7, 6)].T, Tc[:,(0,1,5,4)].T,
    Tc[:,(2, 3, 7, 6)].T, Tc[:,(0, 2, 6, 4)].T, Tc[:,(1,3,7,5)].T]
    ax.add_collection3d(Poly3DCollection(verts, facecolors = c, edgecolors='b', alpha = a))
    #yy, zz = np.meshgrid(Tc[1,:], Tc[2,:])
    #ax.plot_surface(xx, yy, zz)
    #xs = np.linspace(0, 10, 100)
    #zs = np.linspace(0, 10, 100)

    #X, Z = np.meshgrid(Tc[0,:], Tc[2,:])
    #Y, Z = np.meshgrid(Tc[1,:], Tc[2,:])
    #Y = 5 - X
    #ax.plot_surface(X, Y, Z, alpha = .5, color = c)


def DrawRegPoly(T, n, r, h, ax, c='grey', rot = False):
    screw = T.gTAA().reshape((6))
    x = screw[0]
    y = screw[1]
    z = screw[2]
    xs = []
    ys = []
    zb = z-h/2
    zu = z+h/2
    xus=[]
    yus=[]
    zbs=[]
    zus=[]
    disp(r)
    disp(h)
    disp(T)
    for i in range(n):
        if rot:
            xs.append(r * np.cos(2 * (np.pi * i / n + np.pi * 1 / (2*n))))
            ys.append(r * np.sin(2 * (np.pi * i / n + np.pi * 1 / (2*n))))
        else:
            xs.append(r * np.cos(2 * np.pi * i / n))
            ys.append(r * np.sin(2 * np.pi * i / n))
    for i in range(n):
        hb = (T @ T.spawnNew(np.array([xs[i], ys[i], zb, 0, 0, 0]))).gTAA()
        ht = (T @ T.spawnNew(np.array([xs[i], ys[i], zu, 0, 0, 0]))).gTAA()
        xs[i] = hb[0].squeeze()
        ys[i] = hb[1].squeeze()
        xus.append(ht[0].squeeze())
        yus.append(ht[1].squeeze())
        zbs.append(hb[2].squeeze())
        zus.append(ht[2].squeeze())
    for i in range(n+1):
        if i == 0:
            continue
        if i == n:
            ax.plot3D((xs[i-1], xs[0]), (ys[i-1], ys[0]), (zbs[i-1], zbs[0]), c)
            ax.plot3D((xus[i-1], xus[0]), (yus[i-1], yus[0]), (zus[i-1], zus[0]), c)
        else:
            ax.plot3D((xs[i-1], xs[i]), (ys[i-1], ys[i]), (zbs[i-1], zbs[i]), c)
            ax.plot3D((xus[i-1], xus[i]), (yus[i-1], yus[i]), (zus[i-1], zus[i]), c)
        ax.plot3D((xs[i-1], xus[i-1]), (ys[i-1], yus[i-1]), (zbs[i-1], zus[i-1]), c)

def DrawCore(core, ax, c='grey', size = .5):
    DrawRegPoly(core.pos, 8, core.radius, core.height, ax, c, True)
    for i in range(6):
        DrawTube(core.attachmentTMs[i], .1, core.height/2, ax, c = 'purple')
        DrawAxes(core.attachmentTMs[i], .2, ax)
    for i in range(len(core.cameras)):
        DrawCamera(core.cameras[i], size, ax)
    for i in range(6):
        if core.attached[i] != 0:
            core.attached[i].Draw(ax)

def MakeVideo(dir = "VideoTemp"):
    os.chdir(dir)
    os.system("ffmpeg -r 30 -i img%04d.png -vcodec mpeg4 -qscale 0 -y movie.mp4")
    #for file_name in glob.glob("*.png"):
    #    os.remove(file_name)

def Animate(obj, ax, plt, k, i, framelimiter,folder = 'VideoTemp', limits=[[-7,7],[-7,7],[0,8]]):
    if i % framelimiter == 0:
        ax = plt.axes(projection = '3d')
        ax.set_xlim3d(limits[0][0],limits[0][1])
        ax.set_ylim3d(limits[1][0],limits[2][1])
        ax.set_zlim3d(limits[2][0],limits[2][1])
        obj.Draw(ax)
        plt.show()
        plt.savefig(folder + '/file%05d' % k)
        ax.clear()
        k = k + 1
    return k, ax, plt

def AnimateCoreIndices(thetas, indices, core, ax, plt, k, framelimiter, title = "", folder = 'VideoTemp', limits=[[-7,7],[-7,7],[0,8]]):
    maxes = []
    for i in range(len(thetas)):
        maxes.append(len(thetas[i]))
    lim = max(maxes)
    for i in range(lim):
        progressBar(i, lim, title)
        c = 0
        for j in indices:
            try:
                core.attached[j].FK(thetas[c][i])
            except:
                print("fail")
            c = c + 1
            k, ax, plt = Animate(core, ax, plt, k, i, 12)

    return k, ax, plt

def DrawRRT(listPoints, ax):
    for i in range(len(listPoints)):
        temp = listPoints[i].object.getPosition()
        ax.scatter3D(temp[0], temp[1], temp[2], s = 3)
    for i in range(len(listPoints)):
        temp1 = listPoints[i].object.getPosition()
        if listPoints[i].object.getParent() == None:
            DrawRectangle(temp1, [.05, .05, .05], ax, 'b')
            continue
        temp2 = listPoints[i].object.getParent().getPosition()
        c = 'green'
        if  listPoints[i].object.type == 1 and  listPoints[i].object.getParent().type == 1:
            c = 'm'
            continue
        elif listPoints[i].object.type == 0 and listPoints[i].object.getParent().type == 0:
            c = 'blue'
        ax.plot3D([temp1[0], temp2[0]], [temp1[1], temp2[1]], [temp1[2], temp2[2]], c)

def DrawRRTPath(listPoints, ax, col = 'red'):
    DrawRectangle(listPoints[0], [.1, .1, .1], ax, 'b')
    DrawRectangle(listPoints[len(listPoints)-1], [.1, .1, .1], ax, 'r', )
    for i in range(len(listPoints) - 1):
        temp1 = listPoints[i]
        temp2 = listPoints[i+1]
        ax.plot3D([temp1[0], temp2[0]], [temp1[1], temp2[1]], [temp1[2], temp2[2]], col)

def DrawObstructions(listObs, ax, col = 'red', a = .1):
    for obs in listObs:
        center = obs[1].spawnNew([(obs[1][0] + obs[0][0])/2, (obs[1][1] + obs[0][1])/2, (obs[1][2] + obs[0][2])/2, 0, 0, 0])
        dims = [(obs[1][0] - obs[0][0]), (obs[1][1] - obs[0][1]), (obs[1][2] - obs[0][2])]
        DrawRectangle(center, dims, ax, col, a)

def DrawWrench(tr, weight, dir, ax):
    trb = tr.spawnNew([tr[0], tr[1], tr[2], 0, 0, 0])
    other = tr.spawnNew([dir[0], dir[1], dir[2], 0, 0, 0])
    np = trb @ (.4*other)
    a = trb @ (.3*other)
    DrawRectangle(trb, [.1, .1, .1], ax)
    a1 = a @ tr.spawnNew([.05, 0, 0, 0, 0, 0])
    a2 = a @ tr.spawnNew([-.05, 0, 0, 0, 0, 0])
    a3 = a @ tr.spawnNew([0, -.05,  0, 0, 0, 0])
    a4 = a @ tr.spawnNew([0, .05, 0, 0, 0, 0])
    label = '%.1fN' % weight
    ax.text(tr[0], tr[1], tr[2], label)

    ax.plot3D([tr[0], np[0]], [tr[1], np[1]], [tr[2], np[2]], 'b')
    ax.plot3D([np[0], a1[0]],[np[1], a1[1]],[np[2], a1[2]], 'r')
    ax.plot3D([np[0], a2[0]],[np[1], a2[1]],[np[2], a2[2]] ,'r')
    ax.plot3D([np[0], a3[0]],[np[1], a3[1]],[np[2], a3[2]] ,'r')
    ax.plot3D([np[0], a4[0]],[np[1], a4[1]],[np[2], a4[2]] ,'r')

def DrawTube(T, height, r, ax, c = 'blue', res = 12):
    # find points along x and y axes
    points  = np.linspace(0,2*np.pi,res+1)
    x = np.cos(points)*r
    y = np.sin(points)*r

    # find points along z axis
    rpoints = np.atleast_2d(np.linspace(0,1,1))
    z = np.ones((res+1))*height/2
    tres = np.zeros((6,len(x)))
    tres2 = np.zeros((6,len(x)))
    for i in range(len(x)):
        #disp(i)
        tres[0:6,i] = (T @ T.spawnNew([x[i], y[i], z[i], 0, 0, 0])).TAA.flatten()
        tres2[0:6,i] = (T @ T.spawnNew([x[i], y[i], -z[i], 0, 0, 0])).TAA.flatten()
        bx = np.array([tres[0,i], tres2[0,i]], dtype=object)
        by = np.array([tres[1,i], tres2[1,i]], dtype=object)
        bz = np.array([tres[2,i], tres2[2,i]], dtype=object)
        ax.plot3D(bx, by, bz, c)
    ax.plot3D(tres[0,:], tres[1,:],tres[2,:], c)
    ax.plot3D(tres2[0,:], tres2[1,:],tres2[2,:], c)
