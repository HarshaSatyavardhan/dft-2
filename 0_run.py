import os
import shutil
from custodian.vasp.jobs import VaspJob
from pymatgen.io.vasp.sets import MPStaticSet
from pymatgen.core.structure import Structure
from custodian.custodian import Custodian
from custodian.vasp.handlers import VaspErrorHandler, UnconvergedErrorHandler, NonConvergingErrorHandler, \
    PotimErrorHandler, DriftErrorHandler, AliasingErrorHandler, PositiveEnergyErrorHandler, MeshSymmetryErrorHandler
from pymatgen.io.vasp.outputs import Vasprun
import json

def run_dft_calculation(structure_file, vasp_cmd, directory="./dft"):
    """
    Set up and run a DFT calculation for a given structure file.

    Args:
        structure_file (str): Path to the input structure file (CIF).
        vasp_cmd (list): Command to run VASP as a list of args.
        directory (str): Directory to run the calculations.

    Returns:
        dict: A dictionary containing the calculation results.
    """
    structure = Structure.from_file(structure_file)
    if os.path.exists(directory):
        shutil.rmtree(directory)
    os.makedirs(directory)

    # Set up DFT calculation
    dft_set = MPStaticSet(structure, 
                          user_incar_settings={
                              'SYSTEM': 'qvasp',
                              'PREC': 'Normal',
                              'ENCUT': 400,
                              'NELMIN': 5,
                              'LREAL': 'Auto',
                              'EDIFF': 1E-6,
                              'ISMEAR': 1,
                              'SIGMA': 0.2,
                              'ISPIN': 1,
                              'NCORE': 4,
                              'ICHARG': 2,
                              'EDIFFG': 0.01,
                              'NSW': 300,
                              'IBRION': 2,
                              'POTIM': 0.5,
                              'ISIF': 2,
                              'PSTRESS': 0,
                              'LCHARG': False,
                              'LWAVE': False,
                              'ISYM': 0,
                              'SYMPREC': 1E-10
                          },
                          user_kpoints_settings={'reciprocal_density': 100},
                          user_potcar_settings={
                              "POTCAR_FUNCTIONAL": "PBE_54",
                              "POTCAR": {"Nd": "Nd_3", "Al": "Al"}
                          })
    dft_set.write_input(directory)

    # Change to the calculation directory
    original_dir = os.getcwd()
    os.chdir(directory)

    # Set up and run the job
    job = VaspJob(vasp_cmd, final=True, suffix=".static")
    handlers = [
        VaspErrorHandler(),
        UnconvergedErrorHandler(),
        NonConvergingErrorHandler(),
        PotimErrorHandler(),
        DriftErrorHandler(),
        AliasingErrorHandler(),
        PositiveEnergyErrorHandler(),
        MeshSymmetryErrorHandler(),
    ]

    c = Custodian(handlers, [job], max_errors=5)
    c.run()

    # Analyze results
    results = {}
    vasprun_file = "vasprun.xml.static"
    if os.path.exists(vasprun_file):
        try:
            vasprun = Vasprun(vasprun_file)
            results['final_energy'] = vasprun.final_energy
            results['bandgap'] = vasprun.get_band_structure().get_band_gap()['energy']
            print(f"Final energy: {results['final_energy']} eV")
            print(f"Bandgap: {results['bandgap']} eV")
        except Exception as e:
            print(f"Error parsing vasprun.xml: {str(e)}")
            results['error'] = f"Error parsing vasprun.xml: {str(e)}"
    else:
        print(f"{vasprun_file} not found. DFT calculation may have failed.")
        results['error'] = f"{vasprun_file} not found"

    # Copy important output files to the original directory
    output_files = ['INCAR', 'KPOINTS', 'POSCAR', 'CONTCAR', 'OUTCAR', vasprun_file]
    for file in output_files:
        if os.path.exists(file):
            shutil.copy(file, original_dir)

    # Change back to the original directory
    os.chdir(original_dir)

    return results

def main():
    # Set up environment variables
    os.environ['VASP_PP_PATH'] = os.path.abspath('./PMG_VASP_PSP_DIR/POT_GGA_PAW_PBE')

    # Define VASP command
    vasp_cmd = ["mpirun", "-np", "1", "vasp_gpu"]

    # Run DFT calculation on Nd3Al11.cif
    cif_file = "Nd3Al11.cif"
    try:
        results = run_dft_calculation(cif_file, vasp_cmd)

        # Save results to a JSON file
        with open('dft_results.json', 'w') as f:
            json.dump(results, f, indent=2)
        print("Results saved to dft_results.json")
    except Exception as e:
        print(f"Error during DFT calculation: {str(e)}")

if __name__ == "__main__":
    main()