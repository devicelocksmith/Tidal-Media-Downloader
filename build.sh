rm -rf dist
rm -rf build 
rm -rf __init__.spec

cd TIDALDL-PY
rm -rf __init__.spec 
rm -rf dist
rm -rf build 
rm -rf exe
rm -rf MANIFEST.in
rm -rf *.egg-info

python setup.py sdist bdist_wheel
# Explicitly include the ``metadata_refresh`` helper so the frozen executable
# continues to support the ``--refresh-metadata`` flag.
pyinstaller -F --hidden-import tidal_dl.metadata_refresh tidal_dl/__init__.py
mkdir exe
mv dist/__init__.exe exe/tidal-dl.exe

pip uninstall -y tidal-dl

cd ..