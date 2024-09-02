#!/bin/bash
#SBATCH --job-name=dft
#SBATCH -A plafnet2
#SBATCH -p plafnet2
#SBATCH -c 10
#SBATCH --gres=gpu:1
#SBATCH --time=4-00:00:00
#SBATCH --output dft.log
#SBATCH --mail-type=ALL
#SBATCH --mail-user=harsha.vasamsetti@research.iiit.ac.in
#SBATCH -w gnode113

module add u18/vasp/6.1.0
module load u18/openmpi/4.1.2
export CUDA_VISIBLE_DEVICES=0

echo "chdir"
cd /scratch/harsha.vasamsetti/
echo $(ls)

source /home2/harsha.vasamsetti/miniconda3/bin/activate slices

# Then execute your Python script which processes the results
python /scratch/harsha.vasamsetti/run2.py