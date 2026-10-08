"""Generate as-modeled, compact, and raised SEA inertia test references."""
from argparse import ArgumentParser
from pathlib import Path
import csv
import json
import math
import random

PROFILES = {
    'as_modeled': dict(od=70, thickness=6, radii=[25], hole_d=6.4,
                       center_d=8.2, mount_count=3, mount_d=3.2, mount_r=8, mount_offset=math.pi/2,
                       washer_od=18, washer_id=6.4, washer_thickness=1.6,
                       insert_od=6.2, insert_thickness=1.2,
                       kit_mass_g=10, max_layers=12, shaft_height=41, stud_length=75),
    'compact': dict(od=72, thickness=4, radii=[26], hole_d=6.6,
                    washer_od=18, washer_id=6.4, washer_thickness=1.6,
                    insert_od=6.2, insert_thickness=1.2,
                    kit_mass_g=10, max_layers=12, shaft_height=41, stud_length=75),
    'raised': dict(od=196, thickness=4, radii=[40,52,80], hole_d=8.4,
                   washer_od=24, washer_id=8.4, washer_thickness=2,
                   insert_od=8.2, insert_thickness=1.6,
                   kit_mass_g=10, max_layers=4, shaft_height=110, stud_length=75),
}

def points(n,r,offset=0):
    return [(r*math.cos(offset+2*math.pi*k/n),r*math.sin(offset+2*math.pi*k/n)) for k in range(n)]

def geometry(p):
    R=p['od']/2000;t=p['thickness']/1000
    holes=[(0.,0.,p.get('center_d',14.2)/2000)]
    for radius in p['radii']:
        holes += [(x,y,p['hole_d']/2000) for x,y in points(8,radius/1000)]
    holes += [(x,y,p.get('mount_d',3.4)/2000) for x,y in points(p.get('mount_count',4),p.get('mount_r',11)/1000,p.get('mount_offset',math.pi/8))]
    mc=1240*math.pi*t*(R**2-sum(h*h for x,y,h in holes))
    jc=1240*math.pi*t*(R**4/2-sum(h*h*(x*x+y*y+h*h/2) for x,y,h in holes))
    return holes,mc,jc

