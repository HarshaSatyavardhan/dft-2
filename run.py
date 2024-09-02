import subprocess
import json
from pymatgen.core import Structure, Lattice
from pymatgen.io.vasp import Vasprun, Outcar
from pymatgen.io.vasp.sets import MPRelaxSet
from pymatgen.entries.compatibility import MaterialsProjectCompatibility
from pymatgen.entries.computed_entries import ComputedEntry

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

# Create the structure
lattice = Lattice.cubic(5.64)
structure = Structure(lattice, ["Na", "Cl"], [[0, 0, 0], [0.5, 0.5, 0.5]])
structure.sort()
print(structure)

# Set up VASP input
user_incar_settings = {
    'EDIFF': 1e-5,
    'EDIFFG': -0.02,
    'LREAL': True,
    'NSW': 99,
    'ALGO': 'Normal',
    'PREC': 'Accurate',
    'ISMEAR': 0,
    'SIGMA': 0.05,
    'ISIF': 3,
    'LORBIT': False,
    'LCHARG': False,
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
vasp_cmd = ["mpirun", "-np", "1", "vasp_gpu"]
try:
    subprocess.run(vasp_cmd, cwd="./relax", check=True)
    print("VASP relaxation completed successfully.")
except subprocess.CalledProcessError as e:
    print(f"Error running VASP: {e}")
    exit(1)

# Calculate formation energy
with open('./chemPotMP.json') as handle:
    chemPot = json.load(handle)

# Read the vasprun.xml file
vasprun = Vasprun("./relax/vasprun.xml")

# Get the final energy, structure, and other necessary information
final_energy = vasprun.final_energy
relaxed_structure = vasprun.final_structure
potcar_symbols = vasprun.potcar_symbols
parameters = vasprun.incar

# Create a ComputedEntry with all necessary information
entry = ComputedEntry(
    relaxed_structure.composition,
    final_energy,
    parameters={
        "potcar_symbols": potcar_symbols,
        "hubbards": vasprun.hubbards,
        "run_type": vasprun.run_type,
        "is_hubbard": vasprun.is_hubbard,
        "potcar_spec": vasprun.potcar_spec if hasattr(vasprun, 'potcar_spec') else None,
    }
)

# Process the entry
compat = MaterialsProjectCompatibility()
processed_entry = compat.process_entry(entry)

# Calculate formation energy
enthalpyForm = processed_entry.energy_per_atom
for element, amount in processed_entry.composition.get_el_amt_dict().items():
    enthalpyForm -= amount * chemPot[element] / processed_entry.composition.num_atoms

print(f"Formation Energy: {enthalpyForm:.4f} eV/atom")

# Save results
with open("./relax/CONTCAR", "r") as fn2:
    poscar = fn2.read().replace('\n', '\\n')
with open("results.csv", "w") as result_file:
    result_file.write("Compound,Spacegroup,Formation_Energy,POSCAR,Additional_Info\n")
    result_file.write(f"NaCl,225,{enthalpyForm:.4f},{poscar},Relaxed structure\n")
print("Results saved to results.csv")