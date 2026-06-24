# QCT POSCAR generator

This fork is based on the original QCT POSCAR generation project by **Samuel Del Fre** (`SamDFr/QCT_POSCAR_generation`). The commits authored by Samuel Del Fre remain part of the project history. This fork contains additional workflow customizations and QCT/HPC organization changes maintained by **Alejandro Rivero**.

This repository contains the `QCT_POSCAR_generator.ipynb` notebook used to build molecule/surface initial configurations for QCT workflows, and `MACE_quick_MD_check.ipynb` for short validation MD runs on the generated POSCAR files.

The notebook is configured so you only provide VASP outputs as inputs. It reads `vasprun.xml` for the isolated molecule and the surface trajectory, then generates the molecular vibrational `.npz` cache automatically inside the notebook.

## Project layout

```text
.
├── MACE_quick_MD_check.ipynb
├── QCT_POSCAR_HPC_organizer_SO2.ipynb
├── QCT_POSCAR_generator.ipynb
├── model/
│   └── mace-mh-1.model
├── inputs/
│   ├── molecule/
│   └── surface/
├── outputs/
│   ├── qct_poscars/
│   └── qct_poscars_hpc_SO2/
└── requirements.txt
```

## Setup

Create and activate the local virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m ipykernel install --user --name qct-poscar-generator --display-name "Python (qct-poscar-generator)"
```

Then launch Jupyter from the repository root:

```bash
jupyter lab
```

## Expected input files

The notebook reads the following paths by default:

- `inputs/molecule/SO2/vasprun_SO2.xml`
- `inputs/surface/HOPG_therm/vasprun-100K.xml`
- `inputs/surface/HOPG_therm/vasprun-300K.xml`
- `inputs/surface/HOPG_therm/vasprun-500K.xml`
- `model/mace-mh-1.model` for the quick MACE MD check notebook

The notebook also generates:

- `inputs/molecule/SO2/vibrational_modes-SO2.npz`

## Generality and assumptions

The workflow is generic with respect to the molecule and surface species: nothing is hard-coded to SO2 or to a specific slab composition.

The main assumptions are:

- The molecule `vasprun.xml` must come from an isolated-molecule calculation that contains vibrational modes (`IBRION=5` or `IBRION=6`).
- Each surface `vasprun.xml` must contain an ionic trajectory that ASE can read as a sequence of frames.
- The surface normal is assumed to be along `+z`, and the molecule is launched toward `-z`.
- The molecule is treated as a free molecule for the ZPE initialization, so the vibrational modes must correspond to that isolated molecule, not to the adsorbed system.
- An optional rigid-body rotational energy can be added on top of the ZPE by setting `ROTATION_SETTINGS["temperature_K"]` in `QCT_POSCAR_generator.ipynb`. Use `0.0` or `"0K"` to disable it.
- Output POSCAR atom ordering is preserved intentionally.

The generator notebook writes normal POSCAR output to a run-specific subfolder:

- `outputs/qct_poscars/<surface-temperature>/Ei*/`

For example, if `PATHS["surface_vasprun"]` is `inputs/surface/HOPG_therm/vasprun-500K.xml` and `GENERATION["incident_energy_eV"] = 2`, the generated files are written to:

```text
outputs/qct_poscars/500K/Ei2/POSCAR-1..10
outputs/qct_poscars/500K/Ei2/metadata.json
```

This folder is intended as the normal, temporary output of `QCT_POSCAR_generator.ipynb`. It is useful for interactive runs and quick checks, but it should not be used as the long-term cluster input archive.

For HPC runs, use `QCT_POSCAR_HPC_organizer_SO2.ipynb` to copy and reindex the normal output into:

- `outputs/qct_poscars_hpc_SO2/`

The HPC structure is:

```text
outputs/qct_poscars_hpc_SO2/
├── Ei0.1/
│   ├── Ts100/poscars-rand-zpe/POSCAR-1..10
│   ├── Ts300/poscars-rand-zpe/POSCAR-1..10
│   └── Ts500/poscars-rand-zpe/POSCAR-1..10
├── Ei0.3/
├── Ei0.5/
├── Ei1/
└── Ei2/
```

Each `poscars-rand-zpe` folder contains `POSCAR-1` to `POSCAR-10` and a `metadata.json` file.
The full generated set contains 150 initial conditions:

```text
3 surface temperatures x 5 incident energies x 10 configurations = 150 POSCAR files
```

For cluster submission workflows, two global index files are also written:

- `outputs/qct_poscars_hpc_SO2/index.csv`
- `outputs/qct_poscars_hpc_SO2/index.json`

Each row maps one numerical `job_id` to a surface temperature, incident energy, configuration number, and POSCAR path. This is intended to make scheduler array jobs easier to launch without manually enumerating every folder.

The quick MACE validation notebook writes short MD trajectories and plots under:

- `outputs/mace_md_check/`

## POSCAR generation options

`QCT_POSCAR_generator.ipynb` supports both vibrational ZPE initialization and optional rigid-body rotational excitation of the free molecule before it is placed above the surface.

- ZPE is controlled with `ZPE_SETTINGS`.
- Rotational excitation is controlled with `ROTATION_SETTINGS["temperature_K"]`.
- Set `ROTATION_SETTINGS["temperature_K"] = 0.0` or `"0K"` to deposit only the ZPE.
- Set `ROTATION_SETTINGS["temperature_K"]` to a nonzero value in kelvin to add thermal rotational energy on top of the ZPE.

The final validation cell in `QCT_POSCAR_generator.ipynb` rereads generated POSCAR velocity blocks recursively from a user-defined folder:

```python
VALIDATION_ROOT = Path("outputs/qct_poscars_hpc_SO2")
```

It reports:

- the number of POSCAR files found
- the instantaneous surface-temperature range and average
- the molecule center-of-mass incident energy
- a failure if the incident energy or surface-temperature scale is inconsistent

Run this final validation before organizing or submitting the files to the cluster.

## HPC organization

`QCT_POSCAR_HPC_organizer_SO2.ipynb` is a separate notebook for preparing the cluster input tree. It copies the normal generator output into the SO2 HPC folder convention:

```text
outputs/qct_poscars_hpc_SO2/Ei*/Ts*/poscars-rand-zpe/POSCAR-*
```

It also writes `index.csv` and `index.json` at the root of `outputs/qct_poscars_hpc_SO2`. The source cleanup option is disabled by default; set `CLEAN_SOURCE_AFTER_COPY = True` inside that notebook only when you want to empty the normal `outputs/qct_poscars` folder after copying.

## Surface temperature issue and fix

A unit-conversion problem was detected in the surface velocities written to the generated POSCAR files.

The surface velocities are read directly from the `vasprun.xml` files:

- `inputs/surface/HOPG_therm/vasprun-100K.xml`
- `inputs/surface/HOPG_therm/vasprun-300K.xml`
- `inputs/surface/HOPG_therm/vasprun-500K.xml`

In VASP, the velocity block is in Angstrom/fs. ASE stores velocities internally in its own velocity units. The molecule velocities added by the ZPE and incident-energy routines were already converted with:

```python
velocity / units.fs
```

but the surface velocities were previously inserted without this conversion:

```python
atoms.set_velocities(vel)
```

That made the surface velocities in the written POSCAR files too small when interpreted consistently with VASP units. The symptom was that the surface temperatures appeared far below the intended values when reading the POSCAR with ASE:

```text
100K surfaces appeared near 0.9 K
300K surfaces appeared near 3.1 K
500K surfaces appeared near 4.8 K
```

The corrected line in `QCT_POSCAR_generator.ipynb` is:

```python
atoms.set_velocities(vel / units.fs)
```

After regenerating the POSCAR files, direct validation of the POSCAR velocity blocks gives the expected instantaneous surface temperatures:

```text
100K folders: mean surface temperature about 98 K
300K folders: mean surface temperature about 323 K
500K folders: mean surface temperature about 495 K
```

These values are not exactly 100 K, 300 K, and 500 K for every individual POSCAR because each file uses one instantaneous snapshot from a thermal trajectory. The important check is that the averages and ranges are consistent with the intended thermal ensembles.

The incident translational energies were also checked from the molecule center-of-mass velocity in the written POSCAR files:

```text
Ei0.1 -> 0.100000 eV
Ei0.3 -> 0.300000 eV
Ei0.5 -> 0.500000 eV
Ei1   -> 1.000000 eV
Ei2   -> 2.000000 eV
```

The existing POSCAR folders were regenerated after applying the surface velocity conversion fix.

## Quick MACE MD check

`MACE_quick_MD_check.ipynb` is intended to validate one generated POSCAR quickly before larger-scale use.

It does the following:

- reads one `outputs/qct_poscars/*K/Ei*/POSCAR-*`
- reuses the positions and velocities stored in that POSCAR
- attaches the local model `model/mace-mh-1.model`. MACE model can be downloaded here: [MACE models](https://huggingface.co/mace-foundations)
- runs a short constant-energy NVE trajectory with `VelocityVerlet`
- shows a `tqdm` progress bar during the run
- renders both static structure views and an in-notebook trajectory animation
- can optionally export the saved MD trajectory to `xyz` or `extxyz` format

Useful notebook settings:

- `CONFIG["save_xyz"] = True` enables XYZ export after the MD run.
- `CONFIG["xyz_format"]` accepts `"xyz"` or `"extxyz"`.
- `CONFIG["xyz_name"]` controls the exported file name inside `outputs/mace_md_check/`.

## GitHub notes

- The local virtual environment `.venv/` is ignored.
- Generated outputs are ignored, except for placeholder files that keep the folder structure in Git.
- Input directories are tracked but their contents are ignored by default, which avoids committing heavy or private VASP files accidentally.
- The local `model/` directory contents are ignored by default, so large model binaries are not committed accidentally.