def main():
    parser=ArgumentParser(description=__doc__)
    parser.add_argument('--profile',choices=PROFILES,default='compact')
    parser.add_argument('--max-layers',type=int,default=None)
    parser.add_argument('--carrier-mass-g',type=float,default=None)
    parser.add_argument('--washer-mass-g',type=float,default=None)
    parser.add_argument('--insert-mass-g',type=float,default=None)
    parser.add_argument('--kit-mass-g',type=float,default=None)
    parser.add_argument('--external-inertia',type=float,default=1e-5)
    parser.add_argument('--out-dir',default=None)
    args=parser.parse_args();p=PROFILES[args.profile].copy()
    if args.max_layers is not None:p['max_layers']=args.max_layers
    if args.kit_mass_g is not None:p['kit_mass_g']=args.kit_mass_g
    if not 1<=p['max_layers']<=30:parser.error('Choose 1-30 layers; this is not a validated mechanical limit')
    if p['kit_mass_g']<0 or args.external_inertia<0:parser.error('Mass/inertia cannot be negative')
    for value in [args.carrier_mass_g,args.washer_mass_g,args.insert_mass_g]:
        if value is not None and value<=0:parser.error('Measured masses must be positive')
    out=Path(args.out_dir or f'hardware/cad/inertial_disk/{args.profile}');out.mkdir(parents=True,exist_ok=True)
    holes,mc,jc=geometry(p)
    if args.carrier_mass_g is not None:
        jc*=args.carrier_mass_g/1000/mc;mc=args.carrier_mass_g/1000
    wo=p['washer_od']/2000;wi=p['washer_id']/2000;wt=p['washer_thickness']/1000
    mw=7850*math.pi*wt*(wo*wo-wi*wi)
    if args.washer_mass_g is not None:mw=args.washer_mass_g/1000
    kw=(wo*wo+wi*wi)/2;mk=p['kit_mass_g']/1000;base=jc+args.external_inertia
    io=p['insert_od']/2000;ii=.0043/2
    mi=1240*math.pi*(p['insert_thickness']/1000)*(io*io-ii*ii)
    if args.insert_mass_g is not None:mi=args.insert_mass_g/1000
    ki=(io*io+ii*ii)/2
    def setting(name,radius,qa,qb,kits=8):
        r=radius/1000;count=8*(qa+qb)
        J=base+kits*mk*r*r+count*(mw*(r*r+kw)+mi*(r*r+ki))
        return dict(config=name,radius_mm=radius,A_per_face=qa,B_per_face=qb,
                    mass_washer_count=count,retention_kits=kits,
                    carrier_weights_kits_mass_g=(mc+kits*mk+count*(mw+mi))*1000,
                    max_grip_mm=p['thickness']+8+2*max(qa,qb)*p['washer_thickness'],
                    J_estimate_kg_m2=J,locked_motor_load_mode_hz=math.sqrt(1/J)/(2*math.pi))
    rows=[setting('BARE',0,0,0,0)]
    for radius in p['radii']:
        r=radius/1000
        assert 2*r*math.sin(math.pi/8)>2*wo
        assert p['od']/2000-r-wo>=.001-1e-12
        for step in range(2*p['max_layers']+1):
            rows.append(setting(f'R{radius:02d}-S{step:02d}',radius,(step+1)//2,step//2))
    for i,(x,y,h) in enumerate(holes):
        assert math.hypot(x,y)+h<p['od']/2000
        for xx,yy,hh in holes[:i]:assert math.hypot(x-xx,y-yy)>h+hh
    for row in rows[1:]:
        pts=points(8,row['radius_mm']/1000)
        ms=[mk+2*(mw+mi)*(row['A_per_face'] if k%2==0 else row['B_per_face']) for k in range(8)]
        for vals in [[m*x for m,(x,y) in zip(ms,pts)], [m*y for m,(x,y) in zip(ms,pts)],
                     [m*x*y for m,(x,y) in zip(ms,pts)], [m*(x*x-y*y) for m,(x,y) in zip(ms,pts)]]:
            assert abs(sum(vals))<1e-12
    assert len({round(row['J_estimate_kg_m2'],12) for row in rows})==len(rows)
    summary=dict(profile=args.profile,geometry_mm=p,carrier_mass_g=mc*1000,carrier_J_kg_m2=jc,
                 washer_mass_g=mw*1000,insert_mass_g=mi*1000,kit_mass_g=p['kit_mass_g'],external_J_allowance_kg_m2=args.external_inertia,
                 ground_clearance_mm=p['shaft_height']-p['od']/2,distinct_settings=len(rows),
                 hub_note=('As-modeled interface: 8.2 bore, three 3.2 holes on 16 PCD, 90 degree first hole. Verify shaft fit and hub engagement.' if args.profile=='as_modeled' else 'Proposed common interface: 14.2 pilot hole, four 3.4 holes on 22 PCD, 22.5 degree offset. Confirm actual hub.'),
                 limitations='No strength/speed rating. Constant kit mass assumes fixed 75 mm studs with all nuts and retaining washers installed. External inertia is an allowance.',
                 checks='Hole separation, washer separation, first/second planar moments, distinct J values passed',configurations=rows)
    (out/'calculations.json').write_text(json.dumps(summary,indent=2)+'\n')
    with (out/'configurations.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    # Adjacent nominal values can be closer than the eventual ID uncertainty.
    subset=[]
    for row in sorted(rows,key=lambda r:r['J_estimate_kg_m2']):
        if not subset or row['J_estimate_kg_m2']/subset[-1]['J_estimate_kg_m2']>=1.05:
            subset.append(row)
    with (out/'recommended_sweep.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(subset)
    rng=random.Random(41);manifest=[]
    for repeat in range(1,4):
        order=rows.copy();rng.shuffle(order)
        for row in order:
            manifest.append(dict(run_id=f'{args.profile}-{len(manifest)+1:03d}',repeat_block=repeat,
                                 config=row['config'],A_per_face=row['A_per_face'],B_per_face=row['B_per_face'],
                                 radius_mm=row['radius_mm'],J_estimate_kg_m2=row['J_estimate_kg_m2'],
                                 J_identified_kg_m2='',controller_mode='',excitation_id='',temperature_C='',data_filename='',notes=''))
    with (out/'run_manifest.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(manifest[0]));w.writeheader();w.writerows(manifest)
    lines=['0','SECTION','2','HEADER','9','$INSUNITS','70','4','0','ENDSEC','0','SECTION','2','ENTITIES']
    for x,y,h in [(0,0,p['od']/2000)]+holes:
        lines+=['0','CIRCLE','8','CARRIER_CUT','10',f'{x*1000:.8f}','20',f'{y*1000:.8f}','30','0','40',f'{h*1000:.8f}']
    lines+=['0','ENDSEC','0','EOF'];(out/'carrier_reference.dxf').write_text('\n'.join(lines)+'\n')
    draw(out,p,holes,rows)
    print(json.dumps({k:v for k,v in summary.items() if k!='configurations'},indent=2))
    for row in rows:print(f"{row['config']:10s} A/B={row['A_per_face']}/{row['B_per_face']} J={row['J_estimate_kg_m2']:.8f}; mass={row['carrier_weights_kits_mass_g']:.1f} g")

def draw(out,p,holes,rows):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10})
    fig,(ax,chart)=plt.subplots(1,2,figsize=(13,6.8),gridspec_kw={'width_ratios':[1,1.25]})
    fig.patch.set_facecolor('#f7f8fa');R=p['od']/2;r=p['radii'][0];wo=p['washer_od']/2
    ax.add_patch(Circle((0,0),R,facecolor='#e1e7ed',edgecolor='#344454',lw=1.5))
    for radius in p['radii']:ax.add_patch(Circle((0,0),radius,fill=False,edgecolor='#8595a5',ls='--',lw=.7))
    for k,(x,y) in enumerate(points(8,r)):
        ax.add_patch(Circle((x,y),wo,facecolor='#c9e7d7' if k%2==0 else '#f6d8ab',edgecolor='#344454',lw=1))
        dx,dy=points(8,r+wo*.68)[k];ax.text(dx,dy,'A' if k%2==0 else 'B',ha='center',va='center',fontsize=8)
    for x,y,h in holes:ax.add_patch(Circle((x*1000,y*1000),h*1000,facecolor='white',edgecolor='#344454',lw=.7))
    ground=-p['shaft_height'];ax.axhline(ground,color='#596e80',lw=1.4)
    ax.annotate('',xy=(R+8,ground),xytext=(R+8,-R),arrowprops={'arrowstyle':'<->'})
    ax.text(R+11,(ground-R)/2,f"{p['shaft_height']-R:g} mm",va='center',fontsize=9)
    ax.text(0,ground-7,'Ground / clear support surface',ha='center',fontsize=9)
    ax.set(xlim=(-R-12,R+32),ylim=(ground-17,R+12),aspect='equal');ax.axis('off')
    ax.set_title(f"Carrier: diameter {p['od']} x {p['thickness']} mm\n8 stations; group A / group B",pad=16)
    for radius in p['radii']:
        selected=[row for row in rows if row['radius_mm']==radius]
        chart.plot([row['mass_washer_count'] for row in selected],[row['J_estimate_kg_m2']*1e3 for row in selected],marker='o',ms=4,label=f'Radius {radius} mm')
    chart.scatter([0],[rows[0]['J_estimate_kg_m2']*1e3],color='#344454',label='Bare carrier')
    if p['od']>100:chart.axhline(1.2,color='#8595a5',ls='--',label='Original model target')
    chart.set(xlabel='Total mass washers (both faces)',ylabel='Estimated load inertia [10^-3 kg m^2]')
    chart.grid(alpha=.2);chart.legend(frameon=False)
    chart.set_title(f"{len(rows)} distinct calculated settings\nEach step adds 8 washers to one complete quartet",pad=16)
    fig.suptitle('SEA load disk | symmetric inertia sweep',fontsize=17,weight='bold')
    fig.text(.5,.025,'A: 0, 90, 180, 270 degrees. B: 45, 135, 225, 315 degrees. Equal face stacks within each group.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.06,1,.93));fig.savefig(out/'design_reference.png',dpi=170,facecolor=fig.get_facecolor());fig.savefig(out/'design_reference.svg',facecolor=fig.get_facecolor());plt.close(fig)
    svg=out/'design_reference.svg'
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n',encoding='utf-8')

if __name__=='__main__':main()
