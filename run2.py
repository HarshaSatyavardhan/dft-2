import subprocess
import json
from pymatgen.core import Structure, Lattice
from pymatgen.io.vasp import Vasprun
from pymatgen.io.vasp.sets import MPRelaxSet, MPStaticSet, MPNonSCFSet
from pymatgen.electronic_structure.plotter import BSDOSPlotter
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
import os
import sys
import shutil
import matplotlib.pyplot as plt

def print_file(fname, nlines=10, header=False):
    with open(fname) as f:
        lines = f.readlines()
    if nlines == 0:
        nlines = len(lines)
    content = "".join(lines[:nlines])
    if len(lines) > nlines:
        content += "..."
    if header:
        print(f"---{fname}---")
    print(content)

def run_vasp(directory, name):
    vasp_cmd = ["mpirun", "-np", "1", "vasp_std"]
    try:
        subprocess.run(vasp_cmd, cwd=directory, check=True)
        print(f"VASP {name} calculation completed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error running VASP {name} calculation: {e}")
        sys.exit(1)

# Create the structure
lattice = Lattice.cubic(5.64)
structure = Structure(lattice, ["Na", "Cl"], [[0, 0, 0], [0.5, 0.5, 0.5]])
structure.sort()
print(structure)

# Set up VASP input for relaxation
user_incar_settings = {
    'EDIFF': 0.0001,
    'EDIFFG': -0.05,
    'LREAL': False,
    'NSW': 200,
    'ALGO': 'Normal',
    'PREC': 'Normal',
    'ISMEAR': 0,
    'SIGMA': 0.05,
    'ISIF': 3,
    'LORBIT': False,
    'LCHARG': True,
    'LWAVE': False,
    'LDAU': False,
    'ISPIN': 1,
    'ISYM': 0
}
user_kpoint_settings = {'reciprocal_density': 64}

# Generate relaxation set input files
vasp_input_set = MPRelaxSet(structure,
    user_incar_settings=user_incar_settings,
    user_kpoints_settings=user_kpoint_settings,
    user_potcar_functional='PBE_54')
vasp_input_set.write_input("./relax")
print_file("./relax/INCAR", nlines=0, header=True)
print_file("./relax/KPOINTS", nlines=10, header=True)

# Run VASP relaxation
run_vasp("./relax", "relaxation")

# Read the relaxed structure
relaxed_structure = Structure.from_file("./relax/CONTCAR")

# Set up VASP input for static calculation
static_incar = {
    'ISMEAR': 0,
    'NELM': 500,
    'LCHARG': True,
    'LWAVE': False,
    'LDAU': False,
}

static_input_set = MPStaticSet(relaxed_structure,
    user_incar_settings=static_incar,
    user_kpoints_settings=user_kpoint_settings,
    user_potcar_functional='PBE_54')
static_input_set.write_input("./static")

# Run VASP static calculation
run_vasp("./static", "static")

# Copy CHGCAR from static to bandstructure directory
shutil.copy2("./static/CHGCAR", "./bandstructure/CHGCAR")

# Set up VASP input for band structure calculation
bs_incar = {
    'ISMEAR': 0,
    'NELM': 500,
    'LORBIT': 10,
    'LCHARG': False,
    'LWAVE': False,
    'ISTART': 1,
    'ICHARG': 11,
    'LDAU': False,
}

bs_input_set = MPNonSCFSet(relaxed_structure,
    user_incar_settings=bs_incar,
    user_kpoints_settings={'line_mode': True},
    user_potcar_functional='PBE_54')
bs_input_set.write_input("./bandstructure")

# Run VASP band structure calculation
run_vasp("./bandstructure", "band structure")

# Read and analyze results
try:
    vasprun_static = Vasprun("./static/vasprun.xml")
    vasprun_bs = Vasprun("./bandstructure/vasprun.xml", parse_projected_eigen=True)
except Exception as e:
    print(f"Error reading vasprun.xml: {e}")
    print("Checking OUTCAR for errors...")
    with open("./bandstructure/OUTCAR", "r") as f:
        outcar_content = f.read()
        if "I REFUSE TO CONTINUE WITH THIS SICK JOB" in outcar_content:
            print("Error: VASP refused to continue. Check CHGCAR file and INCAR settings.")
        else:
            print("Unknown error occurred. Check OUTCAR for more details.")
    sys.exit(1)

dos = vasprun_static.complete_dos
bs = vasprun_bs.get_band_structure("./bandstructure/KPOINTS", line_mode=True)

# Calculate band gap
band_gap = bs.get_band_gap()
print(f"Band gap: {band_gap['energy']:.4f} eV")
print(f"Band gap type: {band_gap['transition']}")

# Plot band structure and DOS
plotter = BSDOSPlotter(bs_projection="elements", dos_projection="elements")
plt_bs, plt_dos = plotter.get_plot(bs, dos)

# Get the figure from one of the axes
fig = plt_bs.figure
# Adjust the layout and figure size
fig.set_size_inches(12, 8)
fig.set_constrained_layout(True)
# fig.tight_layout()

fig.savefig("band_structure_dos.png", dpi=300)  # Increased DPI for better quality
plt.rcParams["font.family"] = "DejaVu Sans"  # or "Arial"
plt.close(fig)
print("Band structure and DOS plot saved as 'band_structure_dos.png'")

# Get spacegroup
sga = SpacegroupAnalyzer(relaxed_structure)
spacegroup = sga.get_space_group_symbol()

# Save results
with open("./static/CONTCAR", "r") as fn2:
    poscar = fn2.read().replace('\n', '\\n')

with open("results.csv", "w") as result_file:
    result_file.write("Compound,Spacegroup,Band_Gap,Band_Gap_Type,POSCAR\n")
    result_file.write(f"NaCl,{spacegroup},{band_gap['energy']:.4f},{band_gap['transition']},{poscar}\n")

print("Results saved to results.csv")