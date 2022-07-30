#!/usr/bin/python3

import os
import pprint
import tkinter as tk
from tkinter import messagebox as tkmsg
from Xlib import display as X


pp = pprint.PrettyPrinter(indent=2,compact=True)
wnd = None
disp = None

dpmm = 96
if 'DPI' in os.environ.keys():
    dpmm = int(os.environ.get('DPI'))
dpmm /= 25.4

def setTitle():
    if wnd:
        wnd.title("Xrandr %d.%d %s/%d (%dx%d) (%dmmx%dmm)" % (
            randrVer['major_version'], randrVer['minor_version'],
            disp.get_display_name(), disp.get_default_screen(),
            scrn.width_in_pixels, scrn.height_in_pixels,
            scrn.width_in_mms, scrn.height_in_mms)
        )

def initDisplay():
    global disp, scrn
    if disp != None:
        disp.close()
    disp = X.Display()
    scrn = disp.screen()
    print(disp)
    setTitle()

initDisplay()

randrVer = disp.xrandr_query_version()._data
print("RandR: " + str(randrVer))

crtcs = dict()
outputs = dict()
modes = dict()

sres = None
priOut = -1


def setScreenSize(minX = 0, minY = 0, dX = 0, dY = 0):
    maxX = minX + dX
    maxY = minY + dY
    sext = scrn.root.xrandr_get_screen_size_range()
    
    for crtc in crtcs.values():
        if crtc['outputs']:
            minX = min(minX, crtc['x'])
            minY = min(minY, crtc['y'])
            maxX = max(maxX, crtc['x'] + crtc['width'])
            maxY = max(maxY, crtc['y'] + crtc['height'])
    
    extX = maxX - minX
    extY = maxY - minY
    
    print("CFG: %d %dx%d (%d-%dx%d-%d)" % (sres.config_timestamp, extX, extY, sext.min_width, sext.max_width, sext.min_height, sext.max_height))
    
    if (extX != scrn.width_in_pixels or extY != scrn.height_in_pixels) \
            and extX >= sext.min_width and extX <= sext.max_width \
            and extY >= sext.min_height and extY <= sext.max_height:
        scrn.root.xrandr_set_screen_size(extX, extY, int(extX / dpmm), int(extY / dpmm))
        disp.sync()
        initDisplay()


def procScreenRes(withModes=False, setScreen=False, setPrimary=None):
    global sres, priOut
    
    print("Screen: %dx%d %dmmx%dmm" % (scrn.width_in_pixels, scrn.height_in_pixels, scrn.width_in_mms, scrn.height_in_mms))
    
    sres = scrn.root.xrandr_get_screen_resources()
    
    if setPrimary != None:
        scrn.root.xrandr_set_output_primary(setPrimary)
    priOut = scrn.root.xrandr_get_output_primary().output
    
    for crtcid in sres.crtcs:
        crtcs[crtcid] = disp.xrandr_get_crtc_info(crtcid, sres.config_timestamp)._data
    
    print("CRTCs:")
    pp.pprint(crtcs)
    
    for outid in sres.outputs:
        outputs[outid] = disp.xrandr_get_output_info(outid, sres.config_timestamp)._data
    
    print("Outputs:")
    pp.pprint(outputs)
    
    if withModes:
        i = 0
        for mode in sres.modes:
            modeInfo = mode._data
            modeInfo['name'] = sres.mode_names[i:i + mode.name_length]
            modeInfo['rate'] = mode.dot_clock / (mode.h_total * mode.v_total)
            modes[mode.id] = modeInfo
            i += mode.name_length

        print("Modes:")
        pp.pprint(modes)
    
    if setScreen:
        setScreenSize()


procScreenRes(withModes=True)

wnd = tk.Tk()
setTitle()

curOut = -1
btnsOut = dict()
btnsMode = dict()
btnRotate = dict()
btnsPos = dict()


