# Deactivate the travis-provided virtual environment and setup a
# conda-based environment instead
deactivate

# Use the miniconda installer for faster download / install of conda
# itself
pushd .
cd
mkdir -p download
cd download
echo "Cached in $HOME/download :"
ls -l
echo
if [[ ! -f miniconda.sh ]]
   then
   wget $MINICONDA_URL -O miniconda.sh
   fi
chmod +x miniconda.sh && ./miniconda.sh -b -p $HOME/miniconda
cd ..
export PATH=/home/travis/miniconda/bin:$PATH
if [[ `which conda` ]]; then echo 'Conda installation successful'; else exit 1; fi
conda update --yes conda
popd

# Configure the conda environment and put it in the path using the
# provided versions
conda create -n testenv --yes python=$PYTHON_VERSION pip nose
source activate testenv

# Install anaconda gcc compiler to have compiler compatible with the
# anaconda python executable
conda install gcc --yes
echo "Using GCC at "`which gcc`
export CC=`which gcc`

# Install requirements in correct order
cat requirements.txt | xargs -n 1 -L 1 pip install

if [[ "$COVERAGE" == "true" ]]; then
    pip install coverage coveralls
fi

python --version
python -c "import numpy; print('numpy %s' % numpy.__version__)"
python -c "import scipy; print('scipy %s' % scipy.__version__)"
python setup.py develop
