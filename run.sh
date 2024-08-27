#!/bin/bash
#SBATCH --job-name=dft
#SBATCH -A research
#SBATCH -p long
#SBATCH -c 10
#SBATCH --gres=gpu:1
#SBATCH --time=4-00:00:00
#SBATCH --output dft.log
#SBATCH --mail-type=ALL
#SBATCH --mail-user=harsha.vasamsetti@research.iiit.ac.in
#SBATCH -w gnode055

module add u18/vasp/6.1.0
module load u18/openmpi/4.1.2
export CUDA_VISIBLE_DEVICES=0

echo "chdir"
cd /scratch/harsha.vasamsetti/
echo $(ls)

source /home2/harsha.vasamsetti/miniconda3/bin/activate slices

# Run VASP
# mpirun -np 1 vasp_gpu

# Then execute your Python script which processes the results
python /scratch/harsha.vasamsetti/0_run.py