def selOutput(selid):
    global curOut
    
    for outid, btnOut in btnsOut.items():
        btnOut.configure(bg=('gray' if selid == outid else 'lightgray'))
    
    for modeid, btnMode in btnsMode.items():
        if modeid > 0:
            btnMode.configure(bg='beige', fg=('black' if modeid in outputs[selid]['modes'] else 'darkgray'), state=tk.NORMAL)
    btnsMode[0].configure(state=tk.NORMAL)
    
    if outputs[selid]['num_preferred'] > 0:
        btnsMode[outputs[selid]['modes'][outputs[selid]['num_preferred'] - 1]].configure(bg='lightgreen')
    
    if outputs[selid]['crtc'] > 0:
        btnsMode[crtcs[outputs[selid]['crtc']]['mode']].configure(bg='yellow')
    
    for nRotate, rtbtn in btnRotate.items():
        rtbtn.configure(
            state=(tk.NORMAL if outputs[selid]['crtc'] > 0 and crtcs[outputs[selid]['crtc']]['possible_rotations'] & nRotate else tk.DISABLED),
            bg=('LightSkyBlue' if outputs[selid]['crtc'] > 0 and crtcs[outputs[selid]['crtc']]['rotation'] & nRotate else 'LightSteelBlue')
        )
    
    for lblPos, btnPos in btnsPos.items():
        if lblPos == 'primary':
            btnPos.configure(bg='gold' if priOut == selid else 'khaki', state=tk.NORMAL if outputs[selid]['crtc'] > 0 else tk.DISABLED)
        else:
            if lblPos == 'origin':
                btnPos.configure(text=(lblPos + " +%dx%d" % (crtcs[outputs[selid]['crtc']]['x'], crtcs[outputs[selid]['crtc']]['y']))
                    if outputs[selid]['crtc'] > 0 else lblPos)
            
            btnPos.configure(state=tk.DISABLED if not outputs[selid]['crtc'] > 0 \
                or lblPos != 'origin' and (selid == priOut or not priOut > 0) else tk.NORMAL)
    
    curOut = selid


def setCRTC(crtcid, x=None, y=None, mode=None, r=None, out=None, setScreen=True):
    if x == None: x = crtcs[crtcid]['x']
    if y == None: y = crtcs[crtcid]['y']
    if r == None: r = crtcs[crtcid]['rotation']
    if out == None: out = crtcs[crtcid]['outputs'][0]
    if (mode and not mode in outputs[out]['modes']):
        if tkmsg.askokcancel(master=wnd, icon=tkmsg.WARNING, default=tkmsg.CANCEL,
                message='The selected mode is not known to be supported by this output.\nIt might be possible to use it anyway but the results may as well be catastrophic!') \
            and tkmsg.askyesno(master=wnd, default=tkmsg.NO,
                message='Really force mode %s@%.3fHz to be used on %s?' % (modes[mode]['name'], modes[mode]['rate'], outputs[out]['name'])):
            disp.xrandr_add_output_mode(out, mode)
        else:
            return
    if (mode and setScreen):
        setScreenSize(minX = crtcs[crtcid]['x'], minY = crtcs[crtcid]['y'],
            dX = modes[mode]['height'] if r & 10 else modes[mode]['width'],
            dY = modes[mode]['width'] if r & 10 else modes[mode]['height']
        )
    disp.xrandr_set_crtc_config(crtcid, sres.config_timestamp, x, y,
        crtcs[crtcid]['mode'] if mode == None else mode, r, [] if not out else [out]
    )
    procScreenRes(setScreen=setScreen, setPrimary=0 if mode == 0 and priOut in crtcs[crtcid]['outputs'] else None)
    if (out == curOut or out == 0):
        selOutput(curOut)


def setMode(modeid):
    selcrtc = outputs[curOut]['crtc']
    if selcrtc == 0:
        for crtcid in outputs[curOut]['crtcs']:
            if not crtcs[crtcid]['outputs']:
                selcrtc = crtcid
                break
    print("SET: %d %d" % (selcrtc, modeid))
    if selcrtc > 0:
        setCRTC(selcrtc, mode=modeid, out=curOut if modeid != 0 else 0)


def setRotation(fRotate):
    crtcid = outputs[curOut]['crtc']
    if crtcid > 0:
        (setScreen, rotate) = fRotate(crtcs[crtcid]['rotation'])
        if setScreen:
            mext = max(crtcs[crtcid]['width'], crtcs[crtcid]['height'])
            setScreenSize(dX=crtcs[crtcid]['x'] + mext, dY=crtcs[crtcid]['y'] + mext)
        setCRTC(crtcid, r=rotate)


