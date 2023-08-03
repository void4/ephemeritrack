""" https://sagecell.sagemath.org/
	Retrieve vector data from Horizons for one or more target bodies
    relative to an observation center, and thence plot the trajectories
    in 3D using Bézier curves. 

    Written by PM 2Ring 2022.07.11
    adapted by void4 2023 Jul 16
""" 

import re, requests
from functools import lru_cache
from itertools import product
from datetime import datetime, timezone

url = "https://ssd.jpl.nasa.gov/api/horizons_file.api"
api_version = "1.0" 

base_cmd = """
MAKE_EPHEM=YES
OBJ_DATA=NO
REF_SYSTEM=ICRF
EPHEM_TYPE=VECTORS
VEC_TABLE=2
!VEC_CORR=NONE
VEC_LABELS=NO
!VEC_DELTA_T=NO
!OUT_UNITS=KM-D
CSV_FORMAT=YES
""" 

@lru_cache(maxsize=int(20))
def fetch_data(target, center, plane, start, stop, step):
    cmd = f"""
COMMAND='{target}'
CENTER='{center}'
REF_PLANE='{plane}'
START_TIME='{start}'
STOP_TIME='{stop}'
STEP_SIZE='{step}'
"""
    cmd = f"!$$SOF{cmd}{base_cmd}!$$EOF"
    #print(cmd)
    req = requests.post(url, data={'format': 'text'}, files={'input': ('cmd', cmd)})
    version = re.search(r"API VERSION:\s*(\S*)", req.text).group(1)
    if version != api_version:
        print(f"Warning: API version is {version}, but this script is for {api_version}") 

    m = re.search(r"(?s)\$\$SOE(.*)\$\$EOE", req.text)
    if m is None:
        print("NO EPHEMERIS")
        print(req.text)
        return None
    data = m.group(1)[1:] 

    #print(req.text)
    #print('% ' * 40)
    lines = req.text.splitlines()
    #print("\n".join(lines[5:15])) 

    ref = re.search(r"(?si)REFERENCE FRAME AND COORDINATES(.*)\s*Symbol meaning", req.text).group(1)
    print("Reference Frame :", ref)
    return data 

def extract_data(data, get_dates=False, obs_start=None, obs_end=None):
    data = data.splitlines()
    data = [s.split(',')[:-1] for s in data]
    #for row in data: print(row) 

    start_obs = datetime.strptime(obs_start, "%Y-%b-%d %H:%M").replace(tzinfo=timezone.utc)
    end_obs = datetime.strptime(obs_end, "%Y-%b-%d %H:%M").replace(tzinfo=timezone.utc)
    
    pos, tgt, dates, colors = [], [], [], []
    for row in data:
        if get_dates:
            dates.append(f"{row[1]} {float(row[0])}")
            extracted = row[1].split(" ", 2)[2].split(".")[0]
            #print("Extracted:", row[1], extracted)
            if start_obs and end_obs and start_obs <= datetime.strptime(extracted, "%Y-%b-%d %H:%M:%S").replace(tzinfo=timezone.utc) <= end_obs:
                colors.append("red")
            else:
                colors.append("yellow")
        # Extract position & velocity
        row = [float(u) for u in row[2:]]
        pos.append(vector(row[:3]))
        tgt.append(vector(row[3:]).normalized())
    return pos, tgt, dates, colors

# Build Bezier curves
def bez(pos, tgt):
    pos_tgt = zip(pos, tgt)
    p0, t0 = next(pos_tgt)
    row = [p0]
    curves = []
    for p, t in pos_tgt:
        s = abs(p - p0) / 3
        row.extend([p0 + t0*s, p - t*s, p])
        curves.append(row)
        row = []
        p0, t0 = p, t
    return curves 

# Draw a 3D box, with opposite corners a & b
def wire_box(a, b, **kw):
    v = [*product(*zip(a, b))]
    P = line3d([v[i] for i in (0,1,3,2,0)], **kw)
    P += line3d([v[i] for i in (4,5,7,6,4)], **kw)
    P += sum(line3d(t, **kw) for t in zip(v[:4], v[4:]))
    return P 

@interact
def main(
  start="2023-Jul-17 08:00", stop="2023-Jul-17 14:00", step="1m", obs_start="2023-Jul-17 10:05", obs_end="2023-Jul-17 11:03",
  center="399", targets="-158",
  palette="blue, yellow, red",
  plane = Selector(['Ecliptic', 'Frame', 'Body Equator'], selector_type='radio'),
  curve=True, dots=False, size=5, label_step=30,
  frame=True, dark=True, perspective=False, auto_update=False): 

    if not (dots or curve):
        print("Select at least one of dots or curve")
        return 

    center, start, stop, step, obs_start, obs_end = center.strip(), start.strip(), stop.strip(), step.strip(), obs_start.strip(), obs_end.strip()
    center = '@' + center 

    targets = [s.strip() for s in targets.split(',')]
    palette = [s.strip() for s in palette.split(',')] 

    projection = 'perspective' if perspective else 'orthographic'
    theme = 'dark' if dark else 'light' 

    # Point size
    ps = size * 1e6 if perspective else size 

    # Centre
    org = (0, 0, 0)
    P = point3d(org, size=ps, color=palette[0]) 

    for j, (target, color) in enumerate(zip(targets, palette[1:])):
        data = fetch_data(target, center, plane, start, stop, step)
        if data is None:
            return
        if j == 0 and label_step != 0:
            pos, tgt, dates, colors = extract_data(data, get_dates=True, obs_start=obs_start, obs_end=obs_end)
        else:
            pos, tgt, _, _ = extract_data(data, get_dates=False, obs_start=obs_start, obs_end=obs_end) 

        if dots:
            P += point3d(pos, size=ps, color=color)
        if curve:
            for colorgroup in set(colors):
                P += bezier3d(bez([p for k,p in enumerate(pos) if colors[k]==colorgroup], [p for k,p in enumerate(tgt) if colors[k]==colorgroup]), color=colorgroup) 

        if label_step:
            P += sum(text3d(dates[i*label_step].split(" ", 2)[2].rsplit(" ", 1)[0].split(".")[0], p, fontsize="x-small")
              for i, p in enumerate(pos[::label_step])) 

    #if label_step:
    #    print("\nLabels")
    #    print("\n".join([f"{i:3}: {s}"
    #      for i, s in enumerate(dates[::label_step])])) 

    P += sphere((0,0,0), size=4.26e-5, color=(0,0,1))
    
    bbox = P.bounding_box()
    # XY plane
    P += plot3d(0, *[*zip(*bbox)][:2], color="#aaa", opacity=0.25)
    # The +X axis
    P += line3d([org, (bbox[1][0], 0, 0)], color="#555")
    if frame:
        P += wire_box(*bbox, color="green") 

    P.show(frame=False, theme=theme, projection=projection, online=True)