def setPos(fPos):
    selcrtc = outputs[curOut]['crtc']
    if selcrtc > 0:
        cencrtc = crtcs[outputs[priOut]['crtc']] if priOut > 0 else None
        posX = 0
        posY = 0
        if fPos:
            posX, posY = fPos(cencrtc, crtcs[selcrtc]) if fPos else (0, 0)
            if priOut > 0:
                posX += cencrtc['x']
                posY += cencrtc['y']
        print("POS: %d %dx%d" % (selcrtc, posX, posY))
        setScreenSize(minX=posX, minY=posY, dX=crtcs[selcrtc]['width'], dY=crtcs[selcrtc]['height'])
        moveX = posX
        moveY = posY
        for crtcid, crtc in crtcs.items():
            if crtcid != selcrtc and crtc['outputs']:
                moveX = min(moveX, crtc['x'])
                moveY = min(moveY, crtc['y'])
        print("MOVE: %dx%d" % (moveX, moveY))
        setCRTC(selcrtc, x=posX - moveX, y=posY - moveY, setScreen=False)
        if moveX != 0 or moveY != 0:
            for crtcid, crtc in crtcs.items():
                if crtcid != selcrtc and crtc['outputs']:
                    setCRTC(crtcid, x=crtc['x'] - moveX, y=crtc['y'] - moveY, setScreen=False)
        procScreenRes(setScreen=True)


def setPrimary():
    procScreenRes(setPrimary=curOut if curOut != priOut else 0)
    selOutput(curOut)


# Outputs

frmOutputs = tk.Frame(wnd)
frmOutputs.pack(expand=True, fill=tk.X)

for outid, out in outputs.items():
    btnsOut[outid] = tk.Button(frmOutputs, text=out['name'], bg='lightgray', command=lambda n=outid: selOutput(n))
    btnsOut[outid].pack(expand=True, fill=tk.X, side=tk.LEFT)


# Modes

frmModes = tk.Frame(wnd)
frmModes.pack(expand=True, fill=tk.X)

def placeModeButton(btn, n):
    btn.grid(row=int(n / 4), column=n % 4, sticky=tk.EW)

nMode = 0
for modeid, mode in modes.items():
    btnsMode[modeid] = tk.Button(
        frmModes, bg='beige', state=tk.DISABLED,
        text=('%s: %d x %d @ %6.3fHz' % (mode['name'], mode['width'], mode['height'], mode['rate'])),
        command=lambda n=modeid: setMode(n)
    )
    placeModeButton(btnsMode[modeid], nMode)
    nMode += 1
btnsMode[0] = tk.Button(frmModes, text='OFF', state=tk.DISABLED, command=lambda: setMode(0))
placeModeButton(btnsMode[0], nMode)


# Rotation

frmRotate = tk.Frame(wnd)
frmRotate.pack(expand=True, fill=tk.X)

nRotate = 1
for lblRotate in [
    ['normal', lambda r: (True, r & ~0xf | 1)],
    ['turned left', lambda r: (True, r & ~0xf | 2)],
    ['inverted', lambda r: (True, r & ~0xf | 4)],
    ['turned right', lambda r: (True, r & ~0xf | 8)],
    ['mirror x-axis', lambda r: (False, r ^ 16)],
    ['mirror y-axis', lambda r: (False, r ^ 32)]
]:
    btnRotate[nRotate] = tk.Button(frmRotate, text=lblRotate[0], bg='LightSteelBlue',
        command=lambda f=lblRotate[1]: setRotation(f), state=tk.DISABLED
    )
    btnRotate[nRotate].pack(expand=True, fill=tk.X, side=tk.LEFT)
    nRotate = nRotate * 2


# Position

frmPos = tk.Frame(wnd)
frmPos.pack(expand=True, fill=tk.X)

btnsPos['primary'] = tk.Button(frmPos, text='PRIMARY',bg='khaki', state=tk.DISABLED, command=setPrimary)
btnsPos['primary'].pack(expand=True, fill=tk.X, side=tk.LEFT)

for lblPos in [
    ['origin', None],
    ['clone', lambda cen, cur: (0, 0)],
    ['left of', lambda cen, cur: (-cur['width'], int((cen['height'] - cur['height']) / 2))],
    ['right of', lambda cen, cur: (cen['width'], int((cen['height'] - cur['height']) / 2))],
    ['above', lambda cen, cur: (int((cen['width'] - cur['width']) / 2), -cur['height'])],
    ['below', lambda cen, cur: (int((cen['width'] - cur['width']) / 2), cen['height'])]
]:
    btnsPos[lblPos[0]] = tk.Button(frmPos, text=lblPos[0], bg='khaki', command=lambda f=lblPos[1]: setPos(f), state=tk.DISABLED)
    btnsPos[lblPos[0]].pack(expand=True, fill=tk.X, side=tk.LEFT)


wnd.mainloop()